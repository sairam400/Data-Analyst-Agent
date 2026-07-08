import base64
import unittest

from src.agent.tools import ToolError, get_schema, make_chart, run_python, run_sql


class TestGetSchema(unittest.TestCase):
    def test_returns_schema_text(self):
        result = get_schema()
        self.assertIn("products", result["schema"])
        self.assertIn("order_items", result["schema"])


class TestRunSqlGuard(unittest.TestCase):
    def test_rejects_non_select(self):
        with self.assertRaises(ToolError):
            run_sql({"query": "DELETE FROM orders"})

    def test_rejects_select_with_embedded_mutation(self):
        with self.assertRaises(ToolError):
            run_sql({"query": "SELECT 1; DROP TABLE orders;"})

    def test_allows_plain_select(self):
        rows = run_sql({"query": "SELECT COUNT(*) AS n FROM products"})
        self.assertEqual(len(rows), 1)
        self.assertIn("n", rows[0])


class TestRunPython(unittest.TestCase):
    def test_prints_stdout(self):
        result = run_python({"code": "print(2 + 2)"})
        self.assertEqual(result["stdout"].strip(), "4")

    def test_raises_on_uncaught_exception(self):
        with self.assertRaises(ToolError):
            run_python({"code": "raise ValueError('boom')"})

    def test_network_access_is_blocked(self):
        with self.assertRaises(ToolError):
            run_python({"code": "import socket; socket.socket().connect(('example.com', 80))"})

    def test_infinite_loop_times_out(self):
        with self.assertRaises(ToolError):
            run_python({"code": "while True: pass", "timeout": 1})

    def test_runs_in_isolated_scratch_dir(self):
        result = run_python({"code": "import os; print(os.getcwd())"})
        self.assertIn("sandbox", result["stdout"])


class TestMakeChart(unittest.TestCase):
    def test_returns_base64_png(self):
        result = make_chart({"kind": "bar", "x": ["a", "b"], "y": [1, 2], "title": "t"})
        raw = base64.b64decode(result["image_base64"])
        self.assertTrue(raw.startswith(b"\x89PNG"))

    def test_rejects_mismatched_series_lengths(self):
        with self.assertRaises(ToolError):
            make_chart({"kind": "bar", "x": ["a"], "y": [1, 2], "title": "t"})

    def test_rejects_unsupported_kind(self):
        with self.assertRaises(ToolError):
            make_chart({"kind": "pie", "x": ["a"], "y": [1], "title": "t"})


if __name__ == "__main__":
    unittest.main()
