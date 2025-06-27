import configparser
import json
import os
import requests
from requests.auth import HTTPBasicAuth

class JiraIssue:
    def __init__(self, key, summary, status, story_points, description):
        self.key = key
        self.summary = summary
        self.status = status
        self.story_points = story_points
        self.description = description

    def __str__(self):
        return f"Key: {self.key}, Summary: {self.summary}, Status: {self.status}, Story Points: {self.story_points}, Description: {self.description[:100]}..."

def get_jira_issue(issue_key):
    # Read configuration from config.ini

    config = configparser.ConfigParser()
    config.read(os.path.join(os.path.dirname(__file__), 'config.ini'))

    jira_token = config.get('API', 'jira_token')
    jira_email = config.get('API', 'jira_email')
    jira_custom_domain = config.get('API', 'jira_custom_domain')

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
