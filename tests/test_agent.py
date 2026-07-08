import unittest

from src.agent.agent import Agent
from src.agent.tools import ToolError


def broken_tool(args):
    raise ToolError("simulated failure")


def flaky_tool(args):
    raise ToolError("one-off failure")


class AlwaysErrorProvider:
    def next_action(self, case_id, question, history):
        return {"type": "tool", "tool": "broken_tool", "args": {}}


class RecoversAfterOneErrorProvider:
    def __init__(self):
        self.calls = 0

    def next_action(self, case_id, question, history):
        self.calls += 1
        if self.calls == 1:
            return {"type": "tool", "tool": "flaky_tool", "args": {}}
        return {"type": "final", "answer": "done"}


class TestAgentRetryCap(unittest.TestCase):
    def test_stops_after_max_consecutive_errors_instead_of_burning_max_steps(self):
        agent = Agent(
            AlwaysErrorProvider(),
            tools={"broken_tool": broken_tool},
            max_steps=8,
            max_consecutive_errors=3,
        )
        trace = agent.run("case", "question")
        tool_steps = [s for s in trace["steps"] if s["type"] == "tool"]
        self.assertEqual(len(tool_steps), 3)
        self.assertIn("simulated failure", trace["final_answer"])
        self.assertEqual(trace["retries"], 2)

    def test_single_error_does_not_trigger_forced_termination(self):
        agent = Agent(RecoversAfterOneErrorProvider(), tools={"flaky_tool": flaky_tool})
        trace = agent.run("case", "question")
        self.assertEqual(trace["final_answer"], "done")
        self.assertEqual(trace["retries"], 0)


if __name__ == "__main__":
    unittest.main()
