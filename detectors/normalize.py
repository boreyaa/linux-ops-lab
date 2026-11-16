from detectors.base import LEVELS

REQUIRED = ("detector", "level", "title", "evidence")


def normalize(findings):
    kept = []
    for item in findings or []:
        if not isinstance(item, dict):
            continue
        missing = [k for k in REQUIRED if not str(item.get(k) or "").strip()]
        if missing:
            continue
        if item["level"] not in LEVELS:
            continue
        kept.append({
            "detector": item["detector"],
            "level": item["level"],
            "title": item["title"],
            "evidence": item["evidence"],
        })
    return kept
