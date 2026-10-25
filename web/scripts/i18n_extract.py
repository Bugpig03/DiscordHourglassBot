"""List every French / English phrase of the site and check the translation files.

    python scripts/i18n_extract.py            update app/locales/_phrases.json and print the coverage per language
    python scripts/i18n_extract.py todo es    print what app/locales/es.json still misses (key or id, French, English)

The admin page is only used by the site owner: its phrases are not asked for (they show in English).

Phrases are the inline pairs tr('Français', 'English') of the templates and Python code, T(...) / HG.tr(...) of
the scripts, and the French / English data tables (badges, records, gallery, colors, presence, level titles).
An id (p0001…) stays attached to its French text; a new phrase gets the next free id, a phrase that left the
code is dropped. Keys are those of app/translations.py.
"""
import ast
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "app")
LOCALES = os.path.join(APP, "locales")
ADMIN_PHRASES: set = set()
sys.path.insert(0, ROOT)

PY_LIT = r"""(?:'(?:[^'\\\n]|\\.)*'|"(?:[^"\\\n]|\\.)*")"""
JS_LIT = r"""(?:'(?:[^'\\\n]|\\.)*'|"(?:[^"\\\n]|\\.)*"|`(?:[^`\\$]|\\.)*`)"""
PY_CALL = re.compile(rf"\b(?:tr|label)\(\s*({PY_LIT})\s*,\s*({PY_LIT})")
JS_CALL = re.compile(rf"(?:\bT|\bHG\.tr)\(\s*({JS_LIT})\s*,\s*({JS_LIT})")


def py_text(literal: str) -> str:
    return ast.literal_eval(literal)


def js_text(literal: str) -> str:
    body = literal[1:-1]
    return re.sub(r"\\(.)", lambda m: {"n": "\n", "t": "\t"}.get(m.group(1), m.group(1)), body)


def collect() -> list[tuple[str, str, str]]:
    """(French, English, where) for every phrase, in source order."""
    found = []
    for path in sorted(glob.glob(os.path.join(APP, "**", "*.py"), recursive=True)) + sorted(
            glob.glob(os.path.join(APP, "templates", "**", "*.html"), recursive=True)):
        if path.endswith(("i18n.py", "translations.py")):
            continue
        text = open(path, encoding="utf-8").read()
        for m in PY_CALL.finditer(text):
            found.append((py_text(m.group(1)), py_text(m.group(2)), os.path.relpath(path, APP)))
    for path in sorted(glob.glob(os.path.join(APP, "static", "js", "**", "*.js"), recursive=True)):
        if "vendor" in path:
            continue
        text = open(path, encoding="utf-8").read()
        for m in JS_CALL.finditer(text):
            found.append((js_text(m.group(1)), js_text(m.group(2)), os.path.relpath(path, APP)))

    from app import gamification, profile_gallery, profile_records, profile_settings
    from app.functions import format_presence
    data = []
    seen_titles = set()
    for level in range(1, 120):
        xp = gamification.calculate_user_xp_and_level(((level - 1) ** 2) * 100 * 60, 0)
        if (xp["title_fr"], xp["title_en"]) not in seen_titles:
            seen_titles.add((xp["title_fr"], xp["title_en"]))
            data.append((xp["title_fr"], xp["title_en"]))
    data += [(fr, en) for _key, fr, en, _color in gamification.TIERS]
    for _key, name_fr, name_en, what_fr, what_en, *_rest in gamification.BADGE_DEFS:
        data += [(name_fr, name_en), (what_fr, what_en)]
    data += [(fr, en) for _icon, fr, en in profile_records.RECORD_CATALOG.values()]
    for name in dir(profile_gallery):
        table = getattr(profile_gallery, name)
        if name.isupper() and isinstance(table, dict):
            data += [v for v in table.values() if isinstance(v, tuple) and len(v) == 2]
    data += [(fr, en) for _k, _h, fr, en in profile_settings.PALETTE + profile_settings.BACKGROUND_COLORS]
    data += list(profile_settings.HIDEABLE_BLOCKS.values())
    for status in ("online", "idle", "dnd", "offline"):
        p = format_presence(status)
        data.append((p["label_fr"], p["label_en"]))
    found += [(fr, en, "data tables") for fr, en in data]
    return found


