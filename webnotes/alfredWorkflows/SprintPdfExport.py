"""Sprint-Report als PDF — Seite 1 für die PO, ab Seite 2 die Details.

Die Notiz „Story Points done in Sprint" rendert ihre Tabellen über Dataview, das gibt es nur
innerhalb von Obsidian. Dieses Skript rechnet dieselben Zahlen direkt auf den Jira-Notizen nach
und zeichnet daraus ein PDF — kein offenes Obsidian nötig, keine externe PDF-Engine.

    SprintPdfExport.py [--sprint 405] [--out ~/Desktop] [--version 1]
                       [--no-jira]        nur Vault-Daten, kein Initiativen-Scope
                       [--create-notes]   fehlende Jira-Notizen anlegen (schreibt in den Vault)

Ohne --sprint wird die Property `SprintNumber` aus der Notiz gelesen. Existiert die Zieldatei
schon, wird die Versionsnummer hochgezählt statt überschrieben.
"""
import argparse
import collections
import configparser
import os
import re
import sys
import unicodedata
from pathlib import Path

import requests
from requests.auth import HTTPBasicAuth

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from webnotes.paths import VaultPaths

CONFIG_PATH = Path(project_root) / 'webnotes' / 'config.ini'

SP_FIELD = 'customfield_10013'
TEAM_JQL = '"Team[Team]" = 26'
# Keine Vorhaben, sondern Kapazitätstöpfe. Ein Topf wird nie fertig, darum bleibt er aus
# „Fortschritt je Initiative“ draussen — ein Fortschrittsbalken hätte dort kein Ziel.
POOLS = {'Fastlane', 'Superfastlane', 'Engineering'}

PAGE_W, PAGE_H = 842, 595  # A4 quer
MARGIN = 40
LINE = 12

ACCENT = (0.165, 0.471, 0.839)   # #2a78d6
INK = (0.04, 0.04, 0.04)
MUTED = (0.42, 0.42, 0.40)
RULE = (0.80, 0.80, 0.78)
TRACK = (0.90, 0.90, 0.88)


# ------------------------------------------------------------------ Vault lesen

def read_frontmatter(path):
    text = path.read_text(errors='ignore')
    if not text.startswith('---'):
        return {}
    block = text.split('---', 2)[1]
    fields = {}
    for line in block.splitlines():
        # [^\S\n] statt \s: \s würde den Zeilenumbruch fressen und den Wert der Folgezeile klauen
        match = re.match(r'^([A-Za-z][\w-]*):[^\S\n]*(.*)$', line)
        if match:
            fields[match.group(1)] = match.group(2).strip().strip('"').strip("'")
    return fields


def parse_done(sp_done):
    """'403: 1, 405: 2' -> {'403': 1.0, '405': 2.0}"""
    result = {}
    for part in sp_done.split(','):
        if ':' not in part:
            continue
        sprint, value = part.split(':', 1)
        try:
            result[sprint.strip()] = float(value.strip())
        except ValueError:
            pass
    return result


def number(value, default=0.0):
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


def fmt(value):
    return str(int(value)) if float(value).is_integer() else f'{value:.1f}'


def load_notes(jira_dir):
    notes = []
    for path in sorted(jira_dir.glob('*.md')):
        fields = read_frontmatter(path)
        key = path.stem.split(' ')[0]
        if not re.match(r'^[A-Z]+-\d+$', key):
            continue
        done_map = parse_done(fields.get('SP-done', ''))
        notes.append({
            'key': key,
            'path': path,
            'title': re.sub(r'\s+-\s+Jira$', '', path.stem),
            'raw_done': fields.get('SP-done', ''),
            'done_map': done_map,
            'total_done': sum(done_map.values()),
            'total': number(fields.get('Total-SP')),
            'closed': fields.get('closedInSprint', '').strip(),
            'initiative': fields.get('Initiative', '').strip() or 'None',
        })
    return notes


