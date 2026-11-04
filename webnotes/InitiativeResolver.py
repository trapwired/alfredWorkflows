"""Initiative einer Story bestimmen — beim Anlegen der Notiz, nicht erst beim Sprint-Report.

Vorher hing das an einer fest verdrahteten Liste von 15 Begriffen, die per Substring gegen den
Epic-Titel geprüft wurden. Alles, was nicht zufällig so hiess, landete auf `None` und musste
später von Hand nachgetragen werden.

Jetzt in vier Stufen, von präzise nach grob:

1. **Gelernte Zuordnung** Epic -> Initiative aus `initiative_map.json`. Exakt, kein Raten.
2. **Vokabular aus dem Vault** als Substring gegen Epic-Titel, dann gegen den Story-Titel.
   Das Vokabular sind die Initiative-Properties, die in den Notizen wirklich vorkommen.
3. **Story Lane** — `Fastlane`, `Superfastlane` und `Engineering` sind selbst gültige
   Initiativen. Greift für Stories ohne Epic.
4. Sonst `None`, damit im Report sichtbar bleibt, wo noch etwas fehlt.

Was über Stufe 2 oder 3 gefunden wird, wird für das Epic gelernt und beim nächsten Mal über
Stufe 1 beantwortet.

    python -m webnotes.InitiativeResolver rebuild            # Zuordnung aus Vault + Jira neu aufbauen
    python -m webnotes.InitiativeResolver show               # Zuordnung und Vokabular ausgeben
    python -m webnotes.InitiativeResolver backfill           # Probelauf: was liesse sich nachtragen?
    python -m webnotes.InitiativeResolver backfill --apply   # in die Notizen schreiben

Der Resolver läuft sonst nur beim Anlegen einer Notiz. Wurde sie erzeugt, bevor ihr Epic im
Cache stand, bleibt sie für immer auf `None` und fehlt im Sprint-Report — dafür `backfill`.
"""
import collections
import configparser
import json
import re
import sys
from pathlib import Path

import requests
from requests.auth import HTTPBasicAuth

from webnotes.paths import VaultPaths

HERE = Path(__file__).resolve().parent
CACHE_PATH = HERE / 'initiative_map.json'
CONFIG_PATH = HERE / 'config.ini'

LANE_FIELD = 'customfield_19101'
# Lanes, die zugleich Initiativen sind — Kapazitätstöpfe statt Vorhaben.
LANE_INITIATIVES = {'Fastlane', 'Superfastlane', 'Engineering'}

# Fallback, solange noch nie ein rebuild lief: die ursprünglich verdrahtete Liste.
SEED_VOCABULARY = ['ATK', 'ETK', 'Briefzentrum', 'Fastlane', 'FlexPack', 'Sorting', 'VAS',
                   'C-Hand', 'ON1', 'Sortierung', 'Komponentisierung', 'Packing Monitoring',
                   'TETRIS', 'PickPack', 'Gefahrengut']


def _load():
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text())
        except json.JSONDecodeError:
            pass
    return {'epics': {}, 'keys': {}, 'vocabulary': list(SEED_VOCABULARY)}


def _save(cache):
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2, sort_keys=True))


def jira_notes_dir():
    return VaultPaths.from_config(CONFIG_PATH).jira_dir


def vocabulary_from_vault():
    """Initiative-Werte, die in den Notizen wirklich vorkommen — kaputte Frontmatter aussortiert."""
    counter = collections.Counter()
    jira_dir = jira_notes_dir()
    if not jira_dir.exists():
        return list(SEED_VOCABULARY)
    for path in jira_dir.glob('*.md'):
        text = path.read_text(errors='ignore')
        if not text.startswith('---'):
            continue
        match = re.search(r'^Initiative:[^\S\n]*(.*)$', text.split('---', 2)[1], re.M)
        if not match:
            continue
        value = match.group(1).strip().strip('"').strip("'")
        # Frontmatter im Vault ist stellenweise verrutscht — solche Werte sind keine Initiativen.
        if (not value or value == 'None' or len(value) > 40
                or any(bad in value for bad in (':', '[', 'http', 'aliases'))):
            continue
        counter[value] += 1
    known = set(counter) | set(SEED_VOCABULARY)
    # Längere zuerst, damit "Sorter MVP2" vor "Sorting" greift.
    return sorted(known, key=lambda v: (-len(v), v))


def _real_epic(parent_key):
    return bool(parent_key) and parent_key not in ('N/A', 'None')


def resolve(parent_key=None, parent_summary='', summary='', lane=None, learn=True):
    """Gibt den Initiative-Namen zurück oder None."""
    cache = _load()
    if _real_epic(parent_key):
        if parent_key in cache['epics']:
            return cache['epics'][parent_key]
        # Das Parent kann selbst eine Story sein, deren Notiz die Initiative bereits kennt.
        if parent_key in cache.get('keys', {}):
            return cache['keys'][parent_key]

    vocabulary = cache.get('vocabulary') or SEED_VOCABULARY
    for haystack in (parent_summary if _real_epic(parent_key) else '', summary or ''):
        for topic in vocabulary:
            if topic.lower() in haystack.lower():
                if learn and _real_epic(parent_key):
                    cache['epics'][parent_key] = topic
                    _save(cache)
                return topic

    if lane in LANE_INITIATIVES:
        return lane
    return None


