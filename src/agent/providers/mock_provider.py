"""Replays dataset-defined plans so the eval suite is deterministic and free
to run in CI. Every tool call in a plan still executes for real against the
seeded SQLite DB; only the *decision* of which tool to call and what to say is
scripted, not the tool's result. That is what keeps the mock honest rather
than a rigged demo."""
from .base import Provider
from ..agent import obs_list


class MockProvider(Provider):
    """plans: dict[case_id -> list[step]].

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
