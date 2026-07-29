"""Sprint-Wechsel am Planning Day: offene Stories in den nächsten Sprint schieben und den
aktuellen Sprint schliessen.

Getrennt in Vorschau und Ausführung, damit vor jedem Schreibzugriff sichtbar ist, was passiert.

    sprints   alle aktiven und zukünftigen Sprints auflisten
    plan      Vorschau: welche Stories würden vom aktiven in den nächsten Sprint wandern
    move      die Vorschau ausführen
    close     den aktiven Sprint schliessen (erst nachdem move gelaufen ist)

Alle Befehle geben JSON auf stdout aus. Exit 0 = ok, 1 = Fehler, 2 = nichts zu tun.
"""
import configparser
import json
import os
import sys

import requests
from requests.auth import HTTPBasicAuth

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from webnotes import JiraInterface

# Stories in diesen Status gelten als abgeschlossen und wandern nicht mit.
DONE_STATUSES = {'Closed', 'Resolved', 'Done'}

TEAM_JQL = '"Team[Team]" = 26'


def _auth():
    domain, email, token, board_id = JiraInterface.init_config()
    return domain, HTTPBasicAuth(email, token), board_id


def _sprints():
    """Aktive und zukünftige Sprints des Boards, in Jira-Reihenfolge."""
    return JiraInterface.get_all_open_sprints()


def _active_and_next():
    sprints = _sprints()
    active = next((s for s in sprints if s.state == 'active'), None)
    future = [s for s in sprints if s.state == 'future']
    nxt = future[0] if future else None
    return active, nxt


def _issues_in_sprint(sprint_id):
    """Alle Team-Phoenix-Issues eines Sprints. Paginiert, weil ein Sprint > 50 Issues haben kann."""
    domain, auth, _ = _auth()
    url = f'https://{domain}/rest/agile/1.0/sprint/{sprint_id}/issue'
    issues, start_at = [], 0
    while True:
        response = requests.get(
            url,
            headers={'Accept': 'application/json'},
            auth=auth,
            params={'startAt': start_at, 'maxResults': 50, 'jql': TEAM_JQL,
                    'fields': 'summary,status,assignee,issuetype'},
        )
        if response.status_code != 200:
            raise RuntimeError(f'GET sprint {sprint_id} issues failed: {response.status_code} {response.text}')
        payload = response.json()
        for raw in payload.get('issues', []):
            fields = raw.get('fields', {})
            assignee = fields.get('assignee') or {}
            issues.append({
                'key': raw['key'],
                'summary': fields.get('summary', ''),
                'status': (fields.get('status') or {}).get('name', ''),
                'type': (fields.get('issuetype') or {}).get('name', ''),
                'assignee': assignee.get('displayName'),
            })
        start_at += len(payload.get('issues', []))
        if start_at >= payload.get('total', 0) or not payload.get('issues'):
            break
    return issues


def _carry_over(active):
    issues = _issues_in_sprint(active.id)
    return [i for i in issues if i['status'] not in DONE_STATUSES], issues


def cmd_sprints():
    return {'sprints': [{'id': s.id, 'name': s.name, 'state': s.state} for s in _sprints()]}, 0


def cmd_plan():
    active, nxt = _active_and_next()
    if not active:
        return {'ok': False, 'reason': 'kein aktiver Sprint gefunden'}, 1
    if not nxt:
        return {'ok': False, 'reason': 'kein zukünftiger Sprint angelegt — erst im Jira-Backlog erstellen'}, 1

    carry, allissues = _carry_over(active)
    return {
        'ok': True,
        'from': {'id': active.id, 'name': active.name},
        'to': {'id': nxt.id, 'name': nxt.name},
        'total_in_sprint': len(allissues),
        'stays': len(allissues) - len(carry),
        'moves': carry,
    }, (0 if carry else 2)


def cmd_move():
    plan, code = cmd_plan()
    if code == 1:
        return plan, 1
    if not plan['moves']:
        return {'ok': True, 'moved': 0, 'reason': 'nichts offen — alles bleibt'}, 2

    domain, auth, _ = _auth()
    keys = [i['key'] for i in plan['moves']]
    moved, failed = [], []
    # Die Agile-API nimmt maximal 50 Issues pro Aufruf.
    for chunk_start in range(0, len(keys), 50):
        chunk = keys[chunk_start:chunk_start + 50]
        response = requests.post(
            f"https://{domain}/rest/agile/1.0/sprint/{plan['to']['id']}/issue",
            headers={'Accept': 'application/json', 'Content-Type': 'application/json'},
            auth=auth,
            data=json.dumps({'issues': chunk}),
        )
        if response.status_code == 204:
            moved.extend(chunk)
        else:
            failed.append({'issues': chunk, 'status': response.status_code, 'body': response.text})

    return {'ok': not failed, 'moved': len(moved), 'keys': moved,
            'to': plan['to'], 'failed': failed}, (0 if not failed else 1)


def cmd_close():
    active, _ = _active_and_next()
    if not active:
        return {'ok': False, 'reason': 'kein aktiver Sprint gefunden'}, 1

    carry, _ = _carry_over(active)
    if carry:
        return {'ok': False, 'reason': 'es sind noch offene Stories im Sprint — erst move ausführen',
                'open': [i['key'] for i in carry]}, 1

    domain, auth, _ = _auth()
    response = requests.post(
        f'https://{domain}/rest/agile/1.0/sprint/{active.id}',
        headers={'Accept': 'application/json', 'Content-Type': 'application/json'},
        auth=auth,
        data=json.dumps({'state': 'closed'}),
    )
    if response.status_code == 200:
        return {'ok': True, 'closed': {'id': active.id, 'name': active.name}}, 0
    return {'ok': False, 'reason': f'close failed: {response.status_code} {response.text}'}, 1


CASES = {'sprints': cmd_sprints, 'plan': cmd_plan, 'move': cmd_move, 'close': cmd_close}

if __name__ == '__main__':
    case = sys.argv[1] if len(sys.argv) > 1 else 'plan'
    if case not in CASES:
        print(json.dumps({'ok': False, 'reason': f'unknown case: {case}',
                          'cases': list(CASES)}, ensure_ascii=False))
        sys.exit(1)
    try:
        result, exit_code = CASES[case]()
    except Exception as error:  # nach aussen immer JSON, damit der Aufrufer nicht raten muss
        print(json.dumps({'ok': False, 'reason': str(error)}, ensure_ascii=False))
        sys.exit(1)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(exit_code)
