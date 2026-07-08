"""The ReAct-style agent loop: ask the provider for the next action, execute
tools, feed observations back, repeat until the provider returns a final
answer or max_steps is hit.

Self-correction: a tool error is fed back as an observation so the model can
repair and retry. If the *same* tool call fails max_consecutive_errors times
in a row, the loop stops asking the model and reports the failure honestly
instead of burning the rest of the step budget on a doomed retry."""
import time

from .tools import TOOLS, ToolError

MAX_STEPS = 8
MAX_CONSECUTIVE_ERRORS = 3


def obs_list(history):
    return [step["observation"] for step in history if step["type"] == "tool"]


class Agent:
    def __init__(self, provider, tools=None, max_steps=MAX_STEPS,
                 max_consecutive_errors=MAX_CONSECUTIVE_ERRORS):
        self.provider = provider
        self.tools = tools or TOOLS
        self.max_steps = max_steps
        self.max_consecutive_errors = max_consecutive_errors

    def run(self, case_id, question):
        history = []
        start = time.perf_counter()
        consecutive_errors = 0
        retries = 0

        for step_index in range(self.max_steps):
            if consecutive_errors >= self.max_consecutive_errors:
                last_error = history[-1]["error"]
                history.append({
                    "type": "final",
                    "answer": f"I couldn't complete this after {consecutive_errors} consecutive "
                              f"tool errors. Last error: {last_error}",
                })
                break

            action = self.provider.next_action(case_id, question, history)

            if action["type"] == "final":
                history.append({"type": "final", "answer": action["answer"]})
                break

            tool_name = action["tool"]
            args = action["args"]
            tool_id = f"tool_{step_index}"
            if tool_name not in self.tools:
                observation, error = None, f"unknown tool '{tool_name}'"
            else:
                try:
                    observation, error = self.tools[tool_name](args), None
                except ToolError as exc:
                    observation, error = None, str(exc)

            if error:
                if consecutive_errors > 0:
                    retries += 1
                consecutive_errors += 1
                if consecutive_errors == self.max_consecutive_errors:
                    error += f" (reached {consecutive_errors} consecutive errors, giving up on this approach)"
            else:
                consecutive_errors = 0

            history.append({
                "type": "tool",
                "id": tool_id,
                "tool": tool_name,
                "args": args,
                "observation": observation,
                "error": error,
            })
        else:
            history.append({"type": "final", "answer": "(no answer — max steps reached)"})

        elapsed = time.perf_counter() - start
        final_answer = next(
            (s["answer"] for s in reversed(history) if s["type"] == "final"), ""
        )
        return {
            "case_id": case_id,
            "question": question,
            "steps": history,
            "final_answer": final_answer,
            "elapsed_seconds": round(elapsed, 4),
            "tool_calls": [s["tool"] for s in history if s["type"] == "tool"],
            "retries": retries,
        }
