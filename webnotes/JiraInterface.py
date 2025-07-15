import configparser
import json
import os
import requests
from requests.auth import HTTPBasicAuth

# Using absolute import to avoid circular imports
from webnotes import utilities


def get_story_points(story_points):
    if '.' in str(story_points):
        story_points = str(story_points).split('.')[0]  # Take only the integer part
    return story_points


def get_parent(parent):
    parent_number, parent_summary = parent
    possible_topics = ['ATK', 'ETK', 'Briefzentrum', 'Fastlane', 'FlexPack', 'Sorting', 'VAS', 'C-Hand', 'ON1', 'Sortierung']
    for topic in possible_topics:
        if topic.lower() in parent_summary.lower():
            return parent_number, topic
    return parent_number, None


class JiraIssue:
    def __init__(self, key, summary, status, story_points, description, assignee, reporter, parent):
        self.key = key
        self.summary = summary
        self.status = status
        self.story_points = get_story_points(story_points)
        self.description = description
        self.assignee = assignee
        self.reporter = reporter
        parent_number, topic = get_parent(parent)  # Tuple of (parent_key, parent_topic)
        self.parent_key = parent_number
        self.parent_topic = topic

    def __str__(self):
        return f"{self.key} ({self.parent_topic}), {self.summary}, {self.status}, {self.story_points}, {self.description[:100]}..."

    def get_link(self):
        return utilities.get_jira_url(self.key)


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

        # get Assignee information
        assignee_id = jira_data.get('fields', {}).get('assignee', {}).get('accountId', default)
        assignee_name = jira_data.get('fields', {}).get('assignee', {}).get('displayName', default)

        # get Reporter information
        reporter_id = jira_data.get('fields', {}).get('reporter', {}).get('accountId', default)
        reporter_name = jira_data.get('fields', {}).get('reporter', {}).get('displayName', default)

        # Get Parent information if it exists
        parent_key = jira_data.get('fields', {}).get('parent', {}).get('key', default)
        parent_summary = jira_data.get('fields', {}).get('parent', {}).get('fields', {}).get('summary', default)

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
        return JiraIssue(key, summary, status, story_points, description_text, (assignee_id, assignee_name), (reporter_id, reporter_name), (parent_key, parent_summary))

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


def get_all_done_issues_from_current_sprint():
    jira_custom_domain, jira_email, jira_token = init_config()

    url = f"https://{jira_custom_domain}/rest/api/2/search/jql"
    auth = HTTPBasicAuth(jira_email, jira_token)
    headers = {
        "Accept": "application/json"
    }

    query = {
        'jql': 'sprint in openSprints() AND "Team[Team]" = "c3db8dfc-c970-4639-8138-4ccdd1179649-26" AND status IN (Resolved, Closed)',
        'fields': 'key',
    }

    response = requests.get(url, headers=headers, params=query, auth=auth)

    if response.status_code == 200:
        return extract_issues_numbers(response.json().get('issues', []))
    else:
        return []


def get_finish_sprint_table_data():
    issue_numbers = get_all_done_issues_from_current_sprint()
    table_data = []
    for issue_number in issue_numbers:
        table_data.append(get_jira_issue(issue_number))
    return table_data


def extract_issues_numbers(json_data):
    return [item['key'] for item in json_data if 'key' in item]
