def normalize_col(name: str) -> str:
    """Normalize column names for consistent matching."""
    return name.strip().lower().replace(" ", "")