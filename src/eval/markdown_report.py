"""Renders reports/results.md: a compact markdown table meant to be pasted
straight into the README's eval results section."""


def generate_markdown(results, aggregate):
    lines = [
        f"Provider: `{aggregate['provider']}` &middot; {aggregate['n_cases']} cases &middot; "
        f"faithfulness method: `{aggregate['faithfulness_method']}`",
        "",
        f"Overall pass rate: **{aggregate['overall_pass_rate'] * 100:.0f}%** &middot; "
        f"avg tool calls: **{aggregate['avg_tool_calls']:.2f}** &middot; "
        f"avg retries: **{aggregate['avg_retries']:.2f}**",
        "",
        "| case | status | tool calls | retries |",
        "|---|---|---|---|",
    ]
    for entry in results:
        score, trace = entry["score"], entry["trace"]
        if score["overall_pass"]:
            status = "PASS"
        elif score["is_honest_failure"]:
            status = "EXPECTED FAIL"
        else:
            status = "FAIL"
        lines.append(f"| `{score['case_id']}` | {status} | {len(trace['tool_calls'])} | {trace['retries']} |")
    return "\n".join(lines) + "\n"
