"""Tools available to the agent: sql_query (read-only), calculator, chart.

Each tool takes a single args dict and returns a JSON-serializable observation.
sql_query and calculator reject anything that isn't safely evaluable, so a
misbehaving agent can't mutate the database or execute arbitrary code.
"""
import ast
import operator
import re
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "business.db"

_READ_ONLY_PATTERN = re.compile(r"^\s*SELECT\b", re.IGNORECASE)
_FORBIDDEN_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|ATTACH|PRAGMA|REPLACE)\b", re.IGNORECASE
)

SCHEMA_DESCRIPTION = """\
products(id, name, category, unit_price)
customers(id, name)
orders(id, customer_id, order_date [YYYY-MM-DD], status)
order_items(id, order_id, product_id, quantity, unit_price)
returns(id, order_item_id, reason, return_date)
"""

_ALLOWED_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
}


class ToolError(Exception):
    pass


def sql_query(args: dict) -> list:
    query = args.get("query", "")
    if not _READ_ONLY_PATTERN.match(query):
        raise ToolError("sql_query only accepts SELECT statements")
    if _FORBIDDEN_PATTERN.search(query):
        raise ToolError("sql_query rejected: mutating/schema statements are not allowed")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(query).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _safe_eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINOPS:
        return _ALLOWED_BINOPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_BINOPS:
        return _ALLOWED_BINOPS[type(node.op)](_safe_eval(node.operand))
    raise ToolError(f"unsupported expression node: {type(node).__name__}")


def calculator(args: dict) -> dict:
    expression = args.get("expression", "")
    try:
        tree = ast.parse(expression, mode="eval")
        result = _safe_eval(tree.body)
    except Exception as exc:
        raise ToolError(f"invalid arithmetic expression '{expression}': {exc}") from exc
    return {"expression": expression, "result": result}


def chart(args: dict) -> dict:
    kind = args.get("kind", "bar")
    x = args.get("x", [])
    y = args.get("y", [])
    title = args.get("title", "")
    if len(x) != len(y):
        raise ToolError("chart: x and y series must be the same length")
    return {"kind": kind, "x": list(x), "y": list(y), "title": title, "rendered": True}


TOOLS = {
    "sql_query": sql_query,
    "calculator": calculator,
    "chart": chart,
}

TOOL_SPECS = [
    {
        "name": "sql_query",
        "description": "Run a read-only SELECT query against the business SQLite database. Schema:\n" + SCHEMA_DESCRIPTION,
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "A single SELECT statement"}},
            "required": ["query"],
        },
    },
    {
        "name": "calculator",
        "description": "Evaluate an arithmetic expression (numbers and + - * / % ** only).",
        "input_schema": {
            "type": "object",
            "properties": {"expression": {"type": "string"}},
            "required": ["expression"],
        },
    },
    {
        "name": "chart",
        "description": "Record a chart to render in the report (bar or line).",
        "input_schema": {
            "type": "object",
            "properties": {
                "kind": {"type": "string", "enum": ["bar", "line"]},
                "x": {"type": "array", "items": {"type": "string"}},
                "y": {"type": "array", "items": {"type": "number"}},
                "title": {"type": "string"},
            },
            "required": ["kind", "x", "y", "title"],
        },
    },
]