def sprint_stories(notes, sprint, open_sprint_keys=()):
    """Stories mit Buchung im Sprint, plus offene Sprint-Mitglieder ohne Buchung
    (aus Jira, damit der Carry-over vollständig ist)."""
    rows = []
    for note in notes:
        booked = sprint in note['done_map']
        left = note['total'] - note['total_done']
        # Unbebuchte Sprint-Mitglieder nur mit Rest > 0 — sonst gibt es nichts zu carry-overn
        if not booked and (note['key'] not in open_sprint_keys or left <= 0):
            continue
        row = dict(note)
        row['done_sprint'] = note['done_map'].get(sprint, 0)
        row['left'] = left
        rows.append(row)
    return rows


def velocity(notes, sprint, span=8):
    per_sprint = collections.Counter()
    for note in notes:
        for key, value in note['done_map'].items():
            if key.isdigit():
                per_sprint[key] += value
    ordered = sorted(per_sprint, key=int)
    if sprint in ordered:
        ordered = ordered[:ordered.index(sprint) + 1]
    return [(s, per_sprint[s]) for s in ordered[-span:]]


# ------------------------------------------------------------------ Jira: Scope je Initiative

def jira_auth():
    config = configparser.ConfigParser()
    config.read(CONFIG_PATH)
    domain = config.get('API', 'jira_custom_domain')
    return domain, HTTPBasicAuth(config.get('API', 'jira_email'), config.get('API', 'jira_token'))


def jira_search(jql, fields, limit=400):
    domain, auth = jira_auth()
    issues, start = [], 0
    while start < limit:
        response = requests.post(
            f'https://{domain}/rest/api/3/search/jql',
            headers={'Accept': 'application/json', 'Content-Type': 'application/json'},
            auth=auth,
            json={'jql': jql, 'fields': fields, 'maxResults': 100,
                  **({'nextPageToken': issues[-1]['_token']} if False else {})},
            timeout=60,
        )
        if response.status_code != 200:
            raise RuntimeError(f'JQL failed ({response.status_code}): {response.text[:200]}')
        payload = response.json()
        batch = payload.get('issues', [])
        issues.extend(batch)
        if payload.get('isLast', True) or not batch:
            break
        start += len(batch)
        break  # eine Seite reicht für unsere Grössenordnung; verhindert Endlosschleifen
    return issues


def sprint_sync(notes, sprint):
    """Sprint-Mitglieder aus Jira holen: stale Total-SP in den Notizen nachziehen
    und die offenen Keys zurückgeben (für den vollständigen Carry-over)."""
    by_key = {n['key']: n for n in notes}
    open_keys, refreshed = set(), []
    for issue in jira_search(f'sprint = PHX{sprint} AND {TEAM_JQL}', ['status', SP_FIELD]):
        fields = issue.get('fields') or {}
        key = issue['key']
        if (fields.get('status') or {}).get('name') not in ('Closed', 'Resolved', 'Done'):
            open_keys.add(key)
        note = by_key.get(key)
        jira_total = number(fields.get(SP_FIELD))
        if note and jira_total and note['total'] != jira_total:
            content = note['path'].read_text()
            new_content, count = re.subn(r'(?m)^Total-SP:.*$', f'Total-SP: "{fmt(jira_total)}"', content)
            if count:
                note['path'].write_text(new_content)
                refreshed.append(f"{key}: {fmt(note['total'])} -> {fmt(jira_total)}")
                note['total'] = jira_total
    return open_keys, refreshed


def epic_to_initiative(notes):
    """Aus den Notizen mit gesetzter Initiative die Zuordnung Parent-Epic -> Initiative lernen."""
    known = [n for n in notes if n['initiative'] not in ('None', '')]
    votes = collections.defaultdict(collections.Counter)
    for chunk_start in range(0, len(known), 80):
        chunk = known[chunk_start:chunk_start + 80]
        keys = ', '.join(n['key'] for n in chunk)
        by_key = {n['key']: n['initiative'] for n in chunk}
        for issue in jira_search(f'key IN ({keys})', ['parent']):
            parent = (issue.get('fields') or {}).get('parent')
            if parent:
                votes[parent['key']][by_key.get(issue['key'], 'None')] += 1
    return {epic: counter.most_common(1)[0][0] for epic, counter in votes.items()}


