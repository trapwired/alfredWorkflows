import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import NotesInterface


if __name__ == '__main__':
    # get url and title from command-line arguments
    main_path = sys.argv[0]
    notes_interface = NotesInterface.NotesInterface(main_path)

    url_arg = sys.argv[1]
    website_title_arg = ' '.join(sys.argv[2:])

    # get filename, create file if it does not exist
    file_to_open = notes_interface.get_or_create_file(url_arg, website_title_arg)

    # export to alfred, opens obsidian
    print(file_to_open, end='')
