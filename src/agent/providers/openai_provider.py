"""Drives the agent loop against the OpenAI chat-completions function-calling
API. One class covers OpenAI, Azure OpenAI, and any OpenAI-compatible endpoint
(Groq, vLLM, a local server, ...), since they all speak the same wire format —
only base_url / api_version / api_key / model differ, all supplied via config
(src/config.py, OPENAI_* env vars). Set OPENAI_API_VERSION to route through
the Azure client; leave it unset for plain OpenAI or an OpenAI-compatible base_url.
"""
import json

from .base import Provider
from .prompts import SYSTEM_PROMPT
from ..tools import TOOL_SPECS
from ...config import SETTINGS


def _to_openai_tools():
    return [
        {
            "type": "function",
            "function": {
                "name": spec["name"],
                "description": spec["description"],
                "parameters": spec["parameters"],
            },
        }
        for spec in TOOL_SPECS
    ]


class OpenAIProvider(Provider):
    def __init__(self, model=None, client=None):
        if client is None:
            import openai
            if SETTINGS.openai_api_version:
                client = openai.AzureOpenAI(
                    api_key=SETTINGS.openai_api_key,
                    azure_endpoint=SETTINGS.openai_base_url,
                    api_version=SETTINGS.openai_api_version,
                )
            else:
                kwargs = {}
                if SETTINGS.openai_api_key:
                    kwargs["api_key"] = SETTINGS.openai_api_key
                if SETTINGS.openai_base_url:
                    kwargs["base_url"] = SETTINGS.openai_base_url
                client = openai.OpenAI(**kwargs)
        self.client = client
        self.model = model or SETTINGS.openai_model
        self._tools = _to_openai_tools()

    def _build_messages(self, question, history):
        messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": question}]
        for step in history:
            if step["type"] != "tool":
                continue
            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": step["id"],
                    "type": "function",
                    "function": {"name": step["tool"], "arguments": json.dumps(step["args"])},
                }],
            })
            content = step["error"] if step["error"] else json.dumps(step["observation"])
            messages.append({"role": "tool", "tool_call_id": step["id"], "content": content})
        return messages

    def next_action(self, case_id, question, history):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self._build_messages(question, history),
            tools=self._tools,
        )
        message = response.choices[0].message
        if message.tool_calls:
            call = message.tool_calls[0]
            return {"type": "tool", "tool": call.function.name, "args": json.loads(call.function.arguments)}
        return {"type": "final", "answer": (message.content or "").strip()}
