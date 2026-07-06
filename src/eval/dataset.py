"""Gold evaluation dataset: 16 natural-language questions over the seeded
recommerce DB. Each case's gold_answer is computed by an *independent*
reference query — never by re-running the agent's own query — so answer_match
scoring is a real check, not a tautology.

Each case also carries a mock_plan: the scripted (tool, args) / (final, fn)
steps MockProvider replays. Tool calls still execute for real against the
database; only the choice of what to call/say is scripted. See providers.py.

Case `avg_order_value` is a deliberate, honest failure: the scripted plan
computes average *unit price* per line item instead of average *order*
value. It is grounded in its own (wrong) query, so faithfulness passes, but
answer_match correctly fails. Left in on purpose — see README.
"""

CASES = [
    {
        "id": "total_revenue_january",
        "question": "What was our total revenue in January 2025?",
        "expected_tools": {"sql_query"},
        "answer_type": "numeric",
        "gold_answer": 3069.68,
        "tolerance": 0.02,
        "mock_plan": [
            {"type": "tool", "tool": "sql_query", "args": {
                "query": "SELECT ROUND(SUM(quantity*unit_price),2) AS rev FROM order_items oi "
                         "JOIN orders o ON o.id=oi.order_id WHERE o.order_date LIKE '2025-01%'"
            }},
            {"type": "final", "fn": lambda obs: f"Total revenue in January 2025 was ${obs[0][0]['rev']:.2f}."},
        ],
    },
    {
        "id": "total_revenue_all",
        "question": "What is our total revenue across all orders?",
        "expected_tools": {"sql_query"},
        "answer_type": "numeric",
        "gold_answer": 13053.42,
        "tolerance": 0.02,
        "mock_plan": [
            {"type": "tool", "tool": "sql_query", "args": {
                "query": "SELECT ROUND(SUM(quantity*unit_price),2) AS rev FROM order_items"
            }},
            {"type": "final", "fn": lambda obs: f"Total revenue across all orders is ${obs[0][0]['rev']:.2f}."},
        ],
    },
    {
        "id": "avg_order_value",
        "question": "What is the average order value?",
        "expected_tools": {"sql_query"},
        "answer_type": "numeric",
        "gold_answer": 217.56,
        "tolerance": 0.02,
        "is_honest_failure": True,
        "failure_note": "Agent computes average unit price per line item instead of average "
                         "per-order total — grounded in its own query, but the wrong metric.",
        "mock_plan": [
            {"type": "tool", "tool": "sql_query", "args": {
                "query": "SELECT ROUND(AVG(unit_price),2) AS avg_val FROM order_items"
            }},
            {"type": "final", "fn": lambda obs: f"The average order value is ${obs[0][0]['avg_val']:.2f}."},
        ],
    },
    {
        "id": "top_category_by_revenue",
        "question": "Which product category generated the most revenue?",
        "expected_tools": {"sql_query"},
        "answer_type": "string",
        "gold_answer": "Electronics",
        "mock_plan": [
            {"type": "tool", "tool": "sql_query", "args": {
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
        "expected_tools": {"sql_query"},
        "answer_type": "string",
        "gold_answer": "Bluetooth Speaker",
        "mock_plan": [
            {"type": "tool", "tool": "sql_query", "args": {
                "query": "SELECT p.name, SUM(oi.quantity) AS qty FROM order_items oi "
                         "JOIN products p ON p.id=oi.product_id GROUP BY p.name ORDER BY qty DESC LIMIT 1"
            }},
            {"type": "final", "fn": lambda obs: (
                f"{obs[0][0]['name']} sold the most units, with {obs[0][0]['qty']} units sold."
            )},
        ],
    },
    {
        "id": "orders_count_february",
        "question": "How many orders were placed in February 2025?",
        "expected_tools": {"sql_query"},
        "answer_type": "numeric",
        "gold_answer": 15,
        "tolerance": 0,
        "mock_plan": [
            {"type": "tool", "tool": "sql_query", "args": {
                "query": "SELECT COUNT(*) AS n FROM orders WHERE order_date LIKE '2025-02%'"
            }},
            {"type": "final", "fn": lambda obs: f"{obs[0][0]['n']} orders were placed in February 2025."},
        ],
    },
    {
        "id": "total_returns_count",
        "question": "How many items have been returned in total?",
        "expected_tools": {"sql_query"},
        "answer_type": "numeric",
        "gold_answer": 13,
        "tolerance": 0,
        "mock_plan": [
            {"type": "tool", "tool": "sql_query", "args": {"query": "SELECT COUNT(*) AS n FROM returns"}},
            {"type": "final", "fn": lambda obs: f"A total of {obs[0][0]['n']} items have been returned."},
        ],
    },
    {
        "id": "most_common_return_reason",
        "question": "What is the most common reason customers return items?",
        "expected_tools": {"sql_query"},
        "answer_type": "string",
        "gold_answer": "not_as_described",
        "mock_plan": [
            {"type": "tool", "tool": "sql_query", "args": {
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
        "expected_tools": {"sql_query", "calculator"},
        "answer_type": "numeric",
        "gold_answer": 7.89,
        "tolerance": 0.05,
        "mock_plan": [
            {"type": "tool", "tool": "sql_query", "args": {
                "query": "SELECT "
                         "(SELECT COUNT(*) FROM returns r JOIN order_items oi ON oi.id=r.order_item_id "
                         "JOIN products p ON p.id=oi.product_id WHERE p.category='Electronics') AS returned, "
                         "(SELECT COUNT(*) FROM order_items oi JOIN products p ON p.id=oi.product_id "
                         "WHERE p.category='Electronics') AS total"
            }},
            {"type": "tool", "tool": "calculator", "args": lambda obs: {
                "expression": f"{obs[0][0]['returned']} / {obs[0][0]['total']} * 100"
            }},
            {"type": "final", "fn": lambda obs: (
                f"Approximately {obs[1]['result']:.2f}% of Electronics line items get returned."
            )},
        ],
    },
    {
        "id": "monthly_revenue_trend",
        "question": "Show me the monthly revenue trend for 2025 and tell me which month had the highest revenue.",
        "expected_tools": {"sql_query", "chart"},
        "answer_type": "string",
        "gold_answer": "2025-02",
        "mock_plan": [
            {"type": "tool", "tool": "sql_query", "args": {
                "query": "SELECT substr(o.order_date,1,7) AS month, "
                         "ROUND(SUM(oi.quantity*oi.unit_price),2) AS rev FROM order_items oi "
                         "JOIN orders o ON o.id=oi.order_id GROUP BY month ORDER BY month"
            }},
            {"type": "tool", "tool": "chart", "args": lambda obs: {
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
        "id": "revenue_growth_jan_feb",
        "question": "What was the percentage revenue growth from January to February 2025?",
        "expected_tools": {"sql_query", "calculator"},
        "answer_type": "numeric",
        "gold_answer": 48.53,
        "tolerance": 0.05,
        "mock_plan": [
            {"type": "tool", "tool": "sql_query", "args": {
                "query": "SELECT "
                         "ROUND(SUM(CASE WHEN o.order_date LIKE '2025-01%' THEN oi.quantity*oi.unit_price "
                         "ELSE 0 END),2) AS jan_rev, "
                         "ROUND(SUM(CASE WHEN o.order_date LIKE '2025-02%' THEN oi.quantity*oi.unit_price "
                         "ELSE 0 END),2) AS feb_rev "
                         "FROM order_items oi JOIN orders o ON o.id=oi.order_id"
            }},
            {"type": "tool", "tool": "calculator", "args": lambda obs: {
                "expression": f"({obs[0][0]['feb_rev']} - {obs[0][0]['jan_rev']}) / {obs[0][0]['jan_rev']} * 100"
            }},
            {"type": "final", "fn": lambda obs: (
                f"Revenue grew {obs[1]['result']:.2f}% from January (${obs[0][0]['jan_rev']:.2f}) "
                f"to February (${obs[0][0]['feb_rev']:.2f})."
            )},
        ],
    },
    {
        "id": "net_revenue_after_returns",
        "question": "What is our net revenue after accounting for returns?",
        "expected_tools": {"sql_query"},
        "answer_type": "numeric",
        "gold_answer": 11948.63,
        "tolerance": 0.02,
        "mock_plan": [
            {"type": "tool", "tool": "sql_query", "args": {
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
        "expected_tools": {"sql_query"},
        "answer_type": "string",
        "gold_answer": "Kira Volkov",
        "mock_plan": [
            {"type": "tool", "tool": "sql_query", "args": {
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
        "id": "unique_customers_apparel",
        "question": "How many unique customers have purchased Apparel?",
        "expected_tools": {"sql_query"},
        "answer_type": "numeric",
        "gold_answer": 10,
        "tolerance": 0,
        "mock_plan": [
            {"type": "tool", "tool": "sql_query", "args": {
                "query": "SELECT COUNT(DISTINCT o.customer_id) AS n FROM order_items oi "
                         "JOIN orders o ON o.id=oi.order_id JOIN products p ON p.id=oi.product_id "
                         "WHERE p.category='Apparel'"
            }},
            {"type": "final", "fn": lambda obs: f"{obs[0][0]['n']} unique customers have purchased Apparel."},
        ],
    },
    {
        "id": "avg_unit_price_electronics_products",
        "question": "What is the average unit price of products in the Electronics category?",
        "expected_tools": {"sql_query"},
        "answer_type": "numeric",
        "gold_answer": 116.66,
        "tolerance": 0.02,
        "mock_plan": [
            {"type": "tool", "tool": "sql_query", "args": {
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
        "expected_tools": {"sql_query"},
        "answer_type": "numeric",
        "gold_answer": 1799.76,
        "tolerance": 0.02,
        "mock_plan": [
            {"type": "tool", "tool": "sql_query", "args": {
                "query": "SELECT ROUND(SUM(oi.quantity*oi.unit_price),2) AS rev FROM order_items oi "
                         "JOIN products p ON p.id=oi.product_id WHERE p.category='Apparel'"
            }},
            {"type": "final", "fn": lambda obs: f"Apparel generated ${obs[0][0]['rev']:.2f} in revenue."},
        ],
    },
]

CASES_BY_ID = {c["id"]: c for c in CASES}
MOCK_PLANS = {c["id"]: c["mock_plan"] for c in CASES}
