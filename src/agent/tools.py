"""Tools available to the agent: get_schema, run_sql (read-only), run_python
(sandboxed), make_chart.

run_sql rejects anything that isn't a plain SELECT, so a misbehaving agent
can't mutate the database. run_python isolates the agent's code in its own
subprocess, in a scratch working directory, with network sockets disabled and
a hard timeout — see the module docstring on run_python for exactly what that
does and doesn't guarantee.
"""
import base64
import io
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = REPO_ROOT / "data" / "business.db"
SANDBOX_ROOT = REPO_ROOT / "sandbox"

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

RUN_PYTHON_TIMEOUT_SECONDS = 10

_NETWORK_BLOCK_PREAMBLE = """\
import socket as _socket


def _network_disabled(*args, **kwargs):
    raise OSError("network access is disabled in the run_python sandbox")


_socket.socket = _network_disabled
_socket.create_connection = _network_disabled

"""


class ToolError(Exception):
    pass


def get_schema(args: dict = None) -> dict:
    return {"schema": SCHEMA_DESCRIPTION}


def run_sql(args: dict) -> list:
    query = args.get("query", "")
    if not _READ_ONLY_PATTERN.match(query):
        raise ToolError("run_sql only accepts SELECT statements")
    if _FORBIDDEN_PATTERN.search(query):
        raise ToolError("run_sql rejected: mutating/schema statements are not allowed")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(query).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def run_python(args: dict) -> dict:
    """Runs args["code"] in its own subprocess.

    Isolation is process-level, not a real security sandbox: the working
    directory is a fresh scratch dir and the environment is stripped down,
    and network sockets are disabled for code that goes through the socket
    module. It does not stop code from opening an absolute path outside the
    scratch dir — that would need a container or OS-level sandbox, which is
    out of scope here. See KNOWN_ISSUES.md.
    """
    code = args.get("code", "")
    timeout = args.get("timeout", RUN_PYTHON_TIMEOUT_SECONDS)
    SANDBOX_ROOT.mkdir(parents=True, exist_ok=True)
    work_dir = Path(tempfile.mkdtemp(dir=SANDBOX_ROOT))
    script_path = work_dir / "snippet.py"
    script_path.write_text(_NETWORK_BLOCK_PREAMBLE + code)

    env = {"PATH": os.environ.get("PATH", "")}
    if os.name == "nt":
        env["SYSTEMROOT"] = os.environ.get("SYSTEMROOT", "")

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=work_dir,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise ToolError(f"run_python timed out after {timeout}s")

    if result.returncode != 0:
        raise ToolError(result.stderr.strip() or "run_python exited with a non-zero status")

    return {"stdout": result.stdout}


def make_chart(args: dict) -> dict:
    kind = args.get("kind", "bar")
    x = args.get("x", [])
    y = args.get("y", [])
    title = args.get("title", "")
    if kind not in {"bar", "line"}:
        raise ToolError(f"make_chart: unsupported kind '{kind}'")
    if len(x) != len(y):
        raise ToolError("make_chart: x and y series must be the same length")

    fig, ax = plt.subplots(figsize=(6.4, 3.6), dpi=100)
    if kind == "bar":
        ax.bar(x, y, color="#2a78d6")
    else:
        ax.plot(x, y, color="#2a78d6", marker="o")
    ax.set_title(title)
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    image_base64 = base64.b64encode(buf.read()).decode("ascii")

    return {"kind": kind, "title": title, "image_base64": image_base64}


TOOLS = {
    "get_schema": get_schema,
    "run_sql": run_sql,
    "run_python": run_python,
    "make_chart": make_chart,
}

TOOL_SPECS = [
    {
        "name": "get_schema",
        "description": "Get the database schema (tables and columns) before writing SQL.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "run_sql",
        "description": "Run a read-only SELECT query against the business SQLite database.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "A single SELECT statement"}},
            "required": ["query"],
        },
    },
    {
        "name": "run_python",
        "description": "Run a Python snippet for stats or transforms beyond what SQL can express. "
                        "Print results to stdout to see them. No network access.",
        "input_schema": {
            "type": "object",
            "properties": {"code": {"type": "string", "description": "Python source code to execute"}},
            "required": ["code"],
        },
    },
    {
        "name": "make_chart",
        "description": "Render a bar or line chart server-side and return it as an image.",
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
