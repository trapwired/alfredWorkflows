import os.path
from enum import Enum
from pathlib import Path
import re
import datetime
import sys

# To avoid circular import issues, import JiraInterface functions inside the functions that need them
# rather than at the module level

FILE_EXTENSION = '.md'
DELIMITER = '漢'

OPTIONS = ['OPA', 'SUP']


class TEMPLATE(Enum):
    NO_TEMPLATE = 0
    JIRA = 1
    JIRA_PR = 2
    JIRA_SUP = 3

def jira_sup_template_values(url):
    return {
        '漢JIRA_LINK漢': url
    }

def jira_template_values(url):
    number = get_issue_number_from_url(url)
    # Import inside function to avoid circular import
    from webnotes.JiraInterface import get_jira_issue
    jira_issue = get_jira_issue(number)
    if not jira_issue:
        return {
            '漢JIRA_LINK漢': url,
            '漢JIRA_STORY_POINTS漢': '"424242"'
        }
    return {
        '漢JIRA_LINK漢': url,
        '漢JIRA_STORY_POINTS漢': f'"{jira_issue.story_points}"'
    }


def jira_pr_template_values(url, issue_url):
    return {
        '漢JIRA_PR_LINK漢': url,
        '漢JIRA_LINK漢': issue_url
    }


def get_header_with_link(url):
    return f'---\nlink: {url}\n---'


def replace_multiple(input_str: str, characters: str, replace_with: str):
    result = input_str
    for char in characters:
        result = result.replace(char, replace_with)
    return result


def get_filename(name: str):
    filename = replace_multiple(name, '/[]&"', ' ')
    filename = filename.strip()
    filename += FILE_EXTENSION
    return filename


def get_current_sprint():
    """
    Calculate the current sprint number based on two-week sprints.
    Reference point: Sprint 378 starts on July 1, 2025 (a Tuesday)
    Sprint duration: 2 weeks, always starting on Tuesdays
    """

    # Define the reference sprint and date
    reference_sprint = 378
    reference_date = datetime.date(2025, 7, 1)  # July 1, 2025 is a Tuesday

    # Get today's date
    today = datetime.date.today()

    # Calculate the number of days between today and the reference date
    days_diff = (today - reference_date).days

    # Calculate the number of complete sprints that have passed
    # Negative if we're before the reference date, positive if after
    sprints_diff = days_diff // 14

    # Calculate the current sprint
    current_sprint = reference_sprint + sprints_diff

    # Check if we need to adjust based on day of week
    # If we're past a reference date but not yet reached the next Tuesday,
    # we're still in the previous sprint
    if days_diff > 0 and days_diff % 14 < (today.weekday() - 1) % 7:
        current_sprint -= 1

    return current_sprint

def parse_index(index_file):
    result_dict = dict()
    for line in index_file.readlines():
        line_split = line.split(DELIMITER)
        if len(line_split) > 1:
            link = line_split[0].split('?')[0]
            title = line_split[1].rstrip()
            if title == 'None':
                continue
            if title.endswith(f'{FILE_EXTENSION}{FILE_EXTENSION}'):
                title = title.split(f'{FILE_EXTENSION}')[0] + f'{FILE_EXTENSION}'
            result_dict[link] = title
    return result_dict


def find(names, path):
    for root, dirs, files in os.walk(path):
        files = [x.rstrip() for x in files]
        for name in names:
            name = name.rstrip()
            if name in files:
                new_path = os.path.join(root, name)
                return Path(new_path).relative_to(path).as_posix()


def get_issue_number_from_filename(filename):
    potential_issue_number = filename.split()[0]
    if any([x in potential_issue_number for x in OPTIONS]):
        return potential_issue_number
    return None

def get_issue_number_from_url(url):
    match = re.search(r'(OPA|SUP)-\d{1,6}', url)
    if match:
        return match.group(0)
    return None


def find_jira(issue_number, path, filename):
    if not issue_number:
        return
    for root, dirs, files in os.walk(path):
        files = [x.rstrip() for x in files]
        for file in files:
            if file.startswith(issue_number):
                new_path = os.path.join(root, file)
                return Path(new_path).relative_to(path).as_posix()


def get_jira_issue_link_from_pr_title(filename):
    if 'noissue' in filename.lower():
        return '#NOISSUE-PR'

    for option in OPTIONS:
        split_1 = filename.split(f'{option}-')
        if len(split_1) == 1:
            # we are not in this option
            continue
        split_2 = split_1[1].split(' ')
        number = split_2[0]
        return f'https://jiradg.atlassian.net/browse/{option}-{number}'

def get_url_title(number):
    # Import inside function to avoid circular import
    from webnotes.JiraInterface import get_jira_issue
    jira_issue = get_jira_issue(number)
    if jira_issue:
        return f'[{jira_issue.key}] {jira_issue.summary} - Jira'
    return None

def get_jira_url(number):
    return f'https://jiradg.atlassian.net/browse/{number}'

def get_jira_url_and_title(number):
    url = get_jira_url(number)
    website_title = get_url_title(number)
    return url, website_title


def handle_special_jira_cases(url, website_title):
    if url.startswith('https://jiradg.atlassian.net'):
        possible_issue = url.split('&')[-1]
        if possible_issue.startswith('selectedIssue='):
            number = possible_issue.split('=')[1]
            new_url, new_website_title = get_jira_url_and_title(number)
            if not new_website_title:
                return new_url, website_title
            return new_url, new_website_title

    return url, website_title


def get_start_end_date(sprint_number=None):
    """
    Calculate the start and end date for a given sprint number.

    The sprint always starts on a Tuesday and ends on the Monday 13 days later.
    Reference: Sprint 377 lasted from June 17, 2025 (Tuesday) to June 30, 2025 (Monday).

    Args:
        sprint_number (int, optional): The sprint number to get dates for.
                                      If None, uses the current sprint.

    Returns:
        tuple: (start_date, end_date) as datetime.date objects
    """
    if not sprint_number:
        sprint_number = get_current_sprint()

    # Reference sprint data
    reference_sprint = 377
    reference_start = datetime.date(2025, 6, 17)  # Tuesday

    # Calculate the difference in sprints
    sprint_diff = sprint_number - reference_sprint

    # Calculate days difference (each sprint is 14 days)
    days_diff = sprint_diff * 14

    # Calculate the start and end dates
    start_date = reference_start + datetime.timedelta(days=days_diff)
    end_date = start_date + datetime.timedelta(days=13)  # 13 days later (inclusive of start date)

    return start_date, end_date
