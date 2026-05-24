SQL_PATTERN = re.compile(
    r"^SELECT\s+(?P<columns>\*|[a-z_,\s]+)\s+FROM\s+rows(?:\s+WHERE\s+(?P<where_column>[a-z_]+)\s*(?P<where_op>=|>=|<=|>|<)\s*(?P<where_value>-?\d+))?(?:\s+LIMIT\s+(?P<limit>\d+))?$",
    re.IGNORECASE,
)


def run_bounded_sql(query: str, rows: list[dict[str, int]]) -> list[dict[str, int]]:
    lowered = query.lower()
    if ";" in query or any(keyword in lowered for keyword in ("delete", "update", "insert", "drop", "alter", "create", "pragma")):
        raise ValueError("mutating SQL is forbidden")
    match = SQL_PATTERN.fullmatch(query.strip())
    if not match:
        raise ValueError("unsupported query grammar")
    columns_text = match.group("columns")
    columns = list(rows[0]) if columns_text == "*" else [column.strip() for column in columns_text.split(",")]
    for column in columns:
        if column not in rows[0]:
            raise ValueError("unknown selected column")
    filtered = [dict(row) for row in rows]
    where_column = match.group("where_column")
    if where_column:
        if where_column not in rows[0]:
            raise ValueError("unknown where column")
        where_value = int(match.group("where_value"))
        where_op = match.group("where_op")
        filtered = [row for row in filtered if _compare(row[where_column], where_op, where_value)]
    limit_text = match.group("limit")
    if limit_text is not None:
        filtered = filtered[: int(limit_text)]
    return [{column: row[column] for column in columns} for row in filtered]


def _compare(left: int, op: str, right: int) -> bool:
    if op == "=":
        return left == right
    if op == ">=":
        return left >= right
    if op == "<=":
        return left <= right
    if op == ">":
        return left > right
    return left < right
