"""Renders reports/report.html: a single, self-contained dashboard (no CDN,
no JS framework — expand/collapse uses native <details>) so it opens with
zero setup. Colors are the validated default palette from the dataviz skill
(references/palette.md), used verbatim."""
import json
from html import escape as esc

CSS = """
:root {
  --page: #f9f9f7; --surface: #fcfcfb; --ink: #0b0b0b; --ink-2: #52514e; --ink-muted: #898781;
  --grid: #e1e0d9; --baseline: #c3c2b7; --border: rgba(11,11,11,0.10);
  --series-1: #2a78d6; --good: #0ca30c; --critical: #d03b3b; --warning: #eda100;
}
@media (prefers-color-scheme: dark) {
  :root {
    --page: #0d0d0d; --surface: #1a1a19; --ink: #ffffff; --ink-2: #c3c2b7; --ink-muted: #898781;
    --grid: #2c2c2a; --baseline: #383835; --border: rgba(255,255,255,0.10);
    --series-1: #3987e5; --good: #0ca30c; --critical: #e66767; --warning: #c98500;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--page); color: var(--ink);
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  padding: 32px 24px 80px;
}
.wrap { max-width: 960px; margin: 0 auto; }
h1 { font-size: 1.5rem; margin: 0 0 4px; }
.subtitle { color: var(--ink-2); font-size: 0.9rem; margin: 0 0 28px; }
.tile-strip { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 2px;
  background: var(--border); border: 1px solid var(--border); border-radius: 10px; overflow: hidden; margin-bottom: 24px; }
.tile { background: var(--surface); padding: 14px 16px; }
.tile-label { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.04em; color: var(--ink-muted); margin-bottom: 6px; }
.tile-value { font-size: 1.5rem; font-weight: 600; font-variant-numeric: tabular-nums; }
.tile-sub { font-size: 0.72rem; color: var(--ink-muted); margin-top: 2px; }
.honest-banner { background: var(--surface); border: 1px solid var(--warning); border-left: 4px solid var(--warning);
  border-radius: 8px; padding: 12px 16px; font-size: 0.88rem; color: var(--ink-2); margin-bottom: 24px; }
.honest-banner code { color: var(--ink); }
.section-title { font-size: 0.95rem; font-weight: 600; margin: 28px 0 10px; }
.case-card { background: var(--surface); border: 1px solid var(--border); border-radius: 10px;
  margin-bottom: 10px; overflow: hidden; }
.case-card > summary { list-style: none; cursor: pointer; padding: 12px 16px; display: flex;
  align-items: center; gap: 10px; flex-wrap: wrap; }
.case-card > summary::-webkit-details-marker { display: none; }
.status-dot { width: 10px; height: 10px; border-radius: 50%; flex: none; }
.case-card.pass .status-dot { background: var(--good); }
.case-card.fail .status-dot { background: var(--critical); }
.case-card.expected-fail .status-dot { background: var(--warning); }
.case-id { font-family: ui-monospace, monospace; font-size: 0.8rem; color: var(--ink-muted); flex: none; }
.case-question { flex: 1 1 260px; font-size: 0.9rem; }
.status-label { font-size: 0.7rem; font-weight: 700; letter-spacing: 0.04em; padding: 2px 8px; border-radius: 4px; }
.case-card.pass .status-label { color: var(--good); }
.case-card.fail .status-label { color: var(--critical); }
.case-card.expected-fail .status-label { color: var(--warning); }
.metric-badge { font-size: 0.68rem; padding: 2px 7px; border-radius: 999px; border: 1px solid var(--border); color: var(--ink-muted); }
.metric-badge.ok { color: var(--good); border-color: var(--good); }
.metric-badge.bad { color: var(--critical); border-color: var(--critical); }
.case-detail { border-top: 1px solid var(--border); padding: 14px 16px 18px; }
.failure-note { font-size: 0.85rem; color: var(--ink-2); background: var(--page); border-left: 3px solid var(--warning);
  padding: 8px 12px; border-radius: 4px; margin-bottom: 14px; }
.trace-rail { display: flex; flex-direction: column; gap: 0; }
.step { display: flex; gap: 12px; padding: 10px 0; border-bottom: 1px dashed var(--grid); }
.step:last-child { border-bottom: none; }
.step-num { flex: none; width: 22px; height: 22px; border-radius: 50%; background: var(--page);
  color: var(--ink-muted); font-size: 0.72rem; display: flex; align-items: center; justify-content: center; }
.final-step .step-num { background: var(--good); color: #fff; }
.step-body { flex: 1; min-width: 0; }
.tool-chip { display: inline-block; font-family: ui-monospace, monospace; font-size: 0.72rem;
  background: var(--page); color: var(--series-1); border: 1px solid var(--border); border-radius: 4px;
  padding: 1px 7px; margin-bottom: 6px; }
.sql { font-family: ui-monospace, monospace; font-size: 0.76rem; white-space: pre-wrap; word-break: break-word;
  background: var(--page); border-radius: 6px; padding: 8px 10px; margin: 0 0 6px; color: var(--ink-2); }
.observation { font-family: ui-monospace, monospace; font-size: 0.74rem; color: var(--ink-muted);
  white-space: pre-wrap; word-break: break-word; }
.final-answer { font-size: 0.9rem; }
.chart-svg { width: 100%; height: auto; margin: 4px 0 16px; }
.bar { fill: var(--series-1); }
.baseline { stroke: var(--baseline); stroke-width: 1; }
.axis-label { fill: var(--ink-muted); font-size: 10px; }
.value-label { fill: var(--ink-2); font-size: 10px; font-variant-numeric: tabular-nums; }
footer { color: var(--ink-muted); font-size: 0.78rem; margin-top: 28px; }
"""


