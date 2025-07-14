import configparser
import os

import requests
from requests.auth import HTTPBasicAuth

from webnotes.ConfluencePageNodes.ConfPageCreator import create_review_page


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
    output_path = os.path.join(os.path.dirname(__file__), 'review-page-complete.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(response_json)


def create_conf_page():
    conf_custom_domain, jira_email, jira_token = init_config()
    url = f"https://{conf_custom_domain}/wiki/api/v2/pages/"

    auth = HTTPBasicAuth(jira_email, jira_token)

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    # Create a new ReviewPage object with sample data
    review_page = create_review_page()
    payload = review_page.to_json()

    output_path = os.path.join(os.path.dirname(__file__), 'generated.json')
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
    print(response_json[:200])


if __name__ == '__main__':
    # get_conf_page(170983456823)
    create_conf_page()
