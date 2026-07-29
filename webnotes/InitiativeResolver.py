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

    python -m webnotes.InitiativeResolver rebuild   # Zuordnung aus Vault + Jira neu aufbauen
    python -m webnotes.InitiativeResolver show      # Zuordnung und Vokabular ausgeben
"""
import collections
import configparser
import json
import re
import sys
from pathlib import Path

import requests
from requests.auth import HTTPBasicAuth

HERE = Path(__file__).resolve().parent
CACHE_PATH = HERE / 'initiative_map.json'
VAULT_JIRA_DIR = Path('/Users/fluffyoctopus/kDrive/Dominic/notes/Spaces/Home/DG/Jira')

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


def vocabulary_from_vault():
    """Initiative-Werte, die in den Notizen wirklich vorkommen — kaputte Frontmatter aussortiert."""
    counter = collections.Counter()
    if not VAULT_JIRA_DIR.exists():
        return list(SEED_VOCABULARY)
    for path in VAULT_JIRA_DIR.glob('*.md'):
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


def rebuild():
    """Epic -> Initiative aus den Notizen lernen, in denen die Initiative schon gepflegt ist."""
    config = configparser.ConfigParser()
    config.read(HERE / 'config.ini')
    domain = config.get('API', 'jira_custom_domain')
    auth = HTTPBasicAuth(config.get('API', 'jira_email'), config.get('API', 'jira_token'))

    vocabulary = vocabulary_from_vault()
    by_key = {}
    for path in VAULT_JIRA_DIR.glob('*.md'):
        key = path.stem.split(' ')[0]
        if not re.match(r'^[A-Z]+-\d+$', key):
            continue
        text = path.read_text(errors='ignore')
        if not text.startswith('---'):
            continue
        match = re.search(r'^Initiative:[^\S\n]*(.*)$', text.split('---', 2)[1], re.M)
        value = match.group(1).strip().strip('"').strip("'") if match else ''
        if value and value != 'None' and value in vocabulary:
            by_key[key] = value

    votes = collections.defaultdict(collections.Counter)
    keys = sorted(by_key)
    for start in range(0, len(keys), 80):
        chunk = keys[start:start + 80]
        response = requests.post(
            f'https://{domain}/rest/api/3/search/jql',
            headers={'Accept': 'application/json', 'Content-Type': 'application/json'},
            auth=auth,
            json={'jql': f"key IN ({', '.join(chunk)})", 'fields': ['parent'], 'maxResults': 100},
            timeout=60)
        if response.status_code != 200:
            raise RuntimeError(f'JQL failed ({response.status_code}): {response.text[:200]}')
        for issue in response.json().get('issues', []):
            parent = (issue.get('fields') or {}).get('parent')
            if parent:
                votes[parent['key']][by_key[issue['key']]] += 1

    cache = {'epics': {epic: counter.most_common(1)[0][0] for epic, counter in votes.items()},
             'keys': by_key,
             'vocabulary': vocabulary}
    _save(cache)
    return cache


if __name__ == '__main__':
    case = sys.argv[1] if len(sys.argv) > 1 else 'show'
    if case == 'rebuild':
        result = rebuild()
        print(f"{len(result['epics'])} Epics zugeordnet, {len(result['vocabulary'])} Initiativen im Vokabular")
    else:
        result = _load()
        print(f"{len(result['epics'])} Epics, Vokabular: {', '.join(result['vocabulary'])}")