def render_stat_tile(label, value, sublabel=""):
    return (f'<div class="tile"><div class="tile-label">{esc(label)}</div>'
            f'<div class="tile-value">{esc(value)}</div>'
            f'<div class="tile-sub">{esc(sublabel)}</div></div>')


def render_bar_chart(x, y, title):
    width, height = 640, 220
    pad_left, pad_bottom, pad_top, pad_right = 12, 30, 24, 16
    plot_w = width - pad_left - pad_right
    plot_h = height - pad_bottom - pad_top
    max_y = max(y) * 1.15 if y else 1
    n = len(x) or 1
    bar_gap = 14
    bar_w = (plot_w - bar_gap * (n - 1)) / n

    bars, labels = [], []
    for i, (xi, yi) in enumerate(zip(x, y)):
        bar_h = (yi / max_y) * plot_h if max_y else 0
        bx = pad_left + i * (bar_w + bar_gap)
        by = pad_top + (plot_h - bar_h)
        bars.append(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" rx="4" class="bar">'
                     f'<title>{esc(xi)}: {yi:,.2f}</title></rect>')
        labels.append(f'<text x="{bx + bar_w / 2:.1f}" y="{height - pad_bottom + 16}" class="axis-label" '
                       f'text-anchor="middle">{esc(xi)}</text>')
        labels.append(f'<text x="{bx + bar_w / 2:.1f}" y="{by - 6:.1f}" class="value-label" '
                       f'text-anchor="middle">{yi:,.0f}</text>')

    baseline_y = pad_top + plot_h
    return (f'<svg viewBox="0 0 {width} {height}" class="chart-svg" role="img" aria-label="{esc(title)}">'
            f'<line x1="{pad_left}" y1="{baseline_y}" x2="{width - pad_right}" y2="{baseline_y}" class="baseline" />'
            f'{"".join(bars)}{"".join(labels)}</svg>')


