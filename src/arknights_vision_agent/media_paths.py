"""Shared lexical validation for literal relative media references."""

import unicodedata


def is_valid_media_path(value: object) -> bool:
    if type(value) is not str or not 1 <= len(value) <= 1024:
        return False
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return not (
        value.startswith(("/", "~"))
        or "\\" in value
        or ":" in value
        or any(unicodedata.category(character) == "Cc" for character in value)
        or any(part in ("", ".", "..") for part in value.split("/"))
    )
