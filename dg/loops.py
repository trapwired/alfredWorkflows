import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from dg.alfred_items import emit, hint_row, row

LOOP_NOTE_SKILL = Path.home() / ".claude" / "skills" / "loop-note"
OPEN_STATUSES = ("aktiv", "wartet", "geparkt")
STORY_NOTE_SUFFIX = " - Jira"
VAULT_NAME = "notes-dg"


@dataclass(frozen=True)
class OpenLoop:
    name: str
    note_path: str
    status: str
    prio: int
    frist: str
    wartet_auf: str
    warp_link: str


def loop_from_note(relative_path, fields):
    name = Path(relative_path).stem
    if name.endswith(STORY_NOTE_SUFFIX):
        name = name[: -len(STORY_NOTE_SUFFIX)]
    prio = str(fields.get("prio", "")).strip()
    return OpenLoop(
        name=name,
        note_path=str(Path(relative_path).with_suffix("")),
        status=fields.get("status", ""),
        prio=int(prio) if prio.lstrip("-").isdigit() else -1,
        frist=str(fields.get("frist", "")).strip(),
        wartet_auf=str(fields.get("wartet_auf", "")).strip(),
        warp_link=str(fields.get("warp", "")).strip(),
    )


def open_loops_by_priority(loops):
    still_open = [loop for loop in loops if loop.status in OPEN_STATUSES]
    return sorted(still_open, key=lambda loop: (OPEN_STATUSES.index(loop.status), -loop.prio, loop.name.lower()))


def obsidian_url(loop):
    return "obsidian://open?vault=" + VAULT_NAME + "&file=" + quote(loop.note_path, safe="")


def loop_row(loop):
    details = [loop.status]
    if loop.prio >= 0:
        details.append("prio " + str(loop.prio))
    if loop.wartet_auf:
        details.append("wartet auf " + loop.wartet_auf)
    if loop.frist:
        details.append("Frist " + loop.frist)
    note_url = obsidian_url(loop)
    if not loop.warp_link:
        details.append("kein Warp-Tab, Enter öffnet die Notiz")
    return row(
        loop.name,
        " · ".join(details),
        loop.warp_link or note_url,
        cmd=("Notiz in Obsidian öffnen", note_url),
        match=loop.name + " " + loop.status,
    )


def rows_for_loops(loops):
    rows = [loop_row(loop) for loop in open_loops_by_priority(loops)]
    return rows or [hint_row("Keine offenen Loops", "Kein Loop mit Status aktiv, wartet oder geparkt")]


def read_loops_from_vault():
    # loop_note.py owns what counts as a loop note (Loops/ plus story notes), so this list cannot drift from the cockpit.
    sys.path.insert(0, str(LOOP_NOTE_SKILL))
    import loop_note

    vault = loop_note.WORK_VAULT
    return [
        loop_from_note(note.relative_to(vault), loop_note.read_fields(loop_note.read_note(note)))
        for note in loop_note.loop_candidates(vault)
    ]


def main():
    emit(rows_for_loops(read_loops_from_vault()))


if __name__ == "__main__":
    main()
