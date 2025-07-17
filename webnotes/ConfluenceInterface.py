import configparser
import os
import json

import requests
from requests.auth import HTTPBasicAuth

from webnotes.ConfluencePageNodes.ConfPageCreator import create_review_page, create_1to1_page


def init_config():
    # Read configuration from config.ini
    config = configparser.ConfigParser()
    config.read(os.path.join(os.path.dirname(__file__), 'config.ini'))
    jira_token = config.get('API', 'jira_token')
    jira_email = config.get('API', 'jira_email')
    conf_custom_domain = config.get('API', 'conf_custom_domain')
    return conf_custom_domain, jira_email, jira_token


def get_conf_page(page_id):
    conf_custom_domain, jira_email, jira_token = init_config()
    url = f"https://{conf_custom_domain}/wiki/api/v2/pages/{page_id}?body-format=atlas_doc_format"

    auth = HTTPBasicAuth(jira_email, jira_token)

    headers = {
        "Accept": "application/json"
    }

    response = requests.request(
        "GET",
        url,
        headers=headers,
        auth=auth
    )

    response_json = response.text
    output_path = os.path.join(os.path.dirname(__file__), 'download.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(response_json)
    print(f"Stored complete response to {output_path}")

    # Extract and clean up the body content
    try:
        response_data = json.loads(response_json)
        body_content = response_data.get('body', {}).get('atlas_doc_format', {}).get('value', '')

        # Replace escaped quotes with regular quotes
        body_content = body_content.replace('\\"', '"')

        # Save the cleaned body content to body.json
        body_output_path = os.path.join(os.path.dirname(__file__), 'body.json')
        with open(body_output_path, 'w', encoding='utf-8') as f:
            f.write(body_content)

        print(f"Body content successfully extracted and saved to {body_output_path}")

    except (json.JSONDecodeError, AttributeError) as e:
        print(f"Error processing body content: {e}")


def create_confluence_review_page():
    review_page = create_review_page()
    return _create_confluence_page(review_page)

def create_confluence_1to1_page():
    one_to_one_page = create_1to1_page()
    return _create_confluence_page(one_to_one_page)


def _create_confluence_page(new_page):
    conf_custom_domain, jira_email, jira_token = init_config()
    url = f"https://{conf_custom_domain}/wiki/api/v2/pages/"

    auth = HTTPBasicAuth(jira_email, jira_token)

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    payload = new_page.to_json()

    output_path = os.path.join(os.path.dirname(__file__), 'output', 'generated.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(payload)

    response = requests.request(
        "POST",
        url,
        data=payload,
        headers=headers,
        auth=auth
    )

    response_json = response.text
    if response.status_code == 200:
        output_path = os.path.join(os.path.dirname(__file__), 'output', 'response_created.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(response_json)

        # Parse the response JSON to extract title and URL
        response_data = json.loads(response_json)
        title = response_data.get('title', '')

        # Construct the complete URL by concatenating base and webui
        base_url = response_data.get('_links', {}).get('base', '')
        web_ui_path = response_data.get('_links', {}).get('webui', '')
        complete_url = f"{base_url}{web_ui_path}" if base_url and web_ui_path else ''

        return title, complete_url
    else:
        return f"Error: {response.status_code} - {response.text}", None
