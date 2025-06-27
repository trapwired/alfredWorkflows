import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import NotesInterface
import FileAdjuster


if __name__ == '__main__':
    # get url and title from command-line arguments
    main_path = sys.argv[0]
    notes_interface = NotesInterface.NotesInterface(main_path)

    url_arg = sys.argv[1]
    website_title_arg = ' '.join(sys.argv[2:])

    # get filename, create file if it does not exist
    file_to_open = notes_interface.get_or_create_file(url_arg, website_title_arg)
    complete_filepath = notes_interface.get_full_path(file_to_open)

    result = FileAdjuster.adjust_file(complete_filepath)

    # export to alfred, opens obsidian
    print(result, end='')
