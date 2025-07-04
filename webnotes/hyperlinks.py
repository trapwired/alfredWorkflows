import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from webnotes.utilities import get_issue_number_from_url, get_jira_url
from utilities import get_url_title
import JiraInterface


if __name__ == '__main__':
    # get url and title from command-line arguments
    main_path = Path(sys.argv[0])

    url_arg = sys.argv[1]
    website_title_arg = ' '.join(sys.argv[2:])

    # get jira issue number
    issue_number = get_issue_number_from_url(url_arg)
    if issue_number:
        possible_website_title_arg = get_url_title(issue_number)
        if possible_website_title_arg:
            website_title_arg = possible_website_title_arg
        else:
            f'{issue_number} - Jira'
        url_arg = get_jira_url(issue_number)

    result = f'{url_arg}\t{website_title_arg}'
    print(result, end='')