def initiative_scope(notes, initiatives, epic_map):
    """Voller Scope je Initiative: alle Stories unter ihren Epics, auch künftige."""
    wanted_epics = [epic for epic, ini in epic_map.items() if ini in initiatives]
    if not wanted_epics:
        return {}, []
    done_by_key = {n['key']: n['total_done'] for n in notes}
    have_note = {n['key'] for n in notes}
    scope = collections.defaultdict(lambda: {'total': 0.0, 'done': 0.0, 'stories': 0, 'open': 0})
    missing = []
    for chunk_start in range(0, len(wanted_epics), 40):
        chunk = wanted_epics[chunk_start:chunk_start + 40]
        jql = f"parent IN ({', '.join(chunk)}) AND {TEAM_JQL}"
        for issue in jira_search(jql, ['parent', 'status', 'summary', SP_FIELD]):
            fields = issue.get('fields') or {}
            parent = (fields.get('parent') or {}).get('key')
            initiative = epic_map.get(parent)
            if not initiative:
                continue
            bucket = scope[initiative]
            bucket['total'] += number(fields.get(SP_FIELD))
            bucket['done'] += done_by_key.get(issue['key'], 0.0)
            bucket['stories'] += 1
            if (fields.get('status') or {}).get('name') not in ('Closed', 'Resolved', 'Done'):
                bucket['open'] += 1
            if issue['key'] not in have_note:
                missing.append((issue['key'], fields.get('summary', '')))
    return dict(scope), missing


def create_missing_notes(missing):
    from webnotes import NotesInterface, utilities
    interface = NotesInterface.NotesInterface(CONFIG_PATH.parent)
    created = []
    for key, _ in missing:
        url, title = utilities.get_jira_url_and_title(key)
        if interface.get_or_create_file(url, title):
            created.append(key)
    return created


# ------------------------------------------------------------------ PDF

BEYOND_LATIN1 = {'–': '-', '—': '-', '…': '...', '→': '->', '‘': "'", '’': "'",
                 '“': '"', '”': '"', '„': '"', '•': '-', '×': 'x', '✔': 'x', '❓': '?', '·': '-'}


def ascii_safe(text):
    text = unicodedata.normalize('NFC', str(text))
    for source, target in BEYOND_LATIN1.items():
        text = text.replace(source, target)
    return text.encode('latin-1', 'replace').decode('latin-1')


def esc(text):
    return ascii_safe(text).replace('\\', r'\\').replace('(', r'\(').replace(')', r'\)')


def clip(text, budget):
    text = str(text)
    return text if len(text) <= budget else text[:budget - 2] + '..'


