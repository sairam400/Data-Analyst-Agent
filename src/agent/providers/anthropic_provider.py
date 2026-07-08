"""Drives the agent loop with Claude's native tool-use API."""
import json

from .base import Provider
from .prompts import SYSTEM_PROMPT
from ..tools import TOOL_SPECS
from ...config import SETTINGS


def _to_anthropic_tools():
    return [
        {
            "name": spec["name"],
            "description": spec["description"],
            "input_schema": spec["parameters"],
        }
        for spec in TOOL_SPECS
    ]


class AnthropicProvider(Provider):
    def __init__(self, model=None, client=None):
        if client is None:
            import anthropic
            client = anthropic.Anthropic(api_key=SETTINGS.anthropic_api_key) if SETTINGS.anthropic_api_key \
                else anthropic.Anthropic()
        self.client = client
        self.model = model or SETTINGS.anthropic_model
        self._tools = _to_anthropic_tools()

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
            tools=self._tools,
            messages=self._build_messages(question, history),
        )

        tool_use = next((b for b in response.content if b.type == "tool_use"), None)
        if tool_use is not None:
            return {"type": "tool", "tool": tool_use.name, "args": tool_use.input}

        text = "".join(b.text for b in response.content if b.type == "text")
        return {"type": "final", "answer": text.strip()}
