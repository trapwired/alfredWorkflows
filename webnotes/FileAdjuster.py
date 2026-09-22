import re
import os
from webnotes.utilities import get_issue_number_from_url, get_current_sprint
from webnotes.JiraInterface import get_jira_issue


def as_story_points(value):
    """Story points as an int, or None. Tolerates quotes, floats and the literal 'None'
    that older notes carry in Total-SP."""
    if value is None:
        return None
    text = str(value).strip().strip('"\'').strip()
    if text in ('', 'None', 'null'):
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def adjust_file(file_path, done_sp_in_sprint=None, return_remaining_sp=False, mark_closed=False):
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
        closed_in_sprint = ""

        for line in frontmatter_lines:
            if line.strip().startswith('Total-SP:'):
                value = line.split('Total-SP:', 1)[1].strip()
                total_sp = value if value else None
            elif line.strip().startswith('SP-done:'):
                value = line.split('SP-done:', 1)[1].strip()
                sp_done = value if value else ""
            elif line.strip().startswith('jira-link:'):
                jira_link = line.split('jira-link:', 1)[1].strip()
            elif line.strip().startswith('closedInSprint:'):
                closed_in_sprint = line.split('closedInSprint:', 1)[1].strip().strip('"\'')

        # If we don't have jira-link, it's not a valid Jira story
        if not jira_link:
            return "Not a jira story"

        # The estimate belongs to Jira; the note only holds a copy, and that copy goes stale
        # every time someone re-estimates. So ask Jira first and book against its answer —
        # asking afterwards is too late, the wrong number is already in SP-done by then.
        note_total_sp = as_story_points(total_sp)
        jira_total_sp = None
        issue_key = get_issue_number_from_url(jira_link)
        if issue_key:
            jira_issue = get_jira_issue(issue_key)
            jira_total_sp = as_story_points(getattr(jira_issue, 'story_points', None)) if jira_issue else None

        total_sp = jira_total_sp if jira_total_sp is not None else note_total_sp
        if total_sp is None:
            return f'Kein Total-SP in der Notiz und keines in Jira ({issue_key}) — nichts gebucht'

        # Keep the copy honest, otherwise the next run drifts again.
        refreshed_total_sp = total_sp if total_sp != note_total_sp else None
        if refreshed_total_sp is not None:
            print(f'Total-SP aus Jira nachgezogen: {note_total_sp} -> {total_sp}')

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

        if return_remaining_sp:
            return remaining_sp

        # append to SP-done: currentSprint: remainingSP (even if 0)
        current_sprint = get_current_sprint()
        if current_sprint in sp_done_dict.keys():
            remaining_sp += sp_done_dict[current_sprint]

        # 0 is a deliberate booking ("no progress this sprint"), only None means "book remaining"
        if done_sp_in_sprint is not None:
            remaining_sp = done_sp_in_sprint
        sp_done_dict[current_sprint] = remaining_sp

        new_sp_done = ', '.join(f'{k}: {sp_done_dict[k]}' for k in sorted(sp_done_dict, key=int))

        # closedInSprint records the sprint of the FIRST close; re-closing never overwrites it
        set_closed_in_sprint = mark_closed and not closed_in_sprint
        if set_closed_in_sprint:
            closed_in_sprint = str(current_sprint)
        closed_in_sprint_line = f'closedInSprint: "{closed_in_sprint}"' if closed_in_sprint else 'closedInSprint:'

        # Update the SP-done property in the file
        # Surround new_sp_done with double quotes
        new_sp_done_quoted = f'"{new_sp_done}"'
        # Replace the SP-done and closedInSprint properties in the frontmatter
        def replace_sp_done(match):
            frontmatter = match.group(1)
            lines = frontmatter.split('\n')
            has_closed_in_sprint = any(l.strip().startswith('closedInSprint:') for l in lines)
            new_lines = []
            for line in lines:
                if line.strip().startswith('SP-done:'):
                    new_lines.append(f'SP-done: {new_sp_done_quoted}')
                    if set_closed_in_sprint and not has_closed_in_sprint:
                        new_lines.append(closed_in_sprint_line)
                elif line.strip().startswith('closedInSprint:'):
                    new_lines.append(closed_in_sprint_line)
                elif line.strip().startswith('Total-SP:') and refreshed_total_sp is not None:
                    new_lines.append(f'Total-SP: "{refreshed_total_sp}"')
                else:
                    new_lines.append(line)
            return f"---\n{chr(10).join(new_lines)}\n---"
        new_content = re.sub(r'^---\s*\n(.*?)\n---', replace_sp_done, content, flags=re.DOTALL)
        # Write the updated content back to the file
        with open(file_path, 'w') as file:
            file.write(new_content)

        # save file
        # return ok and remaining SP
        closed_info = f', closedInSprint: {closed_in_sprint}' if set_closed_in_sprint else ''
        if done_sp_in_sprint is not None:
            return f'Added {done_sp_in_sprint} SP to current Sprint ({current_sprint}){closed_info}'
        else:
            return f'Added remaining SP ({sp_done_dict[current_sprint]}) to current Sprint ({current_sprint}){closed_info}'

    except Exception as e:
        return f"Error processing file: {str(e)}"
