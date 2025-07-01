import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import NotesInterface
import FileAdjuster

from webnotes.utilities import get_issue_number_from_url


if __name__ == '__main__':
    # get url and title from command-line arguments
    main_path = Path(sys.argv[0])
    notes_interface = NotesInterface.NotesInterface(main_path.parent)

    url_arg = sys.argv[1]
    website_title_arg = ' '.join(sys.argv[2:])

    result = 'Not a Jira issue'
    # get filename, create file if it does not exist
    file_to_open = notes_interface.get_or_create_file(url_arg, website_title_arg)

    if file_to_open:
        complete_filepath = notes_interface.get_full_path(file_to_open)

        remaining_sp = FileAdjuster.adjust_file(complete_filepath, return_remaining_sp=True)

        if type(remaining_sp) is int:

            issue_nuber = get_issue_number_from_url(url_arg)

            result = f'{issue_nuber}: {remaining_sp}'
    # pass to alfred
    print(result, end='')