import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from webnotes.utilities import get_issue_number_from_url
import JiraInterface


if __name__ == '__main__':
    # get url and title from command-line arguments
    main_path = Path(sys.argv[0])

    url_arg = sys.argv[1]

    # get jira issue number
    issue_number = get_issue_number_from_url(url_arg)
    result = 'Not a Jira issue'
    if issue_number:
        result = JiraInterface.transition_issue(issue_number, 151)

    print(result, end='')
