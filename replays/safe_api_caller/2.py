def safe_api_call(url: str, method: str, allowlist: list[str], responses: dict[str, str]) -> str:
    method = method.upper()
    if method != "GET":
        raise ValueError("only GET is allowed")
    parsed = urllib_parse.urlparse(url)
    if parsed.scheme != "https":
        raise ValueError("only https is allowed")
    host = parsed.hostname
    if not host:
        raise ValueError("missing host")
    if host == "localhost":
        raise ValueError("localhost is forbidden")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip is not None:
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            raise ValueError("private host is forbidden")
        raise ValueError("bare IP hosts are forbidden")
    if host not in allowlist:
        raise ValueError("host is not allowlisted")
    key = f"{method} {url}"
    if key not in responses:
        raise ValueError("missing mocked response")
    return responses[key]
