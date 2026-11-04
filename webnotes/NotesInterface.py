import os
from pathlib import Path
from random import randint

from webnotes.paths import VaultPaths
from webnotes.utilities import *


class NotesInterface:

    def __init__(self, main_path: Path):
        self.paths = VaultPaths.from_config(Path(main_path) / 'config.ini')

    def get_full_path(self, filename: str):
        return os.path.join(self.paths.notes, filename)

    def is_jira(self, filename):
        return filename.strip().endswith(f'- Jira{FILE_EXTENSION}')

    def is_jira_sup(self, filename):
        return filename.strip().startswith('SUP')

    def is_jira_pr(self, filename):
        return filename.startswith('Pull request')

    def is_template(self, filename):
        if self.is_jira_sup(filename):
            return TEMPLATE.JIRA_SUP
        elif self.is_jira(filename):
            return TEMPLATE.JIRA
        elif self.is_jira_pr(filename):
            return TEMPLATE.JIRA_PR

        return TEMPLATE.NO_TEMPLATE

    def get_prefixed_filename(self, filename):
        match self.is_template(filename):
            case TEMPLATE.JIRA:
                return os.path.join(self.paths.jira_folder_name, filename)
            case TEMPLATE.JIRA_SUP:
                return os.path.join(self.paths.jira_sup_folder_name, filename)
            case TEMPLATE.JIRA_PR:
                return os.path.join(self.paths.jira_pr_folder_name, filename)
            case _:
                return filename

    def find_note_by_link(self, url: str):
        for root, dirs, files in os.walk(self.paths.notes):
            dirs[:] = [d for d in dirs if d not in SKIPPED_DIRS]
            for name in files:
                if not name.endswith(FILE_EXTENSION):
                    continue
                path = Path(root) / name
                if frontmatter_link(path) == url:
                    return path.relative_to(self.paths.notes).as_posix()
        return None

    def create_new_file(self, filename, website_title, url):
        while os.path.exists(self.get_full_path(self.get_prefixed_filename(filename))):
            filename = website_title + str(randint(0, 100)) + FILE_EXTENSION

        match self.is_template(filename):
            case TEMPLATE.JIRA:
                return self.create_from_template(self.paths.jira_folder_name, self.paths.jira_template,
                                                 filename, jira_template_values(url))
            case TEMPLATE.JIRA_SUP:
                return self.create_from_template(self.paths.jira_sup_folder_name, self.paths.jira_sup_template,
                                                 filename, jira_sup_template_values(url))
            case TEMPLATE.JIRA_PR:
                issue_url = get_jira_issue_link_from_pr_title(filename)
                return self.create_from_template(self.paths.jira_pr_folder_name, self.paths.jira_pr_template,
                                                 filename, jira_pr_template_values(url, issue_url))
            case _:
                with open(self.get_full_path(filename), 'w', encoding='utf-8') as file:
                    file.write(get_header_with_link(url))
                return filename

    def create_from_template(self, folder_name, template_name, filename, values):
        relative_filename = os.path.join(folder_name, filename)
        content = self.paths.template(template_name).read_text(encoding='utf-8')
        for placeholder, value in values.items():
            if value:
                content = content.replace(placeholder, value)
        Path(self.get_full_path(relative_filename)).write_text(content, encoding='utf-8')
        return relative_filename

    def get_or_create_file(self, url: str, website_title: str, resolve_issue_from_clipboard: bool = False):
        url, website_title = handle_special_jira_cases(url, website_title, resolve_issue_from_clipboard)
        url = url.split('?')[0]

        existing = self.find_note_by_link(url)
        if existing:
            return existing

        filename = normalize_jira_filename(url, get_filename(website_title))
        return self.create_new_file(filename, website_title, url)
