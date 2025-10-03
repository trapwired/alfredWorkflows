import os
import sys
from pathlib import Path

# Add the directory containing the webnotes package to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from webnotes.utilities import get_issue_number_from_url, get_jira_url, get_url_title
from webnotes import NotesInterface

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
    else:
        url_arg, website_title_arg = NotesInterface.handle_special_jira_cases(url_arg, website_title_arg)

    result = f'{url_arg}\t{website_title_arg}'
    print(result, end='')
