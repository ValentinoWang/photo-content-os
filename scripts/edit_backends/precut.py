"""Select the automatic cuts that can be passed to a local editor."""


def executable_cuts(raw: dict) -> list[dict]:
    if (not isinstance(raw, dict) or not isinstance(raw.get("suggestions"), list)
            or not all(isinstance(item, dict) for item in raw["suggestions"])):
        raise ValueError("suggestions_list_required")
    cuts = [item for item in raw["suggestions"] if item.get("type") in {"silence", "repetition"}
            and item.get("auto_cut_allowed") is True and raw.get("auto_cut_allowed") is not False]
    for item in cuts:
        if item["type"] == "repetition" and (raw.get("precision") != "word" or item.get("precision", "word") != "word"):
            raise ValueError("repetition_requires_word_timing")
    return cuts
