import re
import os
from webnotes.utilities import get_issue_number_from_url
from webnotes.JiraInterface import get_jira_issue


def adjust_file(file_path):
    """
    Read and process a markdown file with Jira properties.

    Args:
        file_path: Complete path to the markdown file

    Returns:
        dict: Contains 'Total-SP' and 'SP-done' values or 'Not a jira story' message
    """
    if not os.path.exists(file_path):
        return "File does not exist: " + file_path

    try:
        with open(file_path, 'r') as file:
            content = file.read()

        # Check if the file has frontmatter (properties between --- markers)
        frontmatter_match = re.search(r'^---\s*\n(.*?)\n---', content, re.DOTALL)

        if not frontmatter_match:
            return "Not a jira story"

        frontmatter = frontmatter_match.group(1)

        # Process frontmatter line by line to properly extract the properties
        frontmatter_lines = frontmatter.split('\n')
        total_sp = None
        sp_done = ""
        jira_link = None

        for line in frontmatter_lines:
            if line.strip().startswith('Total-SP:'):
                value = line.split('Total-SP:', 1)[1].strip()
                total_sp = value if value else None
            elif line.strip().startswith('SP-done:'):
                value = line.split('SP-done:', 1)[1].strip()
                sp_done = value if value else ""
            elif line.strip().startswith('jira-link:'):
                jira_link = line.split('jira-link:', 1)[1].strip()

        # If we don't have jira-link, it's not a valid Jira story
        if not jira_link:
            return "Not a jira story"

        # If Total-SP doesn't exist or is empty, get it from the Jira API
        if not total_sp or total_sp.strip() == '""' or total_sp.strip() == "''":
            issue_key = get_issue_number_from_url(jira_link)
            if issue_key:
                jira_issue = get_jira_issue(issue_key)
                if jira_issue and hasattr(jira_issue, 'story_points'):
                    total_sp = jira_issue.story_points

        # Clean up the values (remove quotes if present)
        if total_sp:
            total_sp = total_sp.strip('"\'')

        if sp_done:
            sp_done = sp_done.strip('"\'')

        # TODO next
        # Calculate remainind SP, looks like this: 375: 2 376: 1 377: 1
        # calculate remaining SP: all nums in sp_done, subtract from total_sp
        # append to SP-done: currentSprint: remainingSP (even if 0)
        # save file
        # return ok and remaining SP

        return {
            "Total-SP": total_sp,
            "SP-done": sp_done,
            "jira-link": jira_link
        }

    except Exception as e:
        return f"Error processing file: {str(e)}"
