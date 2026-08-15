def validate_title(title: str) -> None:
    if title is None or not title.strip():
        raise ValueError("title must not be empty")
