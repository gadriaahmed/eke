def is_blacklisted(title: str, description: str, blacklist: list[str]) -> str | None:
    """Return the first matched keyword (lowercased) or None if clean."""
    text = f"{title} {description}".lower()
    for kw in blacklist:
        if kw in text:
            return kw
    return None
