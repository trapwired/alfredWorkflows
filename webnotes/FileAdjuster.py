import re
import os
from webnotes.utilities import get_issue_number_from_url, get_current_sprint
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
                    print('Total-SP not found in file, fetched from Jira API:', total_sp)

        # Clean up the values (remove quotes if present)
        if total_sp:
            total_sp = int(total_sp.strip('"\''))

        if sp_done:
            sp_done = sp_done.strip('"\'')

        # Calculate remainind SP, looks like this: 375: 2 376: 1 377: 1
        sp_done_dict = {}
        if sp_done:
            pairs = [p.strip() for p in sp_done.split(',') if p.strip()]
            for pair in pairs:
                if ':' in pair:
                    sprint, points = pair.split(':', 1)
                    try:
                        sprint_num = int(sprint.strip())
                        points_num = int(points.strip())
                        sp_done_dict[sprint_num] = points_num
                    except ValueError:
                        continue  # skip malformed entries

        # Sum up the story points done
        total_sp_done = sum(sp_done_dict.values())
        # calculate remaining SP: all nums in sp_done, subtract from total_sp
        remaining_sp = total_sp - total_sp_done
        # append to SP-done: currentSprint: remainingSP (even if 0)
        current_sprint = get_current_sprint()
        if current_sprint in sp_done_dict.keys():
            remaining_sp += sp_done_dict[current_sprint]
        sp_done_dict[current_sprint] = remaining_sp

        new_sp_done = ', '.join(f'{k}:{sp_done_dict[k]}' for k in sorted(sp_done_dict, key=int))

        # Update the SP-done property in the file
        # Surround new_sp_done with double quotes
        new_sp_done_quoted = f'"{new_sp_done}"'
        # Replace the SP-done property in the frontmatter
        def replace_sp_done(match):
            frontmatter = match.group(1)
            lines = frontmatter.split('\n')
            new_lines = []
            for line in lines:
                if line.strip().startswith('SP-done:'):
                    new_lines.append(f'SP-done: {new_sp_done_quoted}')
                else:
                    new_lines.append(line)
            return f"---\n{chr(10).join(new_lines)}\n---"
        new_content = re.sub(r'^---\s*\n(.*?)\n---', replace_sp_done, content, flags=re.DOTALL)
        # Write the updated content back to the file
        with open(file_path, 'w') as file:
            file.write(new_content)

        # save file
        # return ok and remaining SP

        return f'Added remaining SP ({sp_done_dict[current_sprint]}) to current Sprint ({current_sprint})'

    except Exception as e:
        return f"Error processing file: {str(e)}"
