"""Provider-free routing evaluation for the authored twenty-question set.

Run the API integration test with seeded personas for answer groundedness; this
script verifies deterministic intent, allowlisted tool, and simulation-action
routing without requiring a provider key.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ai.intent import classify  # noqa: E402
from app.ai.orchestrator import AgentOrchestrator  # noqa: E402
from app.ai.tools import TOOL_SPECS  # noqa: E402

EVAL_CASES = [
    ("Where did I spend the most last month?", "get_spending_by_category"),
    ("Why did my spending increase?", "get_spending_by_category"),
    ("How much am I saving?", "get_financial_summary"),
    ("How can I save ₹10000 this month?", "get_spending_by_category"),
    ("How much debt do I have?", "get_debt_summary"),
    ("What happens if I pay ₹5000 extra on my loan?", "simulate_action"),
    ("Will I have enough money at the end of the month?", "get_cash_flow_forecast"),
    ("What bills are coming up?", "get_recurring_expenses"),
    ("Can I afford a ₹30000 laptop next week?", "calculate_affordability"),
    ("What should I focus on this month?", "get_recommendations"),
    ("What if I cancel my subscription?", "simulate_action"),
    ("What if I reduce dining by ₹3000?", "simulate_action"),
    ("What if my income falls 10%?", "simulate_action"),
    ("Can I save ₹5000 monthly?", "simulate_action"),
    ("How much did I spend on dining?", "get_spending_by_category"),
    ("Show my credit card utilization", "get_debt_summary"),
    ("Tell me my current cash flow", "get_cash_flow_forecast"),
    ("Do I have any upcoming risk?", "get_risk_events"),
    ("How am I doing financially?", "get_financial_summary"),
    ("How is my investment portfolio doing?", None),
]


def main():
    router = AgentOrchestrator.__new__(AgentOrchestrator)
    results = []
    for prompt, expected_tool in EVAL_CASES:
        intent, entities = classify(prompt)
        routed = [] if entities.get("unsupported_area") else router._tool_arguments(intent, entities)
        tools = [name for name, _ in routed]
        assert expected_tool is None or expected_tool in tools, (prompt, expected_tool, tools)
        assert expected_tool is not None or entities.get("unsupported_area"), (prompt, entities)
        assert all(name in TOOL_SPECS for name in tools)
        if expected_tool == "simulate_action":
            args = next(args for name, args in routed if name == expected_tool)
            assert args.get("action_type"), (prompt, args)
        results.append(
            {
                "question": prompt,
                "intent": intent.value,
                "tools": tools,
                "entities": {key: str(value) for key, value in entities.items()},
                "passed": True,
            }
        )
    print(json.dumps({"count": len(results), "passed": len(results), "results": results}, indent=2))


if __name__ == "__main__":
    main()
