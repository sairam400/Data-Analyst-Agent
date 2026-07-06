# Agent1 — a data-analyst agent, evaluated end to end

A tool-using agent that answers natural-language business questions over a small
recommerce SQLite database, plus the eval harness that measures it. The harness
is the point of this repo, not the agent — a flashy demo is easy; an honest,
reproducible evaluation of one is the harder and more useful thing to show.

## What's here

```
src/agent/       ReAct loop (agent.py), tools (tools.py), providers (providers.py)
src/data/        schema.sql + seed.py — deterministic synthetic recommerce data
src/eval/        dataset.py (16 gold cases), scorers.py, run_eval.py, report.py
tests/           unit tests for the SQL/calculator guards and the scorers themselves
reports/         generated results.json + report.html (gitignored's the .db, not these)
```

## Run it

```
pip install -r requirements.txt   # only needed for --provider anthropic
python -m src.eval.run_eval --provider mock
```

This seeds `data/business.db` if it doesn't exist, runs all 16 cases, and writes
`reports/report.html` — open it directly, no server needed. Everything renders
inline (SVG charts, no CDN, `<details>` for expand/collapse) so it's a single
file you can email.

To run the same agent loop against a real model instead of the scripted mock:

```
export ANTHROPIC_API_KEY=...
python -m src.eval.run_eval --provider anthropic --model claude-sonnet-5
```

Same tools, same dataset, same scorers — only the decision-maker changes.
Add `--llm-judge` to score faithfulness with a real Claude call instead of the
deterministic grounding heuristic (see below).

Run the unit tests: `python -m unittest discover -s tests`

## The agent

A ReAct-style loop (`src/agent/agent.py`) with three tools: `sql_query`
(read-only — rejects anything that isn't a `SELECT`, and rejects `SELECT`s that
smuggle in a mutating statement), `calculator` (an AST-walking safe evaluator,
not `eval()` — only numeric literals and `+ - * / % **`), and `chart` (records
a series for the report to render).

The domain: products, customers, orders, order_items, returns — a small
recommerce dataset, seeded deterministically (`random.seed(42)`) so gold
answers stay valid across re-seeds.

## The eval harness — the actual point

Every case scores on three independent axes:

- **tool_choice** — did the agent call the tools the question needs? (process)
- **answer_match** — does the final answer match ground truth, within
  tolerance? Ground truth is computed by a query written independently of the
  agent's own query — never by re-running what the agent did, which would make
  this check circular.
- **faithfulness** — is every number in the final answer traceable to a tool
  observation? This is checked *separately* from answer_match on purpose:
  an answer can be perfectly grounded in what a tool returned and still be
  wrong, if the agent asked the tool the wrong question. That's a distinct
  failure mode from hallucinating a number outright, and conflating the two
  hides it.

Faithfulness defaults to a deterministic grounding heuristic (numbers in the
answer must appear in some tool observation, with ISO-date tokens excluded so
"2025-02" doesn't get misread as two numbers) rather than an LLM judge, so the
suite is reproducible and runs free/offline. `--llm-judge` swaps in a real
Claude call for a qualitative faithfulness rating when you want that instead —
the report labels which method produced each score, since "faithfulness: 1.0"
means something different depending on which one ran.

### The one deliberate failure

`avg_order_value` fails on purpose. Asked for average *order* value, the
scripted plan computes average *unit price per line item* instead — a
genuinely easy metric to conflate, since both come from the same table.

- `tool_choice`: 1.0 — it called `sql_query`, which is all this question needs.
- `answer_match`: 0.0 — $82.23 vs. the correct $217.56. Wrong metric.
- `faithfulness`: 1.0 — $82.23 is exactly what its query returned. It didn't
  make anything up; it asked the database the wrong question.

That combination — grounded but wrong — is the whole reason to score these
three things separately instead of collapsing to a single pass/fail. It's left
in the suite rather than tuned away.

### How the mock stays honest

`MockProvider` (`src/agent/providers.py`) replays a scripted plan per test
case so the suite is deterministic and free to run in CI. The plan only
scripts the *decision* — which tool to call, what to say — every tool call it
issues still executes for real against the seeded SQLite database. The final
answer is built from the tool's actual return value (`obs[0][0]['rev']`, etc.),
never from the gold answer directly. That's what keeps the mock an honest
stand-in for a reasoning model rather than a rigged demo that can't fail.

## Known limitations

- 16 gold cases is enough to demonstrate the harness design, not enough to be
  a statistically meaningful benchmark — a real deployment would want low
  hundreds, sampled across more question shapes (ambiguous questions, multi-
  hop questions, adversarial inputs).
- The mock's "reasoning" is scripted per case; it validates the harness and
  the tool-execution path, not an actual model's tool-selection judgment. The
  `--provider anthropic` path is what evaluates real reasoning, and needs an
  API key to run.
- Faithfulness's default grounding heuristic checks numbers only; it wouldn't
  catch a fabricated non-numeric claim (e.g. a made-up return reason). The
  `--llm-judge` path is the mitigation, at the cost of determinism.