def load(name: str) -> dict:
    try:
        with open(os.path.join(LOCALES, name), encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return {}


ADMIN_ONLY = ("admin.html", "admin.js", "admin.py")


def update() -> dict:
    found = collect()
    sources: dict[str, set] = {}
    for fr, _en, where in found:
        sources.setdefault(fr, set()).add(where)
    global ADMIN_PHRASES
    ADMIN_PHRASES = {fr for fr, places in sources.items() if all(w.endswith(ADMIN_ONLY) for w in places)}
    old = load("_phrases.json")
    by_fr = {pair[0]: pid for pid, pair in old.items()}
    english = {}
    for fr, en, where in found:
        if fr in english and english[fr][0] != en:
            print(f"! same French, two English texts: {fr!r} -> {english[fr][0]!r} ({english[fr][1]}) / {en!r} ({where})")
        english.setdefault(fr, (en, where))
    next_id = max([int(pid[1:]) for pid in old] or [0]) + 1
    phrases = {}
    for fr, (en, _where) in english.items():
        pid = by_fr.get(fr)
        if not pid:
            pid = f"p{next_id:04d}"
            next_id += 1
        phrases[pid] = [fr, en]
    phrases = dict(sorted(phrases.items()))
    os.makedirs(LOCALES, exist_ok=True)
    with open(os.path.join(LOCALES, "_phrases.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(phrases, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    dropped = len(set(old) - set(phrases))
    print(f"{len(phrases)} phrases ({len(set(phrases) - set(old))} new, {dropped} dropped)")
    return phrases


def used_keys() -> list[str]:
    """Keys of translations.py that some template, script or module still names (the others are never shown)."""
    from app.translations import TRANSLATIONS
    source = ""
    for pattern in ("**/*.html", "**/*.py", "static/js/**/*.js"):
        for path in glob.glob(os.path.join(APP, pattern), recursive=True):
            if not path.endswith("translations.py"):
                source += open(path, encoding="utf-8").read()
    return [key for key in TRANSLATIONS["en"] if re.search(rf"""['"]{re.escape(key)}['"]""", source) and key != "footer.version"]


def todo(lang: str, phrases: dict) -> None:
    from app.translations import TRANSLATIONS
    done = load(f"{lang}.json")
    for key in used_keys():
        if key not in done:
            print(json.dumps([key, TRANSLATIONS["fr"].get(key, ""), TRANSLATIONS["en"][key]], ensure_ascii=False))
    for pid, (fr, en) in phrases.items():
        if pid not in done and fr not in ADMIN_PHRASES:
            print(json.dumps([pid, fr, en], ensure_ascii=False))


def coverage(phrases: dict) -> None:
    from app.i18n import CODES
    wanted = set(used_keys()) | {pid for pid, (fr, _en) in phrases.items() if fr not in ADMIN_PHRASES}
    from app.translations import TRANSLATIONS
    english = {**TRANSLATIONS["en"], **{pid: en for pid, (_fr, en) in phrases.items()}}
    holes = re.compile(r"\{\w+\}|%d")
    for lang in CODES:
        if lang in ("fr", "en"):
            continue
        done = load(f"{lang}.json")
        unknown = sorted(set(done) - wanted)
        print(f"{lang}: {len(wanted & set(done))}/{len(wanted)}" + (f"  (unknown ids: {', '.join(unknown[:8])})" if unknown else ""))
        # A translation must keep every placeholder of the English text, or a value would disappear
        for key, text in done.items():
            if key in english and sorted(holes.findall(text)) != sorted(holes.findall(english[key])):
                print(f"   ! {key}: placeholders {holes.findall(english[key])} -> {holes.findall(text)}")


if __name__ == "__main__":
    all_phrases = update()
    if len(sys.argv) == 3 and sys.argv[1] == "todo":
        todo(sys.argv[2], all_phrases)
    else:
        coverage(all_phrases)
