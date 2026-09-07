"""Shared opaque-identifier validation."""


def is_valid_identifier(value: object) -> bool:
    if type(value) is not str or not value.strip() or len(value) > 128:
        return False
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True