def _jira_fields(keys, fields):
    """Jira-Felder für viele Keys holen, in Blöcken zu 80. Gibt {key: fields} zurück."""
    config = configparser.ConfigParser()
    config.read(CONFIG_PATH)
    domain = config.get('API', 'jira_custom_domain')
    auth = HTTPBasicAuth(config.get('API', 'jira_email'), config.get('API', 'jira_token'))

    result = {}
    keys = sorted(keys)
    for start in range(0, len(keys), 80):
        chunk = keys[start:start + 80]
        response = requests.post(
            f'https://{domain}/rest/api/3/search/jql',
            headers={'Accept': 'application/json', 'Content-Type': 'application/json'},
            auth=auth,
            json={'jql': f"key IN ({', '.join(chunk)})", 'fields': fields, 'maxResults': 100},
            timeout=60)
        if response.status_code != 200:
            raise RuntimeError(f'JQL failed ({response.status_code}): {response.text[:200]}')
        for issue in response.json().get('issues', []):
            result[issue['key']] = issue.get('fields') or {}
    return result


def read_initiative(path):
    """Initiative-Wert aus dem Frontmatter.

    `None` heisst: die Notiz hat gar kein Initiative-Feld (SUP- und PR-Notizen etwa). Das ist
    etwas anderes als ein leeres Feld — ohne Feld gibt es nichts zu überschreiben.
    """
    text = path.read_text(errors='ignore')
    if not text.startswith('---'):
        return None
    match = re.search(r'^Initiative:[^\S\n]*(.*)$', text.split('---', 2)[1], re.M)
    return match.group(1).strip().strip('"').strip("'") if match else None


def note_paths():
    """Alle Jira-Notizen als (key, path), Dateien ohne sauberen Key übersprungen."""
    for path in sorted(jira_notes_dir().glob('*.md')):
        key = path.stem.split(' ')[0]
        if re.match(r'^[A-Z]+-\d+$', key):
            yield key, path


def backfill(apply=False):
    """Notizen ohne brauchbare Initiative erneut auflösen.

    Der Resolver läuft nur beim Anlegen einer Notiz. Alles, was angelegt wurde, bevor das Epic
    im Cache stand, bleibt sonst für immer auf `None` — und fehlt damit im Sprint-Report.
    Ohne `apply` wird nur berichtet, nichts geschrieben.
    """
    stale = {key: path for key, path in note_paths()
             if read_initiative(path) in ('', 'None', 'Unknown')}
    # `read_initiative` gibt None zurück, wenn die Notiz kein Initiative-Feld hat — die bleibt
    # draussen, sonst meldete der Lauf Treffer, bei denen es nichts zu ersetzen gibt.
    if not stale:
        return []

    fields = _jira_fields(stale, ['parent', 'summary', LANE_FIELD])
    fixed = []
    for key, path in sorted(stale.items()):
        data = fields.get(key)
        if not data:
            continue  # Key existiert in Jira nicht mehr — Notiz unangetastet lassen
        parent = data.get('parent') or {}
        topic = resolve(parent_key=parent.get('key'),
                        parent_summary=(parent.get('fields') or {}).get('summary', ''),
                        summary=data.get('summary', ''),
                        lane=(data.get(LANE_FIELD) or {}).get('value'))
        # `Unknown` steht im Vokabular, ist aber keine Antwort — es würde None nur umbenennen.
        if not topic or topic == 'Unknown':
            continue
        if apply:
            text = path.read_text(errors='ignore')
            path.write_text(re.sub(r'^(Initiative:).*$', lambda m: f'{m.group(1)} "{topic}"',
                                   text, count=1, flags=re.M))
        fixed.append((key, topic))
    return fixed


def rebuild():
    """Epic -> Initiative aus den Notizen lernen, in denen die Initiative schon gepflegt ist."""
    vocabulary = vocabulary_from_vault()
    by_key = {}
    for key, path in note_paths():
        value = read_initiative(path)
        if value and value != 'None' and value in vocabulary:
            by_key[key] = value

    votes = collections.defaultdict(collections.Counter)
    for key, data in _jira_fields(by_key, ['parent']).items():
        parent = data.get('parent')
        if parent:
            votes[parent['key']][by_key[key]] += 1

    # Nicht ersetzen, sondern ergänzen: `resolve()` lernt Epics einzeln dazu (Stufe 2), und
    # dafür gibt es oft keine Notiz, die beim Rebuild mitstimmen könnte. Ein Neuaufbau von null
    # hat diese Zuordnungen bisher stillschweigend weggeworfen. Die frischen Votes gewinnen.
    epics = dict(_load().get('epics', {}))
    epics.update({epic: counter.most_common(1)[0][0] for epic, counter in votes.items()})

    cache = {'epics': epics, 'keys': by_key, 'vocabulary': vocabulary}
    _save(cache)
    return cache


if __name__ == '__main__':
    case = sys.argv[1] if len(sys.argv) > 1 else 'show'
    if case == 'rebuild':
        result = rebuild()
        print(f"{len(result['epics'])} Epics zugeordnet, {len(result['vocabulary'])} Initiativen im Vokabular")
    elif case == 'backfill':
        apply = '--apply' in sys.argv
        fixed = backfill(apply=apply)
        for key, topic in fixed:
            print(f'{key} -> {topic}')
        verb = 'gesetzt' if apply else 'auflösbar (Probelauf, nichts geschrieben)'
        print(f'{len(fixed)} {verb}')
    else:
        result = _load()
        print(f"{len(result['epics'])} Epics, Vokabular: {', '.join(result['vocabulary'])}")