def render_trace(trace):
    parts = []
    for i, step in enumerate(trace["steps"], start=1):
        if step["type"] == "tool":
            args = step["args"]
            body = (f'<pre class="sql">{esc(args["query"])}</pre>' if "query" in args
                    else f'<pre class="sql">{esc(json.dumps(args))}</pre>')
            obs_text = json.dumps(step["observation"]) if step["observation"] is not None else (step.get("error") or "")
            parts.append(
                f'<div class="step"><div class="step-num">{i}</div><div class="step-body">'
                f'<span class="tool-chip">{esc(step["tool"])}</span>{body}'
                f'<div class="observation">{esc(obs_text)}</div></div></div>'
            )
        else:
            parts.append(
                f'<div class="step final-step"><div class="step-num">&#10003;</div><div class="step-body">'
                f'<div class="final-answer">{esc(step["answer"])}</div></div></div>'
            )
    return "".join(parts)


def render_case(entry):
    trace, score = entry["trace"], entry["score"]
    if score["overall_pass"]:
        status_class, status_label = "pass", "PASS"
    elif score["is_honest_failure"]:
        status_class, status_label = "expected-fail", "EXPECTED FAIL"
    else:
        status_class, status_label = "fail", "FAIL"

    def badge(name, ok):
        return f'<span class="metric-badge {"ok" if ok else "bad"}">{name}</span>'

    badges = (badge("tool_choice", score["tool_choice"]["score"] == 1.0)
              + badge("answer_match", score["answer_match"]["score"] == 1.0)
              + badge("faithfulness", score["faithfulness"]["score"] >= 0.5))

    note = f'<div class="failure-note">{esc(score["failure_note"])}</div>' if score.get("failure_note") else ""

    chart_html = ""
    for step in trace["steps"]:
        if step["type"] == "tool" and step["tool"] == "chart":
            obs = step["observation"]
            chart_html = render_bar_chart(obs["x"], obs["y"], obs["title"])

    return (
        f'<details class="case-card {status_class}"><summary>'
        f'<span class="status-dot"></span>'
        f'<span class="case-id">{esc(score["case_id"])}</span>'
        f'<span class="case-question">{esc(score["question"])}</span>'
        f'<span class="status-label">{status_label}</span>{badges}'
        f'</summary><div class="case-detail">{note}{chart_html}'
        f'<div class="trace-rail">{render_trace(trace)}</div></div></details>'
    )


def generate_report(results, aggregate, report_path):
    tiles = "".join([
        render_stat_tile("Overall pass rate", f'{aggregate["overall_pass_rate"] * 100:.0f}%',
                          f'{aggregate["n_cases"]} cases'),
        render_stat_tile("Tool choice", f'{aggregate["tool_choice_avg"] * 100:.0f}%'),
        render_stat_tile("Answer match", f'{aggregate["answer_match_avg"] * 100:.0f}%'),
        render_stat_tile("Faithfulness", f'{aggregate["faithfulness_avg"] * 100:.0f}%',
                          aggregate["faithfulness_method"]),
        render_stat_tile("Avg latency", f'{aggregate["avg_latency_seconds"] * 1000:.1f} ms'),
        render_stat_tile("Tool calls", str(aggregate["total_tool_calls"])),
    ])

    honest_banner = ""
    if aggregate["honest_failures"]:
        ids = ", ".join(aggregate["honest_failures"])
        honest_banner = (
            f'<div class="honest-banner">Deliberate failure case(s) left visible: <code>{esc(ids)}</code> '
            f'&mdash; grounded in its own tool observation, but the wrong metric. Left in the suite on '
            f'purpose; expand it below to see the trace.</div>'
        )

    cases_html = "".join(render_case(r) for r in results)

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agent Eval Report</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
  <h1>Data-Analyst Agent &mdash; Eval Report</h1>
  <p class="subtitle">provider: {esc(aggregate["provider"])} &middot; {aggregate["n_cases"]} cases &middot;
    tool-choice / answer-match / faithfulness scored independently per case</p>
  <div class="tile-strip">{tiles}</div>
  {honest_banner}
  <div class="section-title">Cases</div>
  {cases_html}
  <footer>Self-contained report &mdash; generated by src/eval/run_eval.py, no external assets.</footer>
</div>
</body>
</html>"""

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(html, encoding="utf-8")
