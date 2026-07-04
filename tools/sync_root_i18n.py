#!/usr/bin/env python3
"""Maintain root i18n/ JSON locales (embedded directly from i18n/ via embed.go).

Each locale file:
  {
    "_meta": { "code": "zh_TW", "language_name": "繁體中文" },
    "project_name": "...",
    "exfil_<id>": "..."
  }

Add a language: create i18n/<code>.json (copy en_US.json, edit _meta), then run this script.
The script discovers all i18n/*.json (except catalog.json), merges missing UI keys from en_US,
and injects localized exfil_* keys from internal/points exfil_names.json and eftarkov_names.json.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
I18N_OUT = ROOT / "i18n"
CATALOG_PATH = I18N_OUT / "catalog.json"
EXFIL_NAMES = ROOT / "internal" / "points" / "exfil_names.json"
EFTARKOV_NAMES = ROOT / "internal" / "points" / "eftarkov_names.json"

EXFIL_PREFIX = "exfil_"
DEFAULT_LOCALE = "zh_TW"
FALLBACK_LOCALE = "en_US"

# Same mapping as internal/points/names.go localeToAPILang
LOCALE_TO_NAME_LANG: dict[str, str] = {
    "zh_TW": "zh_TW",
    "zh_CN": "zh_CN",
    "en_US": "en",
    "ja_JP": "ja",
    "cs_CZ": "cs",
    "fr_FR": "fr",
    "de_DE": "de",
    "hu_HU": "hu",
    "it_IT": "it",
    "ko_KR": "ko",
    "pl_PL": "pl",
    "pt_PT": "pt",
    "sk_SK": "sk",
    "es_ES": "es",
    "es_MX": "es",
    "tr_TR": "tr",
    "ru_RU": "ru",
    "ro_RO": "ro",
    "vi_VN": "en",
    "id_ID": "en",
    "th_TH": "en",
}


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")


def discover_locale_codes() -> list[str]:
    codes = sorted(
        path.stem
        for path in I18N_OUT.glob("*.json")
        if path.name != "catalog.json"
    )
    if not codes:
        raise SystemExit("FAIL no locale files in i18n/")
    return codes


def load_catalog() -> dict:
    if not CATALOG_PATH.is_file():
        return {"order": [], "default": DEFAULT_LOCALE}
    payload = load_json(CATALOG_PATH)
    if not isinstance(payload, dict):
        return {"order": [], "default": DEFAULT_LOCALE}
    return payload


def build_locale_order(discovered: list[str], catalog: dict) -> list[str]:
    order: list[str] = []
    seen: set[str] = set()
    for code in catalog.get("order") or []:
        if code in discovered and code not in seen:
            order.append(code)
            seen.add(code)
    for code in discovered:
        if code not in seen:
            order.append(code)
            seen.add(code)
    return order


def parse_locale_file(path: Path) -> tuple[str, str, dict[str, str]]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise SystemExit(f"FAIL invalid locale file {path}")

    meta = payload.get("_meta")
    if isinstance(meta, dict):
        code = str(meta.get("code") or path.stem).strip() or path.stem
        language_name = str(meta.get("language_name") or code).strip() or code
    else:
        code = path.stem
        language_name = str(payload.get("language_name") or code).strip() or code

    strings: dict[str, str] = {}
    for key, value in payload.items():
        if key == "_meta" or not isinstance(value, str):
            continue
        if key == "language_name":
            continue
        strings[key] = value
    return code, language_name, strings


def pick_name_lang(locale_code: str) -> str:
    return LOCALE_TO_NAME_LANG.get(locale_code, "en")


def pick_localized_name(langs: dict, lang: str) -> str:
    if not isinstance(langs, dict):
        return ""
    name = langs.get(lang) or ""
    if not name and lang == "zh_CN":
        name = langs.get("zh") or ""
    if not name:
        name = langs.get("en") or ""
    return str(name).strip()


def load_name_sources() -> dict[str, dict]:
    merged: dict[str, dict] = {}

    def merge(path: Path) -> None:
        if not path.is_file():
            return
        payload = load_json(path)
        if isinstance(payload, dict):
            merged.update(payload)

    merge(EXFIL_NAMES)
    merge(EFTARKOV_NAMES)
    return merged


def localized_exfil_names(locale_code: str, sources: dict[str, dict]) -> dict[str, str]:
    lang = pick_name_lang(locale_code)
    out: dict[str, str] = {}
    for exfil_id, langs in sources.items():
        name = pick_localized_name(langs, lang)
        if name:
            out[str(exfil_id)] = name
    return out


def strip_exfil_keys(strings: dict[str, str]) -> None:
    for key in list(strings.keys()):
        if key.startswith(EXFIL_PREFIX):
            del strings[key]


def inject_exfil_keys(strings: dict[str, str], exfil_names: dict[str, str]) -> None:
    strip_exfil_keys(strings)
    for exfil_id, name in exfil_names.items():
        strings[f"{EXFIL_PREFIX}{exfil_id}"] = name


def ui_string_keys(strings: dict[str, str]) -> dict[str, str]:
    return {k: v for k, v in strings.items() if not k.startswith(EXFIL_PREFIX)}


def merge_missing_ui(target: dict[str, str], fallback: dict[str, str]) -> None:
    for key, value in ui_string_keys(fallback).items():
        if key not in target or not str(target.get(key) or "").strip():
            target[key] = value


def build_locale_document(code: str, language_name: str, strings: dict[str, str]) -> dict[str, object]:
    doc: dict[str, object] = {
        "_meta": {
            "code": code,
            "language_name": language_name,
        }
    }
    ui_keys = sorted(k for k in strings if not k.startswith(EXFIL_PREFIX))
    exfil_keys = sorted(k for k in strings if k.startswith(EXFIL_PREFIX))
    for key in ui_keys:
        doc[key] = strings[key]
    for key in exfil_keys:
        doc[key] = strings[key]
    return doc


def table_key_count(strings: dict[str, str]) -> int:
    # Matches Go LocaleTable: strings + language_name from _meta
    return len(strings) + 1



def main() -> None:
    I18N_OUT.mkdir(parents=True, exist_ok=True)
    discovered = discover_locale_codes()
    catalog = load_catalog()
    order = build_locale_order(discovered, catalog)

    if FALLBACK_LOCALE not in discovered:
        raise SystemExit(f"FAIL missing fallback locale {FALLBACK_LOCALE}.json")

    name_sources = load_name_sources()
    if len(name_sources) < 100:
        raise SystemExit("FAIL too few exfil names loaded")

    _, _, en_strings = parse_locale_file(I18N_OUT / f"{FALLBACK_LOCALE}.json")
    en_ui = ui_string_keys(en_strings)

    display_names: dict[str, str] = {}
    counts: dict[str, int] = {}

    for code in order:
        path = I18N_OUT / f"{code}.json"
        if not path.is_file():
            print(f"SKIP {code}: file missing")
            continue
        file_code, language_name, strings = parse_locale_file(path)
        if file_code != code:
            print(f"WARN {path.name}: _meta.code={file_code} filename={code}, using filename")
            file_code = code
        merge_missing_ui(strings, en_ui)
        inject_exfil_keys(strings, localized_exfil_names(code, name_sources))
        save_json(path, build_locale_document(file_code, language_name, strings))
        display_names[file_code] = language_name
        counts[file_code] = table_key_count(strings)
        print(f"OK i18n/{file_code}.json ({counts[file_code]} keys)")

    default_locale = str(catalog.get("default") or DEFAULT_LOCALE)
    if default_locale not in order:
        default_locale = DEFAULT_LOCALE if DEFAULT_LOCALE in order else order[0]

    save_json(
        CATALOG_PATH,
        {
            "order": order,
            "default": default_locale,
            "display_names": display_names,
            "key_counts": counts,
        },
    )
    print("OK i18n/catalog.json")

    print("\nLocale key counts:")
    for code in order:
        if code in counts:
            label = display_names.get(code, code)
            try:
                print(f"  {code:<8} {counts[code]:>4}  {label}")
            except UnicodeEncodeError:
                print(f"  {code:<8} {counts[code]:>4}")


if __name__ == "__main__":
    main()
