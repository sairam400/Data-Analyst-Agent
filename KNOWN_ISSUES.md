# Known issues

**`run_python` is not a real sandbox.** It runs in its own subprocess, in a
scratch working directory, with a stripped environment and network sockets
disabled. That stops the easy cases (network calls, obvious filesystem
writes in the current directory) but does not stop code that opens an
absolute path outside the scratch directory. A real boundary needs a
container or an OS-level sandbox (gVisor, seccomp, a locked-down container),
which was cut for scope. Don't expose this tool on anything but a trusted,
local demo instance.

**CSV upload and Postgres mode don't compose.** `/upload` always writes the
new table into the bundled SQLite database (`data/business.db`). If
`DATABASE_URL` is set to point `run_sql`/`get_schema` at Postgres instead, an
uploaded CSV won't be visible until the two data paths are unified. Use one
or the other, not both, until this is fixed.

**The mock eval provider validates the harness, not model reasoning.** Its
scripted plans still execute real tool calls against the real database, so
it catches bugs in the tool layer and the scorers, but the *decision* of
which tool to call is hand-written, not the model's. `--provider anthropic`
and `--provider openai` exercise genuine reasoning over the same 15
questions, at the cost of a real API key and real tokens.

**The OpenAI/Azure OpenAI provider was verified against fake clients, not a
live endpoint.** No OpenAI or Azure credentials were available in the
environment this was built in, so `OpenAIProvider`'s request/response
reshaping was checked with stub clients that mimic the SDK's shapes, not
against a real deployment. The Anthropic path was similarly verified without
a live key past the point where the SDK builds the request (see the FastAPI
backend verification in the commit history) — a real key is needed to
confirm the full round trip against either provider.

**Frontend was verified by production build and a stubbed-backend smoke
test, not a live interactive browser session.** No headless browser was
available in the environment this was built in. `npm run build` and serving
the built bundle were both verified to work, and the API layer was smoke-
tested end to end with a stub provider standing in for the LLM call, but
nobody has actually clicked around the running UI in a real browser yet.
