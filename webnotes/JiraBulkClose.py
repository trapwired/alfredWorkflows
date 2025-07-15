import os
import sys
from pathlib import Path

import utilities

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import JiraInterface
import NotesInterface
import FileAdjuster


def get_all_issues():
    global issue_numbers
    issue_numbers = JiraInterface.get_all_done_issues_from_current_sprint()
    result = 'get_all_issues'
    if len(issue_numbers) == 0:
        result = 'NoIssues'
    else:
        result = '\n'.join(issue_numbers)
    return result


def close_all_issues(issue_numbers=None):
    main_path = Path(sys.argv[0])
    notes_interface = NotesInterface.NotesInterface(main_path.parent)

    if not issue_numbers:
        result = 'No issues provided to close'
    else:
        results = []
        for issue_number in issue_numbers:
            # close Story on Jira
            res = JiraInterface.transition_issue(issue_number, 151)

            # close Story in notes
            url, title = utilities.get_jira_url_and_title(issue_number)
            file_to_open = notes_interface.get_or_create_file(url, title)
            if file_to_open:
                complete_filepath = notes_interface.get_full_path(file_to_open)
                _ = FileAdjuster.adjust_file(complete_filepath)

            results.append(res)
        result = f'Closed {len(results)} issues: {", ".join(results)}'
    return result


if __name__ == '__main__':
    main_path = Path(sys.argv[0])
    if len(sys.argv) < 2:
        case_arg = 'get'
    else:
        case_arg = sys.argv[1]

    result = 'main'
    if case_arg == 'get':
        result = get_all_issues()
    elif case_arg == 'close_stories':
        result = close_all_issues(sys.argv[2:])
    print(result, end='')
