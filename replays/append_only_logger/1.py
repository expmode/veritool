def append_only_log(existing: str, new_entry: str, max_bytes: int = 4096) -> str:
    return existing + new_entry
