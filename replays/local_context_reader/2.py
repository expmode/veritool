def read_local_context(base_dir: str, requested_path: str, file_map: dict[str, str]) -> str:
    if requested_path.startswith("/"):
        raise ValueError("absolute paths are forbidden")
    normalized_base = posixpath.normpath(base_dir)
    normalized_path = posixpath.normpath(posixpath.join(normalized_base, requested_path))
    if normalized_path != normalized_base and not normalized_path.startswith(normalized_base + "/"):
        raise ValueError("path escapes base directory")
    if not normalized_path.endswith(".txt"):
        raise ValueError("only .txt files are allowed")
    return file_map[normalized_path]
