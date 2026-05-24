def mask_pii(text: str) -> str:
    text = re.sub(r"\b(?:\d{4}-){3}\d{4}\b", "[CARD]", text)
    text = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[SSN]", text)
    text = re.sub(r"\b\d{3}[- ]\d{3}[- ]\d{4}\b", "[PHONE]", text)
    text = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "[EMAIL]", text)
    return text