class Pdf:
    """Minimaler PDF-Writer: Helvetica, Text, Linien, Flächen. Genug für Balken und Tabellen."""

    def __init__(self):
        self.pages = []
        self._new_page()

    def _new_page(self):
        self.stream = []
        self.y = PAGE_H - MARGIN
        self.pages.append(self.stream)

    def page_break(self):
        self._new_page()

    def space(self, needed=LINE):
        if self.y - needed < MARGIN:
            self._new_page()

    def text(self, content, x, size=9, bold=False, color=INK, y=None):
        font = 'F2' if bold else 'F1'
        pos_y = self.y if y is None else y
        r, g, b = color
        self.stream.append(
            f'BT /{font} {size} Tf {r:.3f} {g:.3f} {b:.3f} rg {x} {pos_y} Td ({esc(content)}) Tj ET')

    def right(self, content, x_right, size=9, bold=False, color=INK, y=None):
        width = len(ascii_safe(content)) * size * (0.56 if bold else 0.52)
        self.text(content, x_right - width, size=size, bold=bold, color=color, y=y)

    def rule(self, y=None, color=RULE):
        pos_y = self.y if y is None else y
        r, g, b = color
        self.stream.append(f'{r:.3f} {g:.3f} {b:.3f} RG 0.6 w {MARGIN} {pos_y} m {PAGE_W - MARGIN} {pos_y} l S')

    def rect(self, x, y, width, height, color):
        if width <= 0:
            return
        r, g, b = color
        self.stream.append(f'{r:.3f} {g:.3f} {b:.3f} rg {x} {y} {width:.2f} {height} re f')

    def heading(self, content, size=12):
        self.space(size + 26)
        self.y -= 14
        self.text(content, MARGIN, size=size, bold=True)
        self.y -= 6
        self.rule()
        self.y -= LINE + 2

    def hbars(self, rows, label_w=150, bar_w=330, value_fmt=lambda v: fmt(v), color=ACCENT):
        """rows: [(label, value, note)] — sortiert übergeben. Direkt beschriftet, keine Legende."""
        peak = max((r[1] for r in rows), default=0) or 1
        for label, value, note in rows:
            self.space(LINE + 3)
            self.text(clip(label, 26), MARGIN, size=8.5)
            width = bar_w * (value / peak)
            self.rect(MARGIN + label_w, self.y - 1, width, 7.5, color)
            self.text(value_fmt(value), MARGIN + label_w + bar_w + 10, size=8.5, bold=True)
            if note:
                self.text(note, MARGIN + label_w + bar_w + 55, size=8.5, color=MUTED)
            self.y -= LINE + 3
        self.y -= 4

    def columns(self, rows, height=64, width=26, gap=12):
        """rows: [(label, value)] — Verlauf über die Zeit, deshalb Säulen statt Balken."""
        self.space(height + 30)
        peak = max((v for _, v in rows), default=0) or 1
        base = self.y - height
        x = MARGIN
        for label, value in rows:
            bar = height * (value / peak)
            self.rect(x, base, width, max(bar, 1), ACCENT)
            self.text(fmt(value), x, size=7.5, bold=True, y=base + bar + 4)
            self.text(label, x, size=7.5, color=MUTED, y=base - 11)
            x += width + gap
        self.y = base - 24

    def progress(self, rows, label_w=150, bar_w=260):
        """rows: [(label, done, total, note)] — Anteil an einem bekannten Ganzen."""
        for label, done, total, note in rows:
            self.space(LINE + 3)
            self.text(clip(label, 26), MARGIN, size=8.5)
            self.rect(MARGIN + label_w, self.y - 1, bar_w, 7.5, TRACK)
            share = (done / total) if total else 0
            self.rect(MARGIN + label_w, self.y - 1, bar_w * min(share, 1), 7.5, ACCENT)
            self.text(f'{fmt(done)}/{fmt(total)} SP', MARGIN + label_w + bar_w + 10, size=8.5, bold=True)
            self.text(f'{share * 100:.0f}%', MARGIN + label_w + bar_w + 80, size=8.5)
            if note:
                self.text(note, MARGIN + label_w + bar_w + 120, size=8.5, color=MUTED)
            self.y -= LINE + 3
        self.y -= 4

    def table(self, headers, rows, widths):
        xs, offset = [], MARGIN
        for width in widths:
            xs.append(offset)
            offset += width
        self.space(LINE * 2)
        for head, x in zip(headers, xs):
            self.text(head, x, size=7.5, bold=True, color=MUTED)
        self.y -= 4
        self.rule()
        self.y -= LINE
        for row in rows:
            self.space()
            for cell, x, width in zip(row, xs, widths):
                self.text(clip(cell, max(4, int(width / 4.6))), x, size=8.5)
            self.y -= LINE
        self.y -= 4

    def build(self):
        objects, page_ids, first = [], [], 5
        for index in range(len(self.pages)):
            page_ids.append(first + index * 2)
        kids = ' '.join(f'{pid} 0 R' for pid in page_ids)
        objects.append('<< /Type /Catalog /Pages 2 0 R >>')
        objects.append(f'<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>')
        objects.append('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>')
        objects.append('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>')
        for index, stream in enumerate(self.pages):
            objects.append(
                f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_W} {PAGE_H}] '
                f'/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {first + index * 2 + 1} 0 R >>')
            objects.append(('STREAM', '\n'.join(stream).encode('latin-1', 'replace')))

        out = bytearray(b'%PDF-1.4\n')
        offsets = [0]
        for index, obj in enumerate(objects, start=1):
            offsets.append(len(out))
            if isinstance(obj, tuple):
                body = obj[1]
                out += f'{index} 0 obj\n<< /Length {len(body)} >>\nstream\n'.encode('latin-1')
                out += body + b'\nendstream\nendobj\n'
            else:
                out += f'{index} 0 obj\n{obj}\nendobj\n'.encode('latin-1')
        xref_at = len(out)
        out += f'xref\n0 {len(objects) + 1}\n'.encode('latin-1') + b'0000000000 65535 f \n'
        for offset in offsets[1:]:
            out += f'{offset:010d} 00000 n \n'.encode('latin-1')
        out += (f'trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n'
                f'startxref\n{xref_at}\n%%EOF\n').encode('latin-1')
        return bytes(out)


