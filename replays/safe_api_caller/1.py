def safe_api_call(url: str, method: str, allowlist: list[str], responses: dict[str, str]) -> str:
    return responses[f"{method.upper()} {url}"]
