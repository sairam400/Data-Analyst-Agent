"""Eval suite entry point.

  python -m src.eval.run_eval --provider mock
  python -m src.eval.run_eval --provider anthropic --model claude-sonnet-5

Runs every case in dataset.py through the agent, scores it on three axes,
writes reports/results.json, and renders reports/report.html.
"""
import argparse
import json
from pathlib import Path
from statistics import mean

from ..agent.agent import Agent
from ..agent.providers import AnthropicProvider, MockProvider
from ..agent.tools import DB_PATH
from .dataset import CASES, MOCK_PLANS
from .report import generate_report
from .scorers import score_case

REPO_ROOT = Path(__file__).resolve().parents[2]


def compute_aggregate(results, provider_name, faithfulness_method):
    n = len(results)
    return {
        "provider": provider_name,
        "n_cases": n,
        "overall_pass_rate": round(mean(1.0 if r["score"]["overall_pass"] else 0.0 for r in results), 4),
        "tool_choice_avg": round(mean(r["score"]["tool_choice"]["score"] for r in results), 4),
        "answer_match_avg": round(mean(r["score"]["answer_match"]["score"] for r in results), 4),
        "faithfulness_avg": round(mean(r["score"]["faithfulness"]["score"] for r in results), 4),
        "faithfulness_method": faithfulness_method,
        "avg_latency_seconds": round(mean(r["trace"]["elapsed_seconds"] for r in results), 4),
        "total_tool_calls": sum(len(r["trace"]["tool_calls"]) for r in results),
        "honest_failures": [r["score"]["case_id"] for r in results if r["score"]["is_honest_failure"]],
    }


def main():
    parser = argparse.ArgumentParser(description="Run the data-analyst agent eval suite.")
    parser.add_argument("--provider", choices=["mock", "anthropic"], default="mock")
    parser.add_argument("--model", default="claude-sonnet-5")
    parser.add_argument("--llm-judge", action="store_true",
                         help="Score faithfulness with a real Claude judge call instead of the "
                              "deterministic grounding heuristic (needs ANTHROPIC_API_KEY).")
    parser.add_argument("--out", default=str(REPO_ROOT / "reports" / "results.json"))
    parser.add_argument("--report", default=str(REPO_ROOT / "reports" / "report.html"))
    args = parser.parse_args()

    if not DB_PATH.exists():
        from ..data.seed import build as seed_build
        seed_build()

    provider = MockProvider(MOCK_PLANS) if args.provider == "mock" else AnthropicProvider(model=args.model)
    agent = Agent(provider)

    faithfulness_client = None
    faithfulness_method = "heuristic-grounding"
    if args.llm_judge:
        import anthropic
        faithfulness_client = anthropic.Anthropic()
        faithfulness_method = "llm-judge"

    results = []
    for case in CASES:
        trace = agent.run(case["id"], case["question"])
        score = score_case(case, trace, faithfulness_client=faithfulness_client, faithfulness_model=args.model)
        results.append({"trace": trace, "score": score})
        status = "PASS" if score["overall_pass"] else "FAIL"
        marker = " (expected)" if score["is_honest_failure"] else ""
        print(f"[{status}]{marker} {case['id']}")

    aggregate = compute_aggregate(results, args.provider, faithfulness_method)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"aggregate": aggregate, "results": results}, indent=2, default=str))

    report_path = Path(args.report)
    generate_report(results, aggregate, report_path)

    print(f"\n{aggregate['n_cases']} cases, "
          f"{round(aggregate['overall_pass_rate'] * aggregate['n_cases'])} passed "
          f"({aggregate['overall_pass_rate']*100:.0f}%)")
    print(f"results: {out_path}")
    print(f"report:  {report_path}")


if __name__ == "__main__":
    main()
