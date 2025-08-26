import datetime
import os
import subprocess
import sys
from pathlib import Path

# Add the directory containing the webnotes package to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from webnotes import JiraInterface
from webnotes import utilities


def get_title(day: str = None) -> str:
    today = datetime.date.today()
    if not day:
        days = [1, 3]
    else:
        if day.upper() == "DI":
            days = [1]  # Tuesday
        elif day.upper() == "DO":
            days = [3]

    next_day = today
    while next_day.weekday() not in days:
        next_day += datetime.timedelta(days=1)
    if next_day.weekday() == 1:
        day_name = "Di"
    else:
        day_name = "DO"

    # Format the date as "Di 23.4.2025"
    date_str = f"{day_name.title()}. {next_day.day}.{next_day.month}.{next_day.year}"

    return f"Programm Refinement, {date_str}"


def make_clickable_bullet_list(urls_and_titles, title="The Bullet List"):
    # Generate list items, with special handling for the last item
    items = []
    for i, (url, item_title) in enumerate(urls_and_titles):
        if i == len(urls_and_titles) - 1:  # Last item
            items.append(f'<li><a href="{url}" target="_blank">{item_title}</a> (wenn Zeit)</li>')
        else:
            items.append(f'<li><a href="{url}" target="_blank">{item_title}</a></li>')

    # Prepend a bold title to the bullet list
    bold_title = f"<strong>{title}</strong>"
    return f"{bold_title}\n<ul>\n{''.join(items)}\n</ul>"


def copy_as_html_to_clipboard(html_text):
    process = subprocess.Popen(
        ['textutil', '-stdin', '-stdout', '-format', 'html', '-convert', 'rtf', '-encoding', 'ASCII'],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    rtf_data, _ = process.communicate(input=html_text.encode())
    pb_process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
    pb_process.communicate(input=rtf_data)


def get_issue_numbers(number_of_elements):
    sprints = JiraInterface.get_all_open_sprints()
    sprints = [s for s in sprints if 'PHX' in s.name]
    sprints = sorted(sprints, key=lambda s: s.name)
    issue_numbers = []
    cur_sprint_index = 0
    while len(issue_numbers) < number_of_elements:
        sprint = sprints[cur_sprint_index]
        filter_query = f'Sprint = {sprint.id} AND status IN (Open, "To be Discussed") ORDER BY RANK ASC'
        sprint_stories = JiraInterface.get_story_keys_from_backlog(filter_query)
        issue_numbers.extend(sprint_stories)
        cur_sprint_index += 1

    return issue_numbers[:number_of_elements]


if __name__ == '__main__':
    main_path = Path(sys.argv[0])

    number_of_issues = 3
    day = None
    if len(sys.argv) > 1:
        number_of_issues = int(sys.argv[1])
    if len(sys.argv) > 2:
        day = sys.argv[2]

    issue_numbers = get_issue_numbers(number_of_issues)

    urls_and_titles = []
    for issue_number in issue_numbers:
        url, title = utilities.get_jira_url_and_title(issue_number)
        urls_and_titles.append((url, title))

    title = get_title(day)
    bullet_list = make_clickable_bullet_list(urls_and_titles, title)

    copy_as_html_to_clipboard(bullet_list)

    print(f'Copied: {title}', end='')
