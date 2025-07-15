import sys
import os
from pathlib import Path

# Add the directory containing the webnotes package to sys.path
# This goes up two levels from the current script: alfredWorkflows -> webnotes -> parent
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Now we can import from webnotes package
from webnotes import NotesInterface


if __name__ == '__main__':
    # get url and title from command-line arguments
    main_path = Path(sys.argv[0])
    notes_interface = NotesInterface.NotesInterface(main_path.parent.parent)

    url_arg = sys.argv[1]
    website_title_arg = ' '.join(sys.argv[2:])

    # get filename, create file if it does not exist
    file_to_open = notes_interface.get_or_create_file(url_arg, website_title_arg)

    # export to alfred, opens obsidian
    print(file_to_open, end='')
