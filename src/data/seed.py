"""Builds data/business.db: a small recommerce dataset (products, customers,
orders, order_items, returns). Deterministic (random.seed(42)) so the gold
answers in eval/dataset.py stay valid across re-seeds."""
import random
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "business.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

PRODUCTS = [
    ("Wireless Earbuds", "Electronics", 59.99),
    ("Bluetooth Speaker", "Electronics", 89.99),
    ("Smart Watch", "Electronics", 199.99),
    ("Running Shoes", "Sporting Goods", 79.99),
    ("Yoga Mat", "Sporting Goods", 29.99),
    ("Winter Jacket", "Apparel", 129.99),
    ("Cotton T-Shirt", "Apparel", 19.99),
    ("Coffee Maker", "Home", 69.99),
    ("Desk Lamp", "Home", 34.99),
]

CUSTOMERS = [
    "Alice Chen", "Ben Torres", "Carla Diaz", "Dev Patel", "Ella Novak",
    "Farid Khan", "Grace Kim", "Hassan Ali", "Ivy Sullivan", "Jon Meyer",
    "Kira Volkov", "Liam O'Brien",
]

RETURN_REASONS = ["wrong_size", "defective", "not_as_described", "changed_mind", "wrong_item"]

MONTHS = ["2025-01", "2025-02", "2025-03", "2025-04"]


def build():
    random.seed(42)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA_PATH.read_text())

    conn.executemany(
        "INSERT INTO products (id, name, category, unit_price) VALUES (?, ?, ?, ?)",
        [(i + 1, n, c, p) for i, (n, c, p) in enumerate(PRODUCTS)],
    )
    conn.executemany(
        "INSERT INTO customers (id, name) VALUES (?, ?)",
        [(i + 1, n) for i, n in enumerate(CUSTOMERS)],
    )

    order_id = 1
    item_id = 1
    order_rows = []
    item_rows = []

    orders_per_month = 15
    for month in MONTHS:
        for _ in range(orders_per_month):
            customer_id = random.randint(1, len(CUSTOMERS))
            day = random.randint(1, 28)
            order_date = f"{month}-{day:02d}"
            order_rows.append((order_id, customer_id, order_date, "completed"))

            n_items = random.choice([1, 1, 2, 2, 3])
            chosen_products = random.sample(range(1, len(PRODUCTS) + 1), n_items)
            for product_id in chosen_products:
                quantity = random.choice([1, 1, 1, 2, 3])
                unit_price = PRODUCTS[product_id - 1][2]
                item_rows.append((item_id, order_id, product_id, quantity, unit_price))
                item_id += 1

            order_id += 1

    conn.executemany(
        "INSERT INTO orders (id, customer_id, order_date, status) VALUES (?, ?, ?, ?)",
        order_rows,
    )
    conn.executemany(
        "INSERT INTO order_items (id, order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?, ?)",
        item_rows,
    )

    return_rows = []
    return_id = 1
    for item in item_rows:
        if random.random() < 0.12:
            iid = item[0]
            order_id_for_item = item[1]
            order_date = next(r[2] for r in order_rows if r[0] == order_id_for_item)
            return_date = order_date[:7] + f"-{min(28, int(order_date[-2:]) + 5):02d}"
            reason = random.choice(RETURN_REASONS)
            return_rows.append((return_id, iid, reason, return_date))
            return_id += 1

    conn.executemany(
        "INSERT INTO returns (id, order_item_id, reason, return_date) VALUES (?, ?, ?, ?)",
        return_rows,
    )

    conn.commit()
    conn.close()
    print(f"Seeded {len(order_rows)} orders, {len(item_rows)} line items, {len(return_rows)} returns -> {DB_PATH}")


if __name__ == "__main__":
    build()
