def run_bounded_sql(query: str, rows: list[dict[str, int]]) -> list[dict[str, int]]:
    return [dict(row) for row in rows]
