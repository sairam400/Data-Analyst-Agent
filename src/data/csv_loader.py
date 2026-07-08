"""Loads an uploaded CSV into a new table in the SQLite demo database, so the
agent's get_schema/run_sql tools can query uploaded data the same way they
query the seeded recommerce tables."""
import csv
import re
import sqlite3

_IDENTIFIER_RE = re.compile(r"[^a-zA-Z0-9_]")


def _sanitize_identifier(name, fallback):
    cleaned = _IDENTIFIER_RE.sub("_", name.strip()).strip("_")
    if not cleaned or cleaned[0].isdigit():
        cleaned = f"{fallback}_{cleaned}" if cleaned else fallback
    return cleaned.lower()


def _infer_column_type(values):
    non_empty = [v for v in values if v != ""]
    if not non_empty:
        return "TEXT"
    if all(re.fullmatch(r"-?\d+", v) for v in non_empty):
        return "INTEGER"
    if all(re.fullmatch(r"-?\d*\.?\d+(?:[eE][-+]?\d+)?", v) for v in non_empty):
        return "REAL"
    return "TEXT"


def load_csv_to_sqlite(csv_path, table_name, db_path):
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)

    columns = [_sanitize_identifier(h, f"col{i}") for i, h in enumerate(header)]
    table = _sanitize_identifier(table_name, "uploaded_table")

    column_values = list(zip(*rows)) if rows else [[] for _ in columns]
    column_types = [_infer_column_type(vals) for vals in column_values]

    conn = sqlite3.connect(db_path)
    try:
        col_defs = ", ".join(f'"{c}" {t}' for c, t in zip(columns, column_types))
        conn.execute(f'DROP TABLE IF EXISTS "{table}"')
        conn.execute(f'CREATE TABLE "{table}" ({col_defs})')

        placeholders = ", ".join("?" for _ in columns)
        insert_sql = f'INSERT INTO "{table}" VALUES ({placeholders})'
        typed_rows = []
        for row in rows:
            typed_row = []
            for value, col_type in zip(row, column_types):
                if value == "":
                    typed_row.append(None)
                elif col_type == "INTEGER":
                    typed_row.append(int(value))
                elif col_type == "REAL":
                    typed_row.append(float(value))
                else:
                    typed_row.append(value)
            typed_rows.append(typed_row)
        conn.executemany(insert_sql, typed_rows)
        conn.commit()
    finally:
        conn.close()

    return {"table": table, "columns": columns, "row_count": len(rows)}
