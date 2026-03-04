from __future__ import annotations

import re


def parse_participant_list(text: str) -> list[str]:
    names: list[str] = []
    for match in re.finditer(r"\"([^\"]+)\"\s*<[^>]+>", text):
        name = match.group(1).strip()
        if name:
            names.append(name)

    if names:
        return names

    for part in re.split(r"[;,]\s*", text.strip()):
        cleaned = part.strip().strip("\"'")
        if not cleaned:
            continue
        if "@" in cleaned:
            continue
        names.append(cleaned)

    return names
