from unittest.mock import patch
from uuid import uuid4

from app.ai.grounding import numeric_claims_grounded
from app.ai.intent import classify, extract_amount
from app.ai.orchestrator import AgentOrchestrator
from app.ai.schemas import Intent


def test_intent_classifier_covers_supported_question_types():
    examples = {
        "Where did I spend the most last month?": Intent.SPENDING,
        "How much am I saving?": Intent.SAVINGS,
        "How much debt do I have?": Intent.DEBT,
        "Will I have enough money at the end of the month?": Intent.CASH_FLOW,
        "Can I afford a ₹30,000 laptop next week?": Intent.AFFORDABILITY,
        "What should I focus on this month?": Intent.RECOMMENDATION,
        "What if I cancel my subscription?": Intent.WHAT_IF,
        "Do I have any upcoming risk?": Intent.RISK,
        "How am I doing financially?": Intent.GENERAL,
    }
    for prompt, expected in examples.items():
        intent, _ = classify(prompt)
        assert intent == expected
    assert extract_amount("Can I afford ₹30,000?") == 30000


def test_grounding_rejects_number_not_in_tool_result():
    assert numeric_claims_grounded(
        "Your expenses are ₹48000.", [{"result": {"facts": {"total_expenses": "48000.00"}}}]
    )
    assert not numeric_claims_grounded(
        "Your expenses are ₹49000.", [{"result": {"facts": {"total_expenses": "48000.00"}}}]
    )
    assert numeric_claims_grounded("The 2026 forecast is unavailable.", [{"result": {}}])


def test_chat_response_falls_back_when_tool_data_is_not_available(db_engine):
    orchestrator = AgentOrchestrator.__new__(AgentOrchestrator)
    orchestrator.db = None
    orchestrator.user_id = uuid4()
    orchestrator.tool_records = []
    orchestrator.raw_results = []
    with patch(
        "app.ai.orchestrator.TOOL_SPECS",
        {
            "get_financial_summary": type(
                "Spec",
                (),
                {
                    "run": lambda *_: {
                        "status": "insufficient_data",
                        "reason": "No data",
                        "missing_information": ["transactions"],
                    }
                },
            )()
        },
    ):
        result = orchestrator._run_tool("get_financial_summary", {})
    assert result["result"]["status"] == "insufficient_data"
    assert orchestrator.tool_records[0].tool == "get_financial_summary"


def test_ai_provider_is_opt_in_by_default():
    from app.core.config import get_settings

    assert get_settings().cloud_ai_consent_granted is False


def test_chat_session_and_message_endpoint_are_owner_protected(client, signup_payload):
    signup = client.post("/api/v1/auth/signup", json=signup_payload).json()
    headers = {"Authorization": f"Bearer {signup['token']}"}
    created = client.post("/api/v1/chat/sessions", headers=headers)
    assert created.status_code == 201
    session_id = created.json()["session_id"]
    response = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        headers=headers,
        json={"message": "How am I doing financially?"},
    )
    assert response.status_code == 200
    assert response.json()["intent"] == "general"
    assert response.json()["tool_calls"]
    assert client.get(f"/api/v1/chat/sessions/{session_id}/messages", headers=headers).status_code == 200
    assert client.get(f"/api/v1/chat/sessions/{session_id}/messages").status_code == 401


def test_chat_uses_phase4_services_for_seeded_persona(client, signup_payload):
    signup = client.post("/api/v1/auth/signup", json=signup_payload).json()
    headers = {"Authorization": f"Bearer {signup['token']}"}
    seeded = client.post("/api/v1/onboarding/demo", headers=headers, json={"persona": "ananya"})
    assert seeded.status_code == 201, seeded.text
    session_id = client.post("/api/v1/chat/sessions", headers=headers).json()["session_id"]

    summary = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        headers=headers,
        json={"message": "How much am I saving?"},
    )
    assert summary.status_code == 200, summary.text
    body = summary.json()
    assert body["tool_calls"][0]["tool"] == "get_financial_summary"
    assert body["facts"]
    assert body["grounded"] is True

    scenario = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        headers=headers,
        json={"message": "What if I reduce dining by ₹3000?"},
    )
    assert scenario.status_code == 200, scenario.text
    scenario_body = scenario.json()
    assert scenario_body["tool_calls"][0]["tool"] == "simulate_action"
    assert scenario_body["tool_calls"][0]["status"] in {"ok", "insufficient_data"}
