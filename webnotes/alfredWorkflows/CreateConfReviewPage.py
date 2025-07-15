import os
import sys
import pyperclip

# Add the directory containing the webnotes package to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from webnotes import ConfluenceInterface


if __name__ == '__main__':
    title, url = ConfluenceInterface.create_confluence_review_page()
    if url:
        pyperclip.copy(url)

    print(title, end='')
