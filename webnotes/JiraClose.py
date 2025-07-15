import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from webnotes.utilities import get_issue_number_from_url
import JiraInterface
import NotesInterface
import FileAdjuster

# Close Story on Jira and in notes
if __name__ == '__main__':
    # get url and title from command-line arguments
    main_path = Path(sys.argv[0])

    url_arg = sys.argv[1]
    website_title_arg = ' '.join(sys.argv[2:])

    # get jira issue number
    issue_number = get_issue_number_from_url(url_arg)
    result = 'Not a Jira issue'
    if issue_number:
        result = JiraInterface.transition_issue(issue_number, 151)

        notes_interface = NotesInterface.NotesInterface(main_path.parent)
        file_to_open = notes_interface.get_or_create_file(url_arg, website_title_arg)

        if file_to_open:
            complete_filepath = notes_interface.get_full_path(file_to_open)
            remaining_sp = FileAdjuster.adjust_file(complete_filepath)

    print(result, end='')
