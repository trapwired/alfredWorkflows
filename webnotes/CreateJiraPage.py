import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import JiraInterface


if __name__ == '__main__':
    # get url and title from command-line arguments
    main_path = Path(sys.argv[0])

    result = JiraInterface.createJiraPage()

    print(result, end='')
