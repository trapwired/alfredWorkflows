import configparser
import json
import os
import requests
from requests.auth import HTTPBasicAuth


def get_story_points(story_points):
    if '.' in str(story_points):
        story_points = str(story_points).split('.')[0]  # Take only the integer part
    return story_points


class JiraIssue:
    def __init__(self, key, summary, status, story_points, description):
        self.key = key
        self.summary = summary
        self.status = status
        self.story_points = get_story_points(story_points)
        self.description = description

    def __str__(self):
        return f"Key: {self.key}, Summary: {self.summary}, Status: {self.status}, Story Points: {self.story_points}, Description: {self.description[:100]}..."


def init_config():
    # Read configuration from config.ini
    config = configparser.ConfigParser()
    config.read(os.path.join(os.path.dirname(__file__), 'config.ini'))
    jira_token = config.get('API', 'jira_token')
    jira_email = config.get('API', 'jira_email')
    jira_custom_domain = config.get('API', 'jira_custom_domain')
    return jira_custom_domain, jira_email, jira_token


def get_jira_issue(issue_key):
    jira_custom_domain, jira_email, jira_token = init_config()

    url = f"https://{jira_custom_domain}/rest/api/3/issue/{issue_key}"
    auth = HTTPBasicAuth(jira_email, jira_token)
    headers = {
        "Accept": "application/json"
    }

    response = requests.get(url, headers=headers, auth=auth)

    # Parse the JSON data
    try:
        jira_data = json.loads(response.text)
        default = 'N/A'

        # Extract the requested fields
        key = jira_data.get('key', default)
        summary = jira_data.get('fields', {}).get('summary', default)

        # Get story points (usually stored in customfield_10013 in Jira Cloud)
        story_points = jira_data.get('fields', {}).get('customfield_10013', default)

        # Get status name
        status = jira_data.get('fields', {}).get('status', {}).get('name', default)

        # Get description - might be complex formatted content
        description = jira_data.get('fields', {}).get('description', {})
        description_text = "Description not available in simple text format"

        # Try to extract plain text from the description if it exists and has content
        if isinstance(description, dict) and 'content' in description:
            try:
                # Simple extraction attempt for plain text
                description_text = "".join([
                    node.get('text', '')
                    for content in description.get('content', [])
                    for node in content.get('content', [])
                    if 'text' in node
                ])
                if not description_text:
                    description_text = "Description exists but couldn't extract plain text"
            except Exception as e:
                description_text = f"Error extracting description text: {str(e)}"

        if key == default or summary == default or status == default or story_points == default:
            return None
        return JiraIssue(key, summary, status, story_points, description_text)

    except json.JSONDecodeError as e:
        return None


def get_transitions(issue_key):
    jira_custom_domain, jira_email, jira_token = init_config()

    url = f"https://{jira_custom_domain}/rest/api/3/issue/{issue_key}/transitions"
    auth = HTTPBasicAuth(jira_email, jira_token)
    headers = {
        "Accept": "application/json"
    }

    response = requests.get(url, headers=headers, auth=auth)

    if response.status_code == 200:
        return response.json().get('transitions', [])
    else:
        return []


def transition_issue(issue_key, transition_id):
    jira_custom_domain, jira_email, jira_token = init_config()

    url = f"https://{jira_custom_domain}/rest/api/3/issue/{issue_key}/transitions"
    auth = HTTPBasicAuth(jira_email, jira_token)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    payload = json.dumps({
        "fields": {
            "resolution": {
                "name": "Done"
            }
        },
        "transition": {
            "id": transition_id
        },

    })

    response = requests.request(
        "POST",
        url,
        data=payload,
        headers=headers,
        auth=auth
    )

    if response.status_code == 204:
        return issue_key
    else:
        return 'Failed to close issue: ' + issue_key + ' - ' + response.text


def get_all_issues_from_current_sprint():
    jira_custom_domain, jira_email, jira_token = init_config()

    url = f"https://{jira_custom_domain}/rest/api/2/search/jql"
    auth = HTTPBasicAuth(jira_email, jira_token)
    headers = {
        "Accept": "application/json"
    }

    query = {
        'jql': 'sprint in openSprints() and "Team[Team]"=c3db8dfc-c970-4639-8138-4ccdd1179649-26 and status = Resolved',
        'fields': 'key',
    }

    response = requests.get(url, headers=headers, params=query, auth=auth)

    if response.status_code == 200:
        return extract_issues_numbers(response.json().get('issues', []))
    else:
        return []

def extract_issues_numbers(json_data):
    return [item['key'] for item in json_data if 'key' in item]

