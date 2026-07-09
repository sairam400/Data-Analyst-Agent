# AI Data Analyst Agent

## Problem

Answering a business question over a database usually means someone who knows
SQL sits between the question and the answer. I got tired of being that
person, so I built an agent that closes the gap: ask it a plain-English
question about your data, and it plans the analysis, writes and runs SQL and
Python itself, corrects its own mistakes when a query errors out, and comes
back with an answer, a chart, and a full trace of every step it took to get
there.

Honestly, the trace matters more than the chart. A confident wrong answer
from an LLM is worse than no answer at all, so I wanted a way to check its
work, not just read its conclusion.

## Demo

*(demo GIF goes here: ask a question, watch the trace panel expand with the
SQL it ran, the retry after a deliberate query error, and the resulting
chart)*

## Architecture

```
   Browser
      |
      | HTTP (fetch)
      v
+-----------------------+
|  React frontend        |
|  chat + trace panel    |
+-----------+-----------+
            |
            v
+-----------------------+
|  FastAPI backend       |
|  /ask  /upload  /schema|
+-----------+-----------+
            |
            v
+-----------------------+
|  Agent loop            |
|  plan -> tool call ->  |
|  observe -> repeat     |
|  max 8 calls,          |
|  3 retries per step    |
+-----------+-----------+
     |      |      |      |
     v      v      v      v
get_schema run_sql run_python make_chart
     |      |      |      |
     +------+------+------+
            |
            v
   SQLite (default) or Postgres
            ^
            |
       CSV upload

LLM provider is picked by config, not code:
Anthropic Claude  |  OpenAI / Azure OpenAI / any OpenAI-compatible endpoint
```

## Quickstart

Docker (needs only `ANTHROPIC_API_KEY` in `.env`):

```
cp .env.example .env   # fill in ANTHROPIC_API_KEY
docker compose up
```

Backend on `http://localhost:8000`, frontend on `http://localhost:5173`.

Without Docker (Python 3.11+, Node 18+):

```
pip install -r requirements.txt
python -m src.data.seed
uvicorn src.api.main:app --reload

cd frontend
npm install
npm run dev
```

Want OpenAI, Azure OpenAI, or some other OpenAI-compatible endpoint instead
of Claude? Set `LLM_PROVIDER` and the matching `OPENAI_*` vars in `.env` (see
`.env.example`). No code changes needed, every provider implements the same
interface, see `src/agent/providers/base.py`.

You don't need the server running to try the agent. The CLI and REPL talk to
it directly:

```
python -m src.agent.demo_cli --provider anthropic --question "What was our revenue in March?"
python -m src.agent.repl --provider anthropic
```

Tests: `python -m unittest discover -s tests`

## Eval results

Provider: `mock` &middot; 15 cases &middot; faithfulness method: `heuristic-grounding`

Overall pass rate: **93%** &middot; avg tool calls: **1.13** &middot; avg retries: **0.00**

| case | status | tool calls | retries |
|---|---|---|---|
| `total_revenue_all` | PASS | 1 | 0 |
| `avg_order_value` | EXPECTED FAIL | 1 | 0 |
| `top_category_by_revenue` | PASS | 1 | 0 |
| `top_product_by_units` | PASS | 1 | 0 |
| `total_returns_count` | PASS | 1 | 0 |
| `most_common_return_reason` | PASS | 1 | 0 |
| `return_rate_electronics` | PASS | 2 | 0 |
| `monthly_revenue_trend` | PASS | 2 | 0 |
| `q1_revenue` | PASS | 1 | 0 |
| `net_revenue_after_returns` | PASS | 1 | 0 |
| `top_customer_by_spend` | PASS | 1 | 0 |
| `avg_unit_price_electronics_products` | PASS | 1 | 0 |
| `revenue_apparel` | PASS | 1 | 0 |
| `profit_margin_best_seller` | PASS | 1 | 0 |
| `customer_email_lookup` | PASS | 1 | 0 |

That's the mock provider: scripted plans that still run real tool calls
against the real database, so it proves the tool layer and the scoring work,
not that the model reasons well. For that, run
`python -m src.eval.run_eval --provider anthropic` (or `--provider openai`)
to send the same 15 questions through a real model. I didn't wire that into
CI here since it costs real tokens and needs a real key, but the regenerated
table, the full HTML report, and the raw JSON all land in `reports/` when you
run it yourself.

Every case gets scored three separate ways, and I mean that literally, three
independent checks, not one score with three inputs: `tool_choice` (did it
call the right tools), `answer_match` (does the final number or name match
ground truth, computed by a reference query I wrote independently of the
agent), and `faithfulness` (is every number in the answer traceable to
something a tool actually returned). `avg_order_value` fails on purpose: the
scripted plan answers with average unit price per line item instead of
average order value, a genuinely easy metric to conflate. It's grounded in
its own query (faithfulness passes) but it's the wrong number (answer_match
fails), which is the whole point of scoring these separately instead of
collapsing to one pass/fail. `profit_margin_best_seller` and
`customer_email_lookup` are deliberately unanswerable (there's no cost data
and no email column in this schema) and they pass when the agent admits that
instead of guessing.

## Design decisions

**Read-only SQL is enforced at the tool layer, not the prompt.** `run_sql`
rejects anything that isn't a `SELECT`, and rejects a `SELECT` that smuggles
in a mutating statement after a semicolon. Telling the model "only run
read-only queries" in the system prompt is not a safety boundary. A regex
check on every query the tool actually executes is.

**Providers are one interface, not one implementation.** Every provider
implements `next_action(case_id, question, history)` and translates the
neutral tool specs into its own wire format. Anthropic and an
OpenAI-compatible provider (covers OpenAI, Azure OpenAI, or a self-hosted
endpoint) exist today. Adding a new one means writing a new adapter file, not
touching the agent loop.

**Self-correction has a hard stop.** A tool error gets fed back so the model
can repair its own query, which works more often than I expected. But
nothing about an LLM guarantees it eventually gives up on a broken approach,
so the agent tracks consecutive errors from the same tool and cuts it off
with an honest failure message after 3 in a row, instead of quietly burning
the rest of its step budget on a retry that was never going to work.

**What didn't work: a real sandbox for `run_python`.** I wanted a sandboxed
Python tool with no filesystem access outside its own working directory.
What I actually shipped is process-level isolation: a fresh subprocess, a
scratch working directory, a stripped environment, network sockets disabled.
That stops the obvious stuff, but it doesn't stop code that opens an
absolute path outside the scratch directory. Doing that properly needs a
container or an OS-level sandbox (gVisor, seccomp, a locked-down container),
and I cut it for scope. That's a real gap, not a rounding error, so
`run_python` shouldn't run against anything but a local demo instance. Full
writeup in `KNOWN_ISSUES.md`.

## Known limitations

See `KNOWN_ISSUES.md` for the rest, including the `run_python` sandbox
boundary and how CSV upload and Postgres mode don't currently play together.
