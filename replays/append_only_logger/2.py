def append_only_log(existing: str, new_entry: str, max_bytes: int = 4096) -> str:
    if "\0" in new_entry:
        raise ValueError("NUL bytes are forbidden")
    result = existing
    if result and not result.endswith("\n"):
        result += "\n"
    result += new_entry
    if len(result.encode("utf-8")) > max_bytes:
        raise ValueError("result exceeds byte budget")
    return result
