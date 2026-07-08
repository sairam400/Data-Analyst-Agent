import unittest

from src.eval.scorers import score_answer_match, score_faithfulness, score_tool_choice

CASE_NUMERIC = {"answer_type": "numeric", "gold_answer": 100.0, "tolerance": 0.5,
                "expected_tools": {"sql_query"}, "question": "What was revenue in 2025?"}
CASE_STRING = {"answer_type": "string", "gold_answer": "Electronics",
               "expected_tools": {"sql_query"}, "question": "Top category?"}


def trace_with(final_answer, tool_calls=("sql_query",), steps=None):
    return {
        "final_answer": final_answer,
        "tool_calls": list(tool_calls),
        "steps": steps or [{"type": "tool", "observation": [{"rev": 100.0}], "error": None}],
    }


class TestToolChoice(unittest.TestCase):
    def test_passes_when_expected_subset_of_actual(self):
        trace = trace_with("x", tool_calls=("sql_query", "calculator"))
        self.assertEqual(score_tool_choice(CASE_NUMERIC, trace)["score"], 1.0)

    def test_fails_when_expected_tool_missing(self):
        trace = trace_with("x", tool_calls=("calculator",))
        self.assertEqual(score_tool_choice(CASE_NUMERIC, trace)["score"], 0.0)


class TestAnswerMatch(unittest.TestCase):
    def test_numeric_within_tolerance_passes(self):
        trace = trace_with("Revenue was $100.20.")
        self.assertEqual(score_answer_match(CASE_NUMERIC, trace)["score"], 1.0)

    def test_numeric_outside_tolerance_fails(self):
        trace = trace_with("Revenue was $50.00.")
        self.assertEqual(score_answer_match(CASE_NUMERIC, trace)["score"], 0.0)

    def test_string_case_insensitive_match(self):
        trace = trace_with("The top category is electronics.")
        self.assertEqual(score_answer_match(CASE_STRING, trace)["score"], 1.0)


class TestUnanswerable(unittest.TestCase):
    CASE = {"answer_type": "unanswerable", "gold_answer": None,
            "expected_tools": {"get_schema"}, "question": "What is the customer's email?"}

    def test_honest_decline_passes(self):
        trace = trace_with("I can't answer that — there's no email column in this schema.")
        self.assertEqual(score_answer_match(self.CASE, trace)["score"], 1.0)

    def test_fabricated_answer_fails(self):
        trace = trace_with("Their email is alice@example.com.")
        self.assertEqual(score_answer_match(self.CASE, trace)["score"], 0.0)


class TestFaithfulness(unittest.TestCase):
    def test_grounded_number_passes(self):
        trace = trace_with("Revenue was $100.00.")
        self.assertEqual(score_faithfulness(CASE_NUMERIC, trace)["score"], 1.0)

    def test_fabricated_number_fails(self):
        trace = trace_with("Revenue was $999.00.")
        self.assertEqual(score_faithfulness(CASE_NUMERIC, trace)["score"], 0.0)

    def test_year_restated_from_question_is_not_fabrication(self):
        trace = trace_with("Revenue in 2025 was $100.00.")
        self.assertEqual(score_faithfulness(CASE_NUMERIC, trace)["score"], 1.0)

    def test_iso_date_in_answer_not_misparsed_as_number(self):
        case = {**CASE_NUMERIC, "question": "Which month?"}
        steps = [{"type": "tool", "observation": [{"month": "2025-02", "rev": 100.0}], "error": None}]
        trace = trace_with("2025-02 had revenue of $100.00.", steps=steps)
        self.assertEqual(score_faithfulness(case, trace)["score"], 1.0)


if __name__ == "__main__":
    unittest.main()
