import json
import sys
from pathlib import Path
from urllib.parse import quote

GENERATED_DIR = Path(__file__).parent / "generated"
DATADOG_LOGS_URL = "https://app.datadoghq.eu/logs?query="


def query_tokens(argv):
    query = argv[1] if len(argv) > 1 else ""
    return query.strip().split()


def row(title, subtitle, arg, *, cmd=None, alt=None, ctrl=None, autocomplete=None, match=None):
    """One selectable Alfred row. cmd / alt / ctrl are (subtitle, arg) pairs for the modifier keys."""
    item = {"title": title, "subtitle": subtitle, "arg": arg, "valid": True}
    if autocomplete is not None:
        item["autocomplete"] = autocomplete
    if match is not None:
        item["match"] = match
    mods = {
        key: {"subtitle": modifier[0], "arg": modifier[1], "valid": True}
        for key, modifier in (("cmd", cmd), ("alt", alt), ("ctrl", ctrl))
        if modifier is not None
    }
    if mods:
        item["mods"] = mods
    return item


def url_row(title, url, *, alt=None, ctrl=None, autocomplete=None, match=None, subtitle=None):
    """A row that opens url on Enter and copies it on Cmd."""
    return row(
        title,
        subtitle or url,
        url,
        cmd=("Copy URL: " + url, url),
        alt=alt,
        ctrl=ctrl,
        autocomplete=autocomplete,
        match=match,
    )


def hint_row(title, subtitle, autocomplete=None):
    """A row that cannot be actioned: a hint or a 'nothing found' message."""
    item = {"title": title, "subtitle": subtitle, "valid": False}
    if autocomplete is not None:
        item["autocomplete"] = autocomplete
    return item


def datadog_logs_url(query):
    return DATADOG_LOGS_URL + quote(query, safe="")


def load_generated(file_name):
    with (GENERATED_DIR / file_name).open(encoding="utf-8") as handle:
        return json.load(handle)


def emit(rows):
    json.dump({"items": rows}, sys.stdout)
