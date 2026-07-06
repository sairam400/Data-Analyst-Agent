"""Three independent scorers, each catching a different failure mode:

  tool_choice   - process:  did the agent call the tools the question needs?
  answer_match  - outcome:  does the final answer match ground truth (computed
                             by an independent reference query, never by the
                             agent under test)?
  faithfulness  - grounding: is every number in the final answer traceable to
                             a tool observation? (Answering the wrong question
                             faithfully is possible — see avg_order_value in
                             dataset.py — and is exactly what this catches
                             *separately* from answer_match.)

faithfulness defaults to a deterministic grounding check (numbers in the
answer must appear in some tool observation) so the harness runs offline and
reproducibly. score_faithfulness_llm is an optional real LLM-judge, used only
when an Anthropic client is supplied — labelled as such in the report so a
"faithfulness: 1.0" never silently means two different things.
"""
import re

NUMBER_PATTERN = re.compile(r"-?\d[\d,]*\.?\d*")
ISO_DATE_PATTERN = re.compile(r"\b\d{4}-\d{2}(?:-\d{2})?\b")


def _numbers_in_text(text):
    text = ISO_DATE_PATTERN.sub(" ", text or "")
    out = []
    for raw in NUMBER_PATTERN.findall(text):
        try:
            out.append(round(float(raw.replace(",", "")), 2))
        except ValueError:
            continue
    return out


def _bucket(value, numbers, strings):
    if isinstance(value, bool):
        return
    if isinstance(value, (int, float)):
        numbers.add(round(float(value), 2))
    elif isinstance(value, str):
        strings.add(value.lower())
    elif isinstance(value, list):
        for item in value:
            _bucket(item, numbers, strings)


def _flatten_observations(steps):
    numbers, strings = set(), set()
    for step in steps:
        if step["type"] != "tool" or step["observation"] is None:
            continue
        obs = step["observation"]
        rows = obs if isinstance(obs, list) else [obs]
        for row in rows:
            if isinstance(row, dict):
                for value in row.values():
                    _bucket(value, numbers, strings)
            else:
                _bucket(row, numbers, strings)
    return numbers, strings


def score_tool_choice(case, trace):
    expected = set(case["expected_tools"])
    actual = trace["tool_calls"]
    passed = expected.issubset(set(actual))
    return {"method": "deterministic", "score": 1.0 if passed else 0.0,
            "expected": sorted(expected), "actual": actual}


def score_answer_match(case, trace):
    final_answer = trace["final_answer"]
    gold = case["gold_answer"]

    if case["answer_type"] == "numeric":
        tolerance = case.get("tolerance", 0.01)
        candidates = _numbers_in_text(final_answer)
        passed = any(abs(c - gold) <= tolerance for c in candidates)
        return {"method": "deterministic", "score": 1.0 if passed else 0.0,
                "gold": gold, "candidates": candidates, "tolerance": tolerance}

    passed = str(gold).lower() in final_answer.lower()
    return {"method": "deterministic", "score": 1.0 if passed else 0.0,
            "gold": gold, "final_answer": final_answer}


def score_faithfulness(case, trace):
    numbers, _strings = _flatten_observations(trace["steps"])
    numbers |= set(_numbers_in_text(case["question"]))  # restating a given (e.g. "2025") isn't a fabricated claim
    answer_numbers = _numbers_in_text(trace["final_answer"])
    ungrounded = [n for n in answer_numbers if not any(abs(n - g) < 0.05 for g in numbers)]
    passed = len(ungrounded) == 0
    return {"method": "heuristic-grounding", "score": 1.0 if passed else 0.0,
            "answer_numbers": answer_numbers, "ungrounded": ungrounded}


FAITHFULNESS_JUDGE_PROMPT = """You are grading whether an AI agent's final answer is \
FAITHFUL to its own tool observations — i.e. every claim is traceable to what the tools \
actually returned, regardless of whether it answers the right question.

Question: {question}
Tool observations (in order): {observations}
Agent's final answer: {final_answer}

Reply with only a number from 0.0 to 1.0 (1.0 = fully grounded, 0.0 = fabricated/ungrounded), \
then a one-sentence justification on the next line."""


def score_faithfulness_llm(case, trace, client, model="claude-sonnet-5"):
    observations = [s["observation"] for s in trace["steps"] if s["type"] == "tool"]
    prompt = FAITHFULNESS_JUDGE_PROMPT.format(
        question=case["question"], observations=observations, final_answer=trace["final_answer"]
    )
    response = client.messages.create(
        model=model, max_tokens=200, messages=[{"role": "user", "content": prompt}]
    )
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    lines = text.splitlines()
    try:
        score = max(0.0, min(1.0, float(lines[0].strip())))
    except (ValueError, IndexError):
        score = 0.0
    rationale = lines[1].strip() if len(lines) > 1 else text
    return {"method": "llm-judge", "score": score, "rationale": rationale}


def score_case(case, trace, faithfulness_client=None, faithfulness_model="claude-sonnet-5"):
    tool_choice = score_tool_choice(case, trace)
    answer_match = score_answer_match(case, trace)
    if faithfulness_client is not None:
        faithfulness = score_faithfulness_llm(case, trace, faithfulness_client, faithfulness_model)
    else:
        faithfulness = score_faithfulness(case, trace)

    overall_pass = tool_choice["score"] == 1.0 and answer_match["score"] == 1.0 and faithfulness["score"] >= 0.5
    return {
        "case_id": case["id"],
        "question": case["question"],
        "is_honest_failure": case.get("is_honest_failure", False),
        "failure_note": case.get("failure_note"),
        "tool_choice": tool_choice,
        "answer_match": answer_match,
        "faithfulness": faithfulness,
        "overall_pass": overall_pass,
    }
