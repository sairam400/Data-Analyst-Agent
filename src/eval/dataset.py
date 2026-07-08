"""Gold evaluation dataset: 15 natural-language questions over the seeded
recommerce DB (~5k order line items). Each case's gold_answer is computed by
an *independent* reference query — never by re-running the agent's own
query — so answer_match scoring is a real check, not a tautology.

Each case also carries a mock_plan: the scripted (tool, args) / (final, fn)
steps MockProvider replays. Tool calls still execute for real against the
database; only the choice of what to call/say is scripted. See providers/.

Case `avg_order_value` is a deliberate, honest failure: the scripted plan
computes average *unit price* per line item instead of average *order*
value. It is grounded in its own (wrong) query, so faithfulness passes, but
answer_match correctly fails. Left in on purpose — see README.

`profit_margin_best_seller` and `customer_email_lookup` are deliberately
unanswerable — the schema has no cost/COGS data and no email column. The
agent is expected to call get_schema, notice the gap, and say so honestly
instead of guessing.
"""

CASES = [
    {
        "id": "total_revenue_all",
        "question": "What is our total revenue across all orders?",
        "expected_tools": {"run_sql"},
        "answer_type": "numeric",
        "gold_answer": 626849.61,
        "tolerance": 0.02,
        "mock_plan": [
            {"type": "tool", "tool": "run_sql", "args": {
                "query": "SELECT ROUND(SUM(quantity*unit_price),2) AS rev FROM order_items"
            }},
            {"type": "final", "fn": lambda obs: f"Total revenue across all orders is ${obs[0][0]['rev']:.2f}."},
        ],
    },
    {
        "id": "avg_order_value",
        "question": "What is the average order value?",
        "expected_tools": {"run_sql"},
        "answer_type": "numeric",
        "gold_answer": 222.29,
        "tolerance": 0.02,
        "is_honest_failure": True,
        "failure_note": "Agent computes average unit price per line item instead of average "
                         "per-order total — grounded in its own query, but the wrong metric.",
        "mock_plan": [
            {"type": "tool", "tool": "run_sql", "args": {
                "query": "SELECT ROUND(AVG(unit_price),2) AS avg_val FROM order_items"
            }},
            {"type": "final", "fn": lambda obs: f"The average order value is ${obs[0][0]['avg_val']:.2f}."},
        ],
    },
    {
        "id": "top_category_by_revenue",
        "question": "Which product category generated the most revenue?",
        "expected_tools": {"run_sql"},
        "answer_type": "string",
        "gold_answer": "Electronics",
        "mock_plan": [
            {"type": "tool", "tool": "run_sql", "args": {
                "query": "SELECT p.category, ROUND(SUM(oi.quantity*oi.unit_price),2) AS rev "
                         "FROM order_items oi JOIN products p ON p.id=oi.product_id "
                         "GROUP BY p.category ORDER BY rev DESC LIMIT 1"
            }},
            {"type": "final", "fn": lambda obs: (
                f"The top category by revenue is {obs[0][0]['category']}, with ${obs[0][0]['rev']:.2f}."
            )},
        ],
    },
    {
        "id": "top_product_by_units",
        "question": "Which product sold the most units?",
        "expected_tools": {"run_sql"},
        "answer_type": "string",
        "gold_answer": "Shampoo Set",
        "mock_plan": [
            {"type": "tool", "tool": "run_sql", "args": {
                "query": "SELECT p.name, SUM(oi.quantity) AS qty FROM order_items oi "
                         "JOIN products p ON p.id=oi.product_id GROUP BY p.name ORDER BY qty DESC LIMIT 1"
            }},
            {"type": "final", "fn": lambda obs: (
                f"{obs[0][0]['name']} sold the most units, with {obs[0][0]['qty']} units sold."
            )},
        ],
    },
    {
        "id": "total_returns_count",
        "question": "How many items have been returned in total?",
        "expected_tools": {"run_sql"},
        "answer_type": "numeric",
        "gold_answer": 659,
        "tolerance": 0,
        "mock_plan": [
            {"type": "tool", "tool": "run_sql", "args": {"query": "SELECT COUNT(*) AS n FROM returns"}},
            {"type": "final", "fn": lambda obs: f"A total of {obs[0][0]['n']} items have been returned."},
        ],
    },
    {
        "id": "most_common_return_reason",
        "question": "What is the most common reason customers return items?",
        "expected_tools": {"run_sql"},
        "answer_type": "string",
        "gold_answer": "wrong_size",
        "mock_plan": [
            {"type": "tool", "tool": "run_sql", "args": {
                "query": "SELECT reason, COUNT(*) AS n FROM returns GROUP BY reason ORDER BY n DESC LIMIT 1"
            }},
            {"type": "final", "fn": lambda obs: (
                f"The most common return reason is '{obs[0][0]['reason']}', "
                f"accounting for {obs[0][0]['n']} returns."
            )},
        ],
    },
    {
        "id": "return_rate_electronics",
        "question": "What percentage of Electronics line items get returned?",
        "expected_tools": {"run_sql", "run_python"},
        "answer_type": "numeric",
        "gold_answer": 12.32,
        "tolerance": 0.05,
        "mock_plan": [
            {"type": "tool", "tool": "run_sql", "args": {
                "query": "SELECT "
                         "(SELECT COUNT(*) FROM returns r JOIN order_items oi ON oi.id=r.order_item_id "
                         "JOIN products p ON p.id=oi.product_id WHERE p.category='Electronics') AS returned, "
                         "(SELECT COUNT(*) FROM order_items oi JOIN products p ON p.id=oi.product_id "
                         "WHERE p.category='Electronics') AS total"
            }},
            {"type": "tool", "tool": "run_python", "args": lambda obs: {
                "code": f"print(round({obs[0][0]['returned']} / {obs[0][0]['total']} * 100, 2))"
            }},
            {"type": "final", "fn": lambda obs: (
                f"Approximately {float(obs[1]['stdout'].strip()):.2f}% of Electronics line items get returned."
            )},
        ],
    },
    {
        "id": "monthly_revenue_trend",
        "question": "Show me the monthly revenue trend for 2025 and tell me which month had the highest revenue.",
        "expected_tools": {"run_sql", "make_chart"},
        "answer_type": "string",
        "gold_answer": "2025-10",
        "mock_plan": [
            {"type": "tool", "tool": "run_sql", "args": {
                "query": "SELECT substr(o.order_date,1,7) AS month, "
                         "ROUND(SUM(oi.quantity*oi.unit_price),2) AS rev FROM order_items oi "
                         "JOIN orders o ON o.id=oi.order_id GROUP BY month ORDER BY month"
            }},
            {"type": "tool", "tool": "make_chart", "args": lambda obs: {
                "kind": "bar",
                "x": [r["month"] for r in obs[0]],
                "y": [r["rev"] for r in obs[0]],
                "title": "Monthly Revenue, 2025",
            }},
            {"type": "final", "fn": lambda obs: (
                lambda top: f"Monthly revenue is charted above. {top['month']} had the highest "
                            f"revenue, at ${top['rev']:.2f}."
            )(max(obs[0], key=lambda r: r["rev"]))},
        ],
    },
    {
        "id": "q1_revenue",
        "question": "How much revenue came from orders placed in the first quarter?",
        "expected_tools": {"run_sql"},
        "answer_type": "numeric",
        "gold_answer": 149881.58,
        "tolerance": 0.02,
        "mock_plan": [
            {"type": "tool", "tool": "run_sql", "args": {
                "query": "SELECT ROUND(SUM(oi.quantity*oi.unit_price),2) AS rev FROM order_items oi "
                         "JOIN orders o ON o.id=oi.order_id "
                         "WHERE o.order_date >= '2025-01-01' AND o.order_date < '2025-04-01'"
            }},
            {"type": "final", "fn": lambda obs: (
                f"Revenue from the first quarter (January through March) was ${obs[0][0]['rev']:.2f}."
            )},
        ],
    },
    {
        "id": "net_revenue_after_returns",
        "question": "What is our net revenue after accounting for returns?",
        "expected_tools": {"run_sql"},
        "answer_type": "numeric",
        "gold_answer": 548261.13,
        "tolerance": 0.02,
        "mock_plan": [
            {"type": "tool", "tool": "run_sql", "args": {
                "query": "SELECT ROUND("
                         "(SELECT SUM(quantity*unit_price) FROM order_items) - "
                         "(SELECT COALESCE(SUM(oi.quantity*oi.unit_price),0) FROM returns r "
                         "JOIN order_items oi ON oi.id=r.order_item_id),2) AS net"
            }},
            {"type": "final", "fn": lambda obs: f"Net revenue after returns is ${obs[0][0]['net']:.2f}."},
        ],
    },
    {
        "id": "top_customer_by_spend",
        "question": "Who is our highest-spending customer?",
        "expected_tools": {"run_sql"},
        "answer_type": "string",
        "gold_answer": "Alice Singh",
        "mock_plan": [
            {"type": "tool", "tool": "run_sql", "args": {
                "query": "SELECT cu.name, ROUND(SUM(oi.quantity*oi.unit_price),2) AS total "
                         "FROM order_items oi JOIN orders o ON o.id=oi.order_id "
                         "JOIN customers cu ON cu.id=o.customer_id "
                         "GROUP BY cu.name ORDER BY total DESC LIMIT 1"
            }},
            {"type": "final", "fn": lambda obs: (
                f"{obs[0][0]['name']} is our highest-spending customer, at ${obs[0][0]['total']:.2f}."
            )},
        ],
    },
    {
        "id": "avg_unit_price_electronics_products",
        "question": "What is the average unit price of products in the Electronics category?",
        "expected_tools": {"run_sql"},
        "answer_type": "numeric",
        "gold_answer": 109.99,
        "tolerance": 0.02,
        "mock_plan": [
            {"type": "tool", "tool": "run_sql", "args": {
                "query": "SELECT ROUND(AVG(unit_price),2) AS a FROM products WHERE category='Electronics'"
            }},
            {"type": "final", "fn": lambda obs: (
                f"The average unit price of Electronics products is ${obs[0][0]['a']:.2f}."
            )},
        ],
    },
    {
        "id": "revenue_apparel",
        "question": "How much revenue did Apparel generate?",
        "expected_tools": {"run_sql"},
        "answer_type": "numeric",
        "gold_answer": 119909.09,
        "tolerance": 0.02,
        "mock_plan": [
            {"type": "tool", "tool": "run_sql", "args": {
                "query": "SELECT ROUND(SUM(oi.quantity*oi.unit_price),2) AS rev FROM order_items oi "
                         "JOIN products p ON p.id=oi.product_id WHERE p.category='Apparel'"
            }},
            {"type": "final", "fn": lambda obs: f"Apparel generated ${obs[0][0]['rev']:.2f} in revenue."},
        ],
    },
    {
        "id": "profit_margin_best_seller",
        "question": "What is the profit margin on our best-selling product?",
        "expected_tools": {"get_schema"},
        "answer_type": "unanswerable",
        "gold_answer": None,
        "mock_plan": [
            {"type": "tool", "tool": "get_schema", "args": {}},
            {"type": "final", "fn": lambda obs: (
                "I can't determine profit margin — products only stores unit_price (the selling "
                "price), with no cost or COGS column to compare it against."
            )},
        ],
    },
    {
        "id": "customer_email_lookup",
        "question": "What is the email address of our highest-spending customer?",
        "expected_tools": {"get_schema"},
        "answer_type": "unanswerable",
        "gold_answer": None,
        "mock_plan": [
            {"type": "tool", "tool": "get_schema", "args": {}},
            {"type": "final", "fn": lambda obs: (
                "I can't answer that — customers only has id and name in this schema, there's no "
                "email column."
            )},
        ],
    },
]

CASES_BY_ID = {c["id"]: c for c in CASES}
MOCK_PLANS = {c["id"]: c["mock_plan"] for c in CASES}
