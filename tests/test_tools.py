import unittest

from src.agent.tools import ToolError, calculator, sql_query


class TestSqlQueryGuard(unittest.TestCase):
    def test_rejects_non_select(self):
        with self.assertRaises(ToolError):
            sql_query({"query": "DELETE FROM orders"})

    def test_rejects_select_with_embedded_mutation(self):
        with self.assertRaises(ToolError):
            sql_query({"query": "SELECT 1; DROP TABLE orders;"})

    def test_allows_plain_select(self):
        rows = sql_query({"query": "SELECT COUNT(*) AS n FROM products"})
        self.assertEqual(len(rows), 1)
        self.assertIn("n", rows[0])


class TestCalculator(unittest.TestCase):
    def test_basic_arithmetic(self):
        self.assertEqual(calculator({"expression": "2 + 3 * 4"})["result"], 14)

    def test_rejects_non_arithmetic(self):
        with self.assertRaises(ToolError):
            calculator({"expression": "__import__('os').system('echo hi')"})

    def test_rejects_name_lookup(self):
        with self.assertRaises(ToolError):
            calculator({"expression": "os.getcwd()"})


if __name__ == "__main__":
    unittest.main()
