"""Two providers behind the same next_action(case_id, question, history) API.

MockProvider replays a scripted plan per test case — deterministic and free,
so the whole eval suite runs offline in CI. Every tool call in a plan still
executes for real against the seeded SQLite DB; only the *decision* of which
tool to call and what to say is scripted, not the tool's result. That is what
keeps the mock honest rather than a rigged demo.

AnthropicProvider drives the same tool loop with a real Claude model call, so
swapping --provider mock -> --provider anthropic exercises the identical
Agent/tool code path against genuine model reasoning.
"""
import json

from .agent import obs_list
from .tools import SCHEMA_DESCRIPTION, TOOL_SPECS

SYSTEM_PROMPT = f"""You are a data analyst agent for a recommerce business.
Answer the user's question using the available tools. The database schema is:

{SCHEMA_DESCRIPTION}

Always ground numeric claims in a tool observation — call sql_query (and
calculator if arithmetic beyond SQL is needed) before giving a final answer.
Give the final answer as plain text, not a tool call, once you have enough
information."""


class MockProvider:
    """Replays dataset-defined plans. plans: dict[case_id -> list[step]].

    Each step is either:
      {"type": "tool", "tool": name, "args": dict | callable(obs_list) -> dict}
      {"type": "final", "fn": callable(obs_list) -> str}
    """

    def __init__(self, plans):
        self.plans = plans

    def next_action(self, case_id, question, history):
        plan = self.plans[case_id]
        step_index = len(history)
        if step_index >= len(plan):
            return {"type": "final", "answer": "(mock plan exhausted)"}

        step = plan[step_index]
        observations = obs_list(history)

        if step["type"] == "tool":
            args = step["args"](observations) if callable(step["args"]) else step["args"]
            return {"type": "tool", "tool": step["tool"], "args": args}

        return {"type": "final", "answer": step["fn"](observations)}


def _load_dotenv_key():
    """Falls back to a local, gitignored .env file (KEY=VALUE lines) if
    ANTHROPIC_API_KEY isn't already in the environment — lets the key live
    only in an untracked file on disk, never typed into a shell command."""
    import os
    from pathlib import Path

    if os.environ.get("ANTHROPIC_API_KEY"):
        return os.environ["ANTHROPIC_API_KEY"]

    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return None
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line.startswith("ANTHROPIC_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


class AnthropicProvider:
    def __init__(self, model="claude-sonnet-5", client=None):
        if client is None:
            import anthropic
            api_key = _load_dotenv_key()
            client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
        self.client = client
        self.model = model

    def _build_messages(self, question, history):
        messages = [{"role": "user", "content": question}]
        for step in history:
            if step["type"] != "tool":
                continue
            messages.append({
                "role": "assistant",
                "content": [{
                    "type": "tool_use",
                    "id": step["id"],
                    "name": step["tool"],
                    "input": step["args"],
                }],
            })
            result_content = step["error"] if step["error"] else json.dumps(step["observation"])
            messages.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": step["id"],
                    "content": result_content,
                    "is_error": bool(step["error"]),
                }],
            })
        return messages

    def next_action(self, case_id, question, history):
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOL_SPECS,
            messages=self._build_messages(question, history),
        )

        tool_use = next((b for b in response.content if b.type == "tool_use"), None)
        if tool_use is not None:
            return {"type": "tool", "tool": tool_use.name, "args": tool_use.input}

        text = "".join(b.text for b in response.content if b.type == "text")
        return {"type": "final", "answer": text.strip()}