# ------------------------------------------------------------------ Report

def render(sprint, stories, notes, scope, missing_notes, jira_note):
    pdf = Pdf()
    delivered = sum(s['done_sprint'] for s in stories)
    closed = [s for s in stories if s['closed'] == sprint]
    carry = [s for s in stories if not s['closed']]
    carry_sp = sum(s['left'] for s in carry)

    # --- Seite 1: die Gesprächsgrundlage
    pdf.text(f'Sprint {sprint}', MARGIN, size=11, color=MUTED)
    pdf.y -= 30
    pdf.text(f'{fmt(delivered)} SP geliefert', MARGIN, size=28, bold=True)
    pdf.y -= 18
    pdf.text(f'{len(closed)} von {len(stories)} Stories abgeschlossen - '
             f'{fmt(carry_sp)} SP wandern in den nächsten Sprint', MARGIN, size=10, color=MUTED)
    pdf.y -= 10
    pdf.rule(color=(0.35, 0.35, 0.33))

    pdf.heading('Wohin die Story Points geflossen sind')
    per_initiative = collections.Counter()
    for story in stories:
        per_initiative[story['initiative']] += story['done_sprint']
    rows = sorted(per_initiative.items(), key=lambda kv: -kv[1])
    pdf.hbars([(name, value, f'{value / delivered * 100:.0f}%' if delivered else '')
               for name, value in rows], value_fmt=lambda v: f'{fmt(v)} SP')

    pdf.heading('Töpfe')
    initiative_sp = sum(v for k, v in per_initiative.items() if k not in POOLS)
    pool_rows = [(k, v) for k, v in per_initiative.items() if k in POOLS]
    split = [('Initiative-Arbeit', initiative_sp, ACCENT)] + [(k, v, ACCENT) for k, v in sorted(pool_rows)]
    peak = max((v for _, v, _ in split), default=1) or 1
    for label, value, color in split:
        pdf.space(LINE + 3)
        pdf.text(label, MARGIN, size=8.5)
        pdf.rect(MARGIN + 150, pdf.y - 1, 330 * (value / peak), 7.5, color)
        pdf.text(f'{fmt(value)} SP', MARGIN + 490, size=8.5, bold=True)
        pdf.text(f'{value / delivered * 100:.0f}%' if delivered else '', MARGIN + 535,
                 size=8.5, color=MUTED)
        pdf.y -= LINE + 3

    pdf.heading(f'Abgeschlossen in diesem Sprint  ({len(closed)})')
    pdf.table(['Story', 'SP im Sprint', 'Total SP', 'Initiative'],
              [[s['title'], fmt(s['done_sprint']), fmt(s['total']), s['initiative']] for s in closed],
              [460, 80, 80, 140])

    # --- Seite 2: Detail
    pdf.page_break()
    pdf.text('Detail', MARGIN, size=11, color=MUTED)
    pdf.y -= 16
    pdf.rule(color=(0.35, 0.35, 0.33))

    pdf.heading('Velocity - Story Points pro Sprint')
    pdf.columns(velocity(notes, sprint))

    pdf.heading('Fortschritt je Initiative')
    if scope:
        progress_rows = []
        for name in sorted(per_initiative, key=lambda n: -per_initiative[n]):
            if name in POOLS:
                continue
            data = scope.get(name)
            if not data or not data['total']:
                continue
            progress_rows.append((name, data['done'], data['total'],
                                  f"{data['open']} von {data['stories']} Stories offen"))
        if progress_rows:
            pdf.progress(progress_rows)
        else:
            pdf.text('Kein Scope aus Jira ableitbar.', MARGIN, size=8.5, color=MUTED)
            pdf.y -= LINE
    else:
        pdf.text(jira_note or 'Ohne Jira-Abfrage erstellt.', MARGIN, size=8.5, color=MUTED)
        pdf.y -= LINE

    pdf.heading(f'Carry-over in den nächsten Sprint  ({len(carry)}, {fmt(carry_sp)} SP)')
    pdf.table(['Story', 'SP im Sprint', 'Rest SP', 'Total SP', 'Initiative'],
              [[s['title'], fmt(s['done_sprint']), fmt(s['left']), fmt(s['total']), s['initiative']]
               for s in carry],
              [420, 80, 70, 70, 140])

    issues = []
    for story in stories:
        if story['initiative'] == 'None':
            issues.append(f"{story['key']}: keine Initiative")
        if not story['total']:
            issues.append(f"{story['key']}: kein Total-SP")
        if story['closed'] and story['closed'] != sprint:
            issues.append(f"{story['key']}: closedInSprint={story['closed']}")
        if story['left'] < 0:
            issues.append(f"{story['key']}: mehr abgebucht als geschätzt ({fmt(-story['left'])} SP)")
    if missing_notes:
        issues.append(f'{len(missing_notes)} Stories im Initiativen-Scope ohne Notiz im Vault')
    if issues:
        pdf.heading('Datenqualität')
        for item in issues:
            pdf.space()
            pdf.text('- ' + item, MARGIN, size=8.5, color=MUTED)
            pdf.y -= LINE
    return pdf.build()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sprint')
    parser.add_argument('--out', default=str(Path.home() / 'Desktop'))
    parser.add_argument('--version', type=int, default=1)
    parser.add_argument('--no-jira', action='store_true')
    parser.add_argument('--create-notes', action='store_true')
    args = parser.parse_args()

    paths = VaultPaths.from_config(CONFIG_PATH)
    overview = paths.notes / 'SCRUM/Story Points done in Sprint.md'
    sprint = args.sprint or read_frontmatter(overview).get('SprintNumber')
    if not sprint:
        print('Kein Sprint angegeben und keine SprintNumber in der Notiz gefunden.')
        return 1

    notes = load_notes(paths.jira_dir)
    open_sprint_keys = set()
    if not args.no_jira:
        try:
            open_sprint_keys, refreshed = sprint_sync(notes, sprint)
            for line in refreshed:
                print(f'  Total-SP aus Jira nachgezogen: {line}')
        except Exception as error:
            print(f'  ! Sprint-Sync nicht verfügbar: {error}')
    stories = sprint_stories(notes, sprint, open_sprint_keys)
    if not stories:
        print(f'Keine Stories mit Aufwand im Sprint {sprint} gefunden.')
        return 2

    scope, missing, jira_note = {}, [], ''
    if not args.no_jira:
        try:
            initiatives = {s['initiative'] for s in stories} - {'None'}
            scope, missing = initiative_scope(notes, initiatives, epic_to_initiative(notes))
        except Exception as error:
            jira_note = f'Initiativen-Scope nicht verfügbar: {error}'
            print(f'  ! {jira_note}')

    if missing and args.create_notes:
        created = create_missing_notes(missing)
        print(f'  {len(created)} Jira-Notizen angelegt')
        missing = []

    out_dir = Path(os.path.expanduser(args.out))
    version = args.version
    while (out_dir / f'Story Points Done im Sprint {sprint} V{version}.pdf').exists():
        version += 1
    target = out_dir / f'Story Points Done im Sprint {sprint} V{version}.pdf'
    target.write_bytes(render(sprint, stories, notes, scope, missing, jira_note))

    print(target)
    print(f'  {len(stories)} Stories, {fmt(sum(s["done_sprint"] for s in stories))} SP geliefert')
    if missing:
        print(f'  {len(missing)} Stories im Scope ohne Notiz — mit --create-notes anlegen')
    return 0


if __name__ == '__main__':
    sys.exit(main())
