"""Interactive demo: run the agent on one question and print its ReAct loop
live, step by step — the same Agent/tools code the eval harness scores.

  python -m src.agent.demo_cli --list
  python -m src.agent.demo_cli --case avg_order_value
  python -m src.agent.demo_cli --provider anthropic --question "What was our revenue in March 2025?"
  python -m src.agent.demo_cli --provider openai --question "..."
"""
import argparse
import json

from .agent import Agent
from .providers import get_provider
from ..config import SETTINGS
from ..eval.dataset import CASES_BY_ID, MOCK_PLANS


def print_trace(trace):
    print(f"\nQ: {trace['question']}\n")
    for i, step in enumerate(trace["steps"], start=1):
        if step["type"] == "tool":
            print(f"  [{i}] tool call -> {step['tool']}({json.dumps(step['args'])})")
            if step["error"]:
                print(f"      error: {step['error']}")
            else:
                print(f"      observation: {json.dumps(step['observation'])}")
        else:
            print(f"  [{i}] final answer -> {step['answer']}")
    print(f"\n({trace['elapsed_seconds']}s, {len(trace['tool_calls'])} tool call(s): "
          f"{trace['tool_calls']}, {trace['retries']} retr{'y' if trace['retries'] == 1 else 'ies'})")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=["mock", "anthropic", "openai"], default="mock")
    parser.add_argument("--model", default=None, help="overrides the configured model for the chosen provider")
    parser.add_argument("--case", help="case id from src/eval/dataset.py (required for --provider mock)")
    parser.add_argument("--question", help="freeform question (only used with --provider anthropic/openai)")
    parser.add_argument("--list", action="store_true", help="list available case ids and exit")
    args = parser.parse_args()

    if args.list:
        for case_id, case in CASES_BY_ID.items():
            print(f"{case_id:36s} {case['question']}")
        return

    if args.model:
        if args.provider == "openai":
            SETTINGS.openai_model = args.model
        else:
            SETTINGS.anthropic_model = args.model

    if args.provider == "mock":
        if not args.case:
            parser.error("--provider mock requires --case (see --list)")
        provider = get_provider(mock_plans=MOCK_PLANS, provider_name="mock")
        agent = Agent(provider)
        trace = agent.run(args.case, CASES_BY_ID[args.case]["question"])
    else:
        provider = get_provider(provider_name=args.provider)
        agent = Agent(provider)
        question = args.question or CASES_BY_ID[args.case]["question"]
        trace = agent.run(args.case or "adhoc", question)

    print_trace(trace)


if __name__ == "__main__":
    main()
