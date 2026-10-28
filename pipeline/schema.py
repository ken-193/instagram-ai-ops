"""script.json validation (dependency-free).

Returns a list of human-readable errors; an empty list means the script is valid.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

CATEGORIES = {
    "scientific": "科学的な仮説検証",
    "data_estimate": "実データを用いた概算シミュレーション",
    "thought_experiment": "社会・経済の思考実験",
    "fiction": "完全なフィクション",
}
FACT_STATUSES = {"verified", "assumption", "estimate", "fiction"}
POST_ID_RE = re.compile(r"^IG-\d{8}-\d{3}$")

REQUIRED_TOP = {
    "post_id": str,
    "title": str,
    "summary": str,
    "premise": str,
    "categories": list,
    "genre": str,
    "target_audience": str,
    "hook": str,
    "tokushima_ending": dict,
    "bgm": dict,
    "scenes": list,
    "fact_checks": list,
    "sources": list,
    "caption": str,
    "hashtags": list,
    "pinned_comment": str,
    "thumbnail_text": str,
    "production_notes": list,
}
REQUIRED_SCENE = {
    "id": str,
    "type": str,
    "narration": list,
    "on_screen_text": list,
    "animation": str,
    "camera": str,
    "sfx": list,
    "video_prompt": str,
}


def _check_types(obj: dict, spec: dict, where: str, errors: list[str]) -> None:
    for key, typ in spec.items():
        if key not in obj:
            errors.append(f"{where}: missing '{key}'")
        elif not isinstance(obj[key], typ):
            errors.append(f"{where}: '{key}' must be {typ.__name__}")
        elif typ in (str, list) and len(obj[key]) == 0 and key not in ("sfx", "production_notes"):
            errors.append(f"{where}: '{key}' is empty")


def validate(script: dict, known_scene_types: set[str] | None = None) -> list[str]:
    errors: list[str] = []
    _check_types(script, REQUIRED_TOP, "script", errors)
    if errors:
        return errors

    if not POST_ID_RE.match(script["post_id"]):
        errors.append("script: post_id must look like IG-YYYYMMDD-NNN")
    for c in script["categories"]:
        if c not in CATEGORIES:
            errors.append(f"script: unknown category '{c}' (allowed: {sorted(CATEGORIES)})")

    end = script["tokushima_ending"]
    for k in ("type", "description"):
        if not end.get(k):
            errors.append(f"tokushima_ending: missing '{k}'")

    source_ids = set()
    for i, s in enumerate(script["sources"]):
        for k in ("id", "title", "url", "accessed", "used_for"):
            if not s.get(k):
                errors.append(f"sources[{i}]: missing '{k}'")
        if s.get("url") and not str(s["url"]).startswith("https://"):
            errors.append(f"sources[{i}]: url must be https")
        source_ids.add(s.get("id"))

    for i, fc in enumerate(script["fact_checks"]):
        where = f"fact_checks[{i}]"
        if not fc.get("claim"):
            errors.append(f"{where}: missing 'claim'")
        if fc.get("status") not in FACT_STATUSES:
            errors.append(f"{where}: status must be one of {sorted(FACT_STATUSES)}")
        if fc.get("status") == "verified" and not fc.get("source_ids"):
            errors.append(f"{where}: verified claims need source_ids")
        if fc.get("status") == "estimate" and not fc.get("method"):
            errors.append(f"{where}: estimates need 'method' (assumptions + calculation)")
        for sid in fc.get("source_ids", []):
            if sid not in source_ids:
                errors.append(f"{where}: unknown source id '{sid}'")

    seen = set()
    for i, sc in enumerate(script["scenes"]):
        where = f"scenes[{i}]"
        if not isinstance(sc, dict):
            errors.append(f"{where}: must be an object")
            continue
        _check_types(sc, REQUIRED_SCENE, where, errors)
        if sc.get("id") in seen:
            errors.append(f"{where}: duplicate id '{sc.get('id')}'")
        seen.add(sc.get("id"))
        if known_scene_types is not None and sc.get("type") not in known_scene_types:
            errors.append(f"{where}: unknown scene type '{sc.get('type')}'")
        for j, line in enumerate(sc.get("narration", [])):
            if not isinstance(line, dict) or not line.get("text"):
                errors.append(f"{where}.narration[{j}]: needs {{'text': ..., 'tts'?: ...}}")

    tags = script["hashtags"]
    if len(tags) > 15:
        errors.append("hashtags: keep it to 15 or fewer relevant tags")
    for t in tags:
        if not t.startswith("#") or " " in t:
            errors.append(f"hashtags: invalid tag '{t}'")
    if len(script["caption"]) > 2200:
        errors.append("caption: exceeds Instagram's 2200 character limit")
    return errors


def load_and_validate(path: str | Path, known_scene_types: set[str] | None = None) -> tuple[dict, list[str]]:
    try:
        script = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return {}, [f"invalid JSON: {e}"]
    return script, validate(script, known_scene_types)


if __name__ == "__main__":
    from pipeline.render.scenes import SCENES

    _, errs = load_and_validate(sys.argv[1], set(SCENES))
    for e in errs:
        print("ERROR:", e)
    print("OK" if not errs else f"{len(errs)} error(s)")
    sys.exit(1 if errs else 0)
