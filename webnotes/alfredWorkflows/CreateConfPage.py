import os
import sys
from pathlib import Path

import pyperclip

# Add the directory containing the webnotes package to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from webnotes import ConfluenceInterface


def create_review_page():
    title, url = ConfluenceInterface.create_confluence_review_page()
    if url:
        pyperclip.copy(url)
    return title


def create_1to1_page():
    title, url = ConfluenceInterface.create_confluence_1to1_page()
    if url:
        pyperclip.copy(url)
    return title


cases = {
    "review": create_review_page,
    "1to1": create_1to1_page
}

if __name__ == '__main__':
    main_path = Path(sys.argv[0])
    if len(sys.argv) < 2:
        print('specify which type of page to create')
        sys.exit(0)

    case_arg = sys.argv[1]
    if case_arg not in cases.keys():
        print(f'Unknown case: {case_arg}')
        sys.exit(0)

    result = cases[case_arg]()

    print(result, end='')
