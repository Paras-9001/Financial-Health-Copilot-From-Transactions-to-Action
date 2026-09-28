"""Bounded, evidence-first agent orchestration."""

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.ai.grounding import numeric_claims_grounded
from app.ai.intent import classify, extract_amount, extract_target_date
from app.ai.prompts import SYSTEM_PROMPT, composition_prompt
from app.ai.provider import OpenAICompatibleProvider, ProviderError
from app.ai.schemas import ChatResponse, Claim, Intent, ToolCallRecord
from app.ai.tools import INTENT_TOOLS, TOOL_SPECS, ToolError
from app.core.config import get_settings


def _stringify(value: Any) -> str:
    if isinstance(value, dict):
        return ", ".join(f"{k}: {_stringify(v)}" for k, v in list(value.items())[:5])
    if isinstance(value, list):
        return ", ".join(_stringify(v) for v in value[:3])
    return str(value)


class AgentOrchestrator:
    def __init__(self, db: Session, user_id: UUID):
        self.db, self.user_id = db, user_id
        self.tool_records: list[ToolCallRecord] = []
        self.raw_results: list[dict[str, Any]] = []

    def run(self, message: str, history: list[dict[str, str]] | None = None) -> ChatResponse:
        intent, entities = classify(message)
        if entities.get("unsupported_area"):
            area = str(entities["unsupported_area"])
            return ChatResponse(
                answer_text=(
                    f"I don’t have {area} in the supported financial tools, so I can’t answer that reliably. "
                    "I can help with spending, savings, debt, cash flow, affordability, risks, and recommendations."
                ),
                intent=intent,
                missing_information=[area],
            )
        if history and intent in {Intent.GENERAL, Intent.UNCLEAR} and "what about" in message.lower():
            previous = next(
                (item["content"] for item in reversed(history) if item.get("role") == "user"), None
            )
            if previous:
                previous_intent, _ = classify(previous)
                if previous_intent not in {Intent.GENERAL, Intent.UNCLEAR}:
                    intent = previous_intent
        provider = self._provider()
        if provider:
            intent, entities = self._classify_with_provider(provider, message, intent, entities)
        tools = self._tool_arguments(intent, entities)
        for tool_name, args in tools[: get_settings().llm_max_tool_calls]:
            result = self._run_tool(tool_name, args)
            self.raw_results.append(result)
        fallback = self._fallback(intent)
        if provider:
            generated = self._compose_with_provider(provider, intent, message, fallback)
            if generated is not None:
                return generated
        return fallback

    @staticmethod
    def _classify_with_provider(
        provider, message: str, fallback_intent: Intent, fallback_entities: dict[str, object]
    ):
        try:
            raw = provider.classify(message)
            candidate = Intent(str(raw.get("intent", "general")))
            entities = dict(fallback_entities)
            if raw.get("amount") is not None:
                amount = extract_amount(f"₹{raw['amount']}")
                if amount is not None:
                    entities["amount"] = amount
            if raw.get("target_date"):
                target = extract_target_date(str(raw["target_date"]))
                if target:
                    entities["target_date"] = target
            return candidate, entities
        except (ValueError, TypeError, ProviderError):
            return fallback_intent, fallback_entities

    def _provider(self) -> OpenAICompatibleProvider | None:
        settings = get_settings()
        # Cloud AI is opt-in. Setting ai_mode=auto without consent/key remains local.
        if settings.ai_mode == "fallback" or not settings.cloud_ai_consent_granted:
            return None
        return OpenAICompatibleProvider.from_settings()

    def _tool_arguments(
        self, intent: Intent, entities: dict[str, object]
    ) -> list[tuple[str, dict[str, Any]]]:
        amount = entities.get("amount")
        target_date = entities.get("target_date")
        args: dict[str, Any] = {}
        if intent == Intent.AFFORDABILITY:
            if amount is not None:
                args["amount"] = amount
            if target_date is not None:
                args["target_date"] = target_date
        if intent == Intent.SPENDING and entities.get("category"):
            args["category"] = entities["category"]
        if intent == Intent.WHAT_IF:
            params: dict[str, Any] = {}
            if amount is not None:
                params["amount"] = str(amount)
            if target_date is not None:
                params["date"] = str(target_date)
                params["new_date"] = str(target_date)
            if entities.get("category"):
                params["category"] = entities["category"]
            if entities.get("percent") is not None:
                params["percent"] = str(entities["percent"])
            if entities.get("cancel") is not None:
                params["cancel"] = entities["cancel"]
            args = {"action_type": entities.get("action_type"), "params": params}
        names = INTENT_TOOLS[intent]
        if intent == Intent.CASH_FLOW and entities.get("cash_flow_mode") == "recurring":
            names = ["get_recurring_expenses"]
        return [(name, args) for name in names]

    def _run_tool(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        spec = TOOL_SPECS[name]
        try:
            result = spec.run(self.db, self.user_id, args)
        except ToolError as exc:
            result = {"status": "error", "code": exc.code, "reason": exc.message}
        except Exception:
            # Do not leak SQL/provider/internal details to a user or model.
            result = {
                "status": "error",
                "code": "tool_unavailable",
                "reason": "The requested data tool is temporarily unavailable.",
            }
        self.tool_records.append(
            ToolCallRecord(
                tool=name,
                args=self._safe_args(args),
                status=result.get("status", "error"),
                result_summary=_stringify(
                    result.get(
                        "reason",
                        result.get(
                            "facts",
                            result.get(
                                "categories", result.get("risks", result.get("recommendations", "completed"))
                            ),
                        ),
                    )
                ),
            )
        )
        return {"tool": name, "result": result}

    @staticmethod
    def _safe_args(args: dict[str, Any]) -> dict[str, Any]:
        return {
            key: str(value)
            if not isinstance(value, (str, int, float, bool, type(None), dict, list))
            else value
            for key, value in args.items()
        }

    def _fallback(self, intent: Intent) -> ChatResponse:
        first = self.raw_results[0]["result"] if self.raw_results else {"status": "error"}
        if first.get("status") == "insufficient_data":
            missing = [str(v) for v in first.get("missing_information", [])]
            answer = "I can’t answer that reliably from this workspace yet. " + first.get(
                "reason", "Some required information is missing."
            )
            if missing:
                answer += " Please add or confirm: " + ", ".join(missing) + "."
            return ChatResponse(
                answer_text=answer, intent=intent, tool_calls=self.tool_records, missing_information=missing
            )
        if first.get("status") == "error":
            return ChatResponse(
                answer_text="I couldn’t complete that financial lookup just now. Please try again.",
                intent=intent,
                tool_calls=self.tool_records,
            )
        facts: list[Claim] = []
        predictions: list[Claim] = []
        recommendations: list[Claim] = []
        assumptions: list[Claim] = []
        if "facts" in first:
            for label, value in first["facts"].items():
                facts.append(
                    Claim(
                        type="fact",
                        label=label.replace("_", " ").title(),
                        value=value,
                        source=self.tool_records[0].tool,
                    )
                )
            answer = (
                "Here is what your supplied transaction history shows: "
                + "; ".join(f"{c.label}: {c.value}" for c in facts[:3])
                + "."
            )
        elif "categories" in first:
            for row in first["categories"][:5]:
                facts.append(
                    Claim(
                        type="fact",
                        label=f"{row['name']} spending",
                        value=row["amount"],
                        source=self.tool_records[0].tool,
                    )
                )
            answer = (
                "Your largest recorded expense categories are "
                + "; ".join(f"{r['name']} ({r['amount']})" for r in first["categories"][:3])
                + "."
            )
        elif "verdict" in first:
            facts.append(
                Claim(
                    type="fact",
                    label="Affordability verdict",
                    value=first["verdict"],
                    source=self.tool_records[0].tool,
                    confidence=first.get("confidence"),
                )
            )
            predictions.append(
                Claim(
                    type="prediction",
                    label="Resulting buffer days",
                    value=first.get("resulting_buffer_days"),
                    source=self.tool_records[0].tool,
                    confidence=first.get("confidence"),
                    basis="; ".join(first.get("reasoning_basis", [])),
                )
            )
            answer = (
                f"The Phase 4 affordability simulation says **{first['verdict']}**. "
                f"The projected resulting buffer is {first.get('resulting_buffer_days')} days."
            )
        elif "total_debt" in first:
            facts = [
                Claim(
                    type="fact",
                    label="Total debt",
                    value=first["total_debt"],
                    source=self.tool_records[0].tool,
                ),
                Claim(
                    type="fact",
                    label="Debt to income",
                    value=first.get("dti"),
                    source=self.tool_records[0].tool,
                ),
                Claim(
                    type="fact",
                    label="Credit utilization",
                    value=first.get("credit_utilization"),
                    source=self.tool_records[0].tool,
                ),
            ]
            answer = (
                f"Your recorded total debt is {first['total_debt']}; debt-to-income is "
                f"{first.get('dti')} and credit utilization is {first.get('credit_utilization')}."
            )
        elif "risks" in first:
            facts = [
                Claim(
                    type="fact",
                    label=r["risk_type"],
                    value=r["severity"],
                    source=self.tool_records[0].tool,
                    confidence=r.get("confidence"),
                )
                for r in first["risks"][:3]
            ]
            answer = (
                "The current risk records are: " + "; ".join(f"{c.label} ({c.value})" for c in facts) + "."
                if facts
                else first.get("summary", "No active risk was detected by the current analysis.")
            )
        elif "recommendations" in first:
            recommendations = [
                Claim(
                    type="recommendation",
                    label=r["title"],
                    value=r.get("reason"),
                    source=self.tool_records[0].tool,
                    confidence=r.get("confidence"),
                )
                for r in first["recommendations"][:3]
            ]
            answer = (
                "The current recommendations are: " + "; ".join(c.label for c in recommendations) + "."
                if recommendations
                else first.get("summary", "No recommendation is supported by the current analysis.")
            )
        elif "baseline" in first and "proposed" in first:
            predictions = [
                Claim(
                    type="prediction",
                    label="Baseline scenario",
                    value=first["baseline"],
                    source=self.tool_records[0].tool,
                    confidence=first.get("confidence"),
                ),
                Claim(
                    type="prediction",
                    label="Proposed scenario",
                    value=first["proposed"],
                    source=self.tool_records[0].tool,
                    confidence=first.get("confidence"),
                ),
            ]
            assumptions.append(
                Claim(
                    type="assumption",
                    label="Trade-off",
                    value=first.get("trade_off_note"),
                    source=self.tool_records[0].tool,
                )
            )
            answer = (
                f"The Phase 4 simulation completed with {first.get('confidence')} confidence. "
                f"The modeled change is: {_stringify(first.get('delta', {}))}."
            )
        elif "daily_projection" in first:
            predictions = [
                Claim(
                    type="prediction",
                    label="Cash-flow forecast",
                    value=first.get("daily_projection"),
                    source=self.tool_records[0].tool,
                    confidence=first.get("confidence"),
                    basis=first.get("method"),
                )
            ]
            answer = f"I found a {first.get('confidence')} confidence cash-flow forecast using {first.get('method')} for {first.get('horizon_days')} days."
        elif "recurring" in first:
            facts = [
                Claim(
                    type="fact",
                    label=row["merchant"],
                    value=row["amount"],
                    source=self.tool_records[0].tool,
                )
                for row in first["recurring"][:5]
            ]
            answer = (
                "The detected recurring expenses are: "
                + "; ".join(f"{item.label} ({item.value})" for item in facts)
                + "."
                if facts
                else "No recurring expense pattern was detected in the available history."
            )
        elif "transactions" in first:
            facts = [
                Claim(
                    type="fact",
                    label=row["merchant"],
                    value=row["amount"],
                    source=self.tool_records[0].tool,
                )
                for row in first["transactions"][:5]
            ]
            answer = (
                "The matching recorded transactions are: "
                + "; ".join(f"{item.label} ({item.value})" for item in facts)
                + "."
                if facts
                else "No transactions matched those filters."
            )
        else:
            answer = "I found the requested data, but it does not yet contain a supported explanation for this question."
        return ChatResponse(
            answer_text=answer,
            intent=intent,
            facts=facts,
            predictions=predictions,
            recommendations=recommendations,
            assumptions=assumptions,
            tool_calls=self.tool_records,
        )

    def _compose_with_provider(
        self, provider: OpenAICompatibleProvider, intent: Intent, message: str, fallback: ChatResponse
    ) -> ChatResponse | None:
        try:
            raw = provider.compose(
                SYSTEM_PROMPT,
                composition_prompt(intent.value, self.raw_results) + "\nUSER_QUESTION:\n" + message,
            )
            raw.setdefault("intent", intent.value)
            raw.setdefault("tool_calls", [record.model_dump(mode="json") for record in self.tool_records])
            raw.setdefault("facts", fallback.facts)
            raw.setdefault("predictions", fallback.predictions)
            raw.setdefault("recommendations", fallback.recommendations)
            raw.setdefault("assumptions", fallback.assumptions)
            raw.setdefault("missing_information", fallback.missing_information)
            raw["provider"] = provider.name
            candidate = ChatResponse.model_validate(raw)
            if not numeric_claims_grounded(candidate.answer_text, self.raw_results):
                return None
            candidate.grounded = True
            return candidate
        except (ProviderError, ValueError, TypeError):
            return None
