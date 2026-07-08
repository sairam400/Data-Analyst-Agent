"""Interactive REPL: type a question, watch the agent's ReAct loop live.

  python -m src.agent.repl                              # mock provider
  python -m src.agent.repl --provider anthropic            # needs ANTHROPIC_API_KEY
  python -m src.agent.repl --provider openai               # needs OPENAI_API_KEY (or Azure vars)

Mock mode can only answer the scripted questions in src/eval/dataset.py —
MockProvider has no real reasoning, it replays a fixed plan per case_id, so it
can't improvise over a question it wasn't scripted for. Type `list` to see
them. --provider anthropic/openai drives the same Agent/tools with genuine
model reasoning, so it can take any question.
"""
import argparse
import sys

from .agent import Agent
from .demo_cli import print_trace
from .providers import get_provider
from ..config import SETTINGS
from ..eval.dataset import CASES, CASES_BY_ID, MOCK_PLANS


def match_mock_case(user_input):
    text = user_input.strip()
    if text in CASES_BY_ID:
        return text
    lowered = text.lower().rstrip("?").strip()
    for case in CASES:
        if case["question"].lower().rstrip("?").strip() == lowered:
            return case["id"]
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=["mock", "anthropic", "openai"], default="mock")
    parser.add_argument("--model", default=None)
    args = parser.parse_args()

    if args.model:
        if args.provider == "openai":
            SETTINGS.openai_model = args.model
        else:
            SETTINGS.anthropic_model = args.model

    if args.provider == "mock":
        provider = get_provider(mock_plans=MOCK_PLANS, provider_name="mock")
        print("Mock agent - scripted plans, real tool execution. Type `list` for the questions it knows.")
    else:
        try:
            provider = get_provider(provider_name=args.provider)
        except Exception as exc:
            print(f"Could not start the {args.provider} provider: {exc}")
            print(f"Set the required API key env var, or run without --provider {args.provider} to use the mock.")
            sys.exit(1)
        print(f"Live agent (provider={args.provider}). Ask anything about the recommerce DB.")

    agent = Agent(provider)
    turn = 0

    while True:
        try:
            user_input = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue
        if user_input.lower() in {"quit", "exit"}:
            break
        if user_input.lower() == "list":
            for case in CASES:
                print(f"  {case['id']:36s} {case['question']}")
            continue

        turn += 1
        if args.provider == "mock":
            case_id = match_mock_case(user_input)
            if case_id is None:
                print("Mock provider doesn't have a script for that question. Type `list` to see what it knows, "
                      "or rerun with --provider anthropic/openai for freeform questions.")
                continue
            trace = agent.run(case_id, CASES_BY_ID[case_id]["question"])
        else:
            trace = agent.run(f"repl-{turn}", user_input)

        print_trace(trace)


if __name__ == "__main__":
    main()
