"""Eval suite entry point.

  python -m src.eval.run_eval --provider mock
  python -m src.eval.run_eval --provider anthropic --model claude-sonnet-5
  python -m src.eval.run_eval --provider openai --model gpt-4o

Runs every case in dataset.py through the agent, scores it on three axes,
writes reports/results.json, reports/report.html, and reports/results.md.
"""
import argparse
import json
from pathlib import Path
from statistics import mean

from ..agent.agent import Agent
from ..agent.providers import get_provider
from ..agent.tools import DB_PATH
from ..config import SETTINGS
from .dataset import CASES, MOCK_PLANS
from .markdown_report import generate_markdown
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
        "avg_tool_calls": round(mean(len(r["trace"]["tool_calls"]) for r in results), 4),
        "avg_retries": round(mean(r["trace"]["retries"] for r in results), 4),
        "total_tool_calls": sum(len(r["trace"]["tool_calls"]) for r in results),
        "honest_failures": [r["score"]["case_id"] for r in results if r["score"]["is_honest_failure"]],
    }


def main():
    parser = argparse.ArgumentParser(description="Run the data-analyst agent eval suite.")
    parser.add_argument("--provider", choices=["mock", "anthropic", "openai"], default="mock")
    parser.add_argument("--model", default=None)
    parser.add_argument("--llm-judge", action="store_true",
                         help="Score faithfulness with a real Claude judge call instead of the "
                              "deterministic grounding heuristic (needs ANTHROPIC_API_KEY).")
    parser.add_argument("--out", default=str(REPO_ROOT / "reports" / "results.json"))
    parser.add_argument("--report", default=str(REPO_ROOT / "reports" / "report.html"))
    parser.add_argument("--markdown", default=str(REPO_ROOT / "reports" / "results.md"))
    args = parser.parse_args()

    if not DB_PATH.exists():
        from ..data.seed import build as seed_build
        seed_build()

    if args.model:
        if args.provider == "openai":
            SETTINGS.openai_model = args.model
        else:
            SETTINGS.anthropic_model = args.model

    provider = get_provider(mock_plans=MOCK_PLANS, provider_name=args.provider)
    agent = Agent(provider)

    faithfulness_client = None
    faithfulness_method = "heuristic-grounding"
    faithfulness_model = args.model or SETTINGS.anthropic_model
    if args.llm_judge:
        import anthropic
        faithfulness_client = anthropic.Anthropic()
        faithfulness_method = "llm-judge"

    results = []
    for case in CASES:
        trace = agent.run(case["id"], case["question"])
        score = score_case(case, trace, faithfulness_client=faithfulness_client, faithfulness_model=faithfulness_model)
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

    markdown_path = Path(args.markdown)
    markdown_path.write_text(generate_markdown(results, aggregate), encoding="utf-8")

    print(f"\n{aggregate['n_cases']} cases, "
          f"{round(aggregate['overall_pass_rate'] * aggregate['n_cases'])} passed "
          f"({aggregate['overall_pass_rate']*100:.0f}%)")
    print(f"results:  {out_path}")
    print(f"report:   {report_path}")
    print(f"markdown: {markdown_path}")


if __name__ == "__main__":
    main()
