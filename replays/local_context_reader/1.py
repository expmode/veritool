def read_local_context(base_dir: str, requested_path: str, file_map: dict[str, str]) -> str:
    candidate_path = posixpath.join(base_dir, requested_path)
    return file_map[candidate_path]
