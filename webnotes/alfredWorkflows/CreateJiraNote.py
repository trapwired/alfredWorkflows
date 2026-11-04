"""Jira-Notiz im Vault anlegen, falls sie noch nicht existiert.

Dieselbe Mechanik, die JiraBulkClose und addStoryPoints benutzen (Template, Ordner, Dateiname
aus dem Jira-Titel) — nur als eigener Aufruf, damit der Second Brain eine Notiz erzeugen kann,
sobald Domi über eine Story schreibt, für die es noch keine gibt.

    CreateJiraNote.py OPA-52324 [OPA-53470 ...]

Gibt je Key eine Zeile aus: `created {key} {pfad}` oder `exists {key} {pfad}`. Idempotent.
"""
import os
import sys
from pathlib import Path

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from webnotes import NotesInterface
from webnotes import utilities


def main(keys):
    interface = NotesInterface.NotesInterface(Path(project_root) / 'webnotes')
    for key in keys:
        url, title = utilities.get_jira_url_and_title(key)
        if not title:
            print(f'failed {key} — Jira lieferte keinen Titel')
            continue
        existed = interface.find_note_by_link(url) is not None
        filename = interface.get_or_create_file(url, title)
        if not filename:
            print(f'failed {key}')
            continue
        print(f'{"exists" if existed else "created"} {key} {interface.get_full_path(filename)}')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1:])
