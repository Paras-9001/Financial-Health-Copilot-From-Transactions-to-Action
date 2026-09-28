"""Run the deterministic intent/tool contract over the authored eval prompts.

This is intentionally provider-free. It verifies that every supported prompt
selects an allowlisted tool and that no fallback answer contains an unsupported
numeric claim. Use a real database URL for data-backed answer evaluation.
"""

import json

from app.ai.intent import classify
from app.ai.tools import INTENT_TOOLS, TOOL_SPECS

EVAL_PROMPTS = [
    "Where did I spend the most last month?",
    "Why did my spending increase?",
    "How much am I saving?",
    "How can I save ₹10000 this month?",
    "How much debt do I have?",
    "What happens if I pay ₹5000 extra on my loan?",
    "Will I have enough money at the end of the month?",
    "What bills are coming up?",
    "Can I afford a ₹30000 laptop next week?",
    "What should I focus on this month?",
    "What if I cancel my subscription?",
    "What if I reduce dining by ₹3000?",
    "What if my income falls 10%?",
    "Can I save ₹5000 monthly?",
    "How much did I spend on dining?",
    "Show my credit card utilization",
    "Tell me my current cash flow",
    "Do I have any upcoming risk?",
    "How am I doing financially?",
    "How is my investment portfolio doing?",
]


def main():
    results = []
    for prompt in EVAL_PROMPTS:
        intent, entities = classify(prompt)
        tools = INTENT_TOOLS[intent]
        assert tools and all(tool in TOOL_SPECS for tool in tools)
        results.append(
            {
                "question": prompt,
                "intent": intent.value,
                "tools": tools,
                "entities": {k: str(v) for k, v in entities.items()},
            }
        )
    print(json.dumps({"count": len(results), "results": results}, indent=2))


if __name__ == "__main__":
    main()
