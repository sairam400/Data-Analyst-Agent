"""Interactive REPL: type a question, watch the agent's ReAct loop live.

  python -m src.agent.repl                                   # mock provider
  python -m src.agent.repl --provider anthropic                # real Claude, needs ANTHROPIC_API_KEY

Mock mode can only answer the 16 scripted questions in src/eval/dataset.py —
MockProvider has no real reasoning, it replays a fixed plan per case_id, so it
can't improvise over a question it wasn't scripted for. Type `list` to see
them. --provider anthropic drives the same Agent/tools with genuine model
reasoning, so it can take any question.
"""
import argparse
import sys

from .agent import Agent
from .demo_cli import print_trace
from .providers import AnthropicProvider, MockProvider
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
    parser.add_argument("--provider", choices=["mock", "anthropic"], default="mock")
    parser.add_argument("--model", default="claude-sonnet-5")
    args = parser.parse_args()

    if args.provider == "anthropic":
        try:
            provider = AnthropicProvider(model=args.model)
        except Exception as exc:
            print(f"Could not start the Anthropic provider: {exc}")
            print("Set ANTHROPIC_API_KEY, or run without --provider anthropic to use the mock.")
            sys.exit(1)
        print(f"Live agent (provider=anthropic, model={args.model}). Ask anything about the recommerce DB.")
    else:
        provider = MockProvider(MOCK_PLANS)
        print("Mock agent - scripted plans, real tool execution. Type `list` for the 16 questions it knows.")

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
                      "or rerun with --provider anthropic for freeform questions.")
                continue
            trace = agent.run(case_id, CASES_BY_ID[case_id]["question"])
        else:
            trace = agent.run(f"repl-{turn}", user_input)

        print_trace(trace)


if __name__ == "__main__":
    main()
