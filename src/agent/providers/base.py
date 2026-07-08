"""Every provider implements next_action(case_id, question, history) ->
{"type": "tool", "tool": name, "args": dict} | {"type": "final", "answer": str}.

A provider's only job is translating the neutral TOOL_SPECS (src/agent/tools.py)
into its own SDK's tool-calling wire format, and translating the response back
into that shape. That's what makes swapping the underlying LLM a config change
(LLM_PROVIDER in .env) rather than a code change — see providers/__init__.py.
"""


class Provider:
    def next_action(self, case_id, question, history):
        raise NotImplementedError
