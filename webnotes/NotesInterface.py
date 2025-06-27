import configparser
import os.path
from random import randint
import shutil

from webnotes.utilities import *


class NotesInterface:

    def __init__(self, main_path: str):
        config = configparser.RawConfigParser()
        config_path = os.path.join(main_path[:-9], 'config.ini')
        config.read(config_path, encoding='utf8')

        try:
            self._path: str = config.get('OPTIONS', 'path')

            self._jira_path: str = config.get('OPTIONS', 'jira_template_path')
            self._jira_folder_name: str = config.get('OPTIONS', 'jira_folder_name')
            self._jira_sup_path: str = config.get('OPTIONS', 'jira_sup_template_path')
            self._jira_sup_folder_name: str = config.get('OPTIONS', 'jira_sup_folder_name')
            self._jira_pr_path: str = config.get('OPTIONS', 'jira_pr_template_path')
            self._jira_pr_folder_name: str = config.get('OPTIONS', 'jira_pr_folder_name')
            self._index_path: str = config.get('OPTIONS', 'index_path')
        except Exception as e:
            print(e)

    def get_index_file(self, option: str):
        index_path = self._index_path
        if index_path == 'SAMPLE/PATH':
            index_path = self._path
        index_filename = os.path.join(index_path, 'index.txt')
        if not os.path.exists(index_filename):
            index_file = open(index_filename, "w", encoding='utf-8')
            index_file.close()
        index_file = open(index_filename, option, encoding='utf-8')
        return index_file

    def get_index(self):
        index_file = self.get_index_file('r')
        result = parse_index(index_file)
        index_file.close()
        return result

    def write_index(self, index):
        index_file = self.get_index_file('w')
        for key, value in index.items():
            index_file.write(f'{key}{DELIMITER}{value}\n')
        index_file.close()

    def is_jira(self, filename):
        return (self._jira_path != 'SAMPLE/JIRA/TEMPLATE/PATH'
                and self._jira_folder_name != 'SAMPLE_JIRA_FOLDER_NAME'
                and filename.strip().endswith(f'- Jira{FILE_EXTENSION}'))

    def is_jira_sup(self, filename):
        return (self._jira_path != 'SAMPLE/JIRA/TEMPLATE/PATH'
                and self._jira_sup_folder_name != 'SAMPLE_JIRA_FOLDER_NAME'
                and filename.strip().startswith(f'SUP'))

    def is_jira_pr(self, filename):
        return (self._jira_path != 'SAMPLE/JIRA/PR/TEMPLATE/PATH'
                and self._jira_folder_name != 'SAMPLE_JIRA_PR_FOLDER_NAME'
                and filename.startswith('Pull request'))

    def is_template(self, filename):
        if self.is_jira_sup(filename):
            return TEMPLATE.JIRA_SUP
        elif self.is_jira(filename):
            return TEMPLATE.JIRA
        elif self.is_jira_pr(filename):
            return TEMPLATE.JIRA_PR

        return TEMPLATE.NO_TEMPLATE

    def create_new_file(self, filename, website_title, url):
        while os.path.exists(os.path.join(self._path, filename)):
            filename = website_title + str(randint(0, 100)) + FILE_EXTENSION

        template = self.is_template(filename)
        match template:
            case TEMPLATE.JIRA:
                return self.create_jira_template(filename, url)
            case TEMPLATE.JIRA_SUP:
                return self.create_jira_sup_template(filename, url)
            case TEMPLATE.JIRA_PR:
                return self.create_jira_pr_template(filename, url)
            case _:
                with open(os.path.join(self._path, filename), 'w') as file:
                    file.write(get_header_with_link(url))
                return filename

    def get_prefixed_filename(self, filename):
        template = self.is_template(filename)
        match template:
            case TEMPLATE.JIRA:
                return os.path.join(self._jira_folder_name, filename)
            case TEMPLATE.JIRA_SUP:
                return os.path.join(self._jira_sup_folder_name, filename)
            case TEMPLATE.JIRA_PR:
                return os.path.join(self._jira_pr_folder_name, filename)
            case _:
                return os.path.join(filename)

    def create_jira_pr_template(self, filename, url):
        filename = os.path.join(self._jira_pr_folder_name, filename)
        jira_folder_path = os.path.join(self._path, filename)
        shutil.copyfile(self._jira_pr_path, jira_folder_path)

        filename_fullpath = os.path.join(self._path, filename)
        with open(filename_fullpath, 'r') as file:
            filedata = file.read()

        issue_number = get_jira_issue_link_from_pr_title(filename)
        for key, value in jira_pr_template_values(url, issue_number).items():
            if value:
                filedata = filedata.replace(key, value)

        with open(filename_fullpath, 'w') as file:
            file.write(filedata)
        return filename

    def create_jira_template(self, filename, url):
        filename = os.path.join(self._jira_folder_name, filename)
        jira_folder_path = os.path.join(self._path, filename)
        shutil.copyfile(self._jira_path, jira_folder_path)

        filename_fullpath = os.path.join(self._path, filename)
        with open(filename_fullpath, 'r') as file:
            filedata = file.read()

        for key, value in jira_template_values(url).items():
            filedata = filedata.replace(key, value)

        with open(filename_fullpath, 'w') as file:
            file.write(filedata)
        return filename

    def create_jira_sup_template(self, filename, url):
        filename = os.path.join(self._jira_sup_folder_name, filename)
        jira_folder_path = os.path.join(self._path, filename)
        shutil.copyfile(self._jira_sup_path, jira_folder_path)

        filename_fullpath = os.path.join(self._path, filename)
        with open(filename_fullpath, 'r') as file:
            filedata = file.read()

        for key, value in jira_template_values(url).items():
            filedata = filedata.replace(key, value)

        with open(filename_fullpath, 'w') as file:
            file.write(filedata)
        return filename

    def get_or_create_file(self, url: str, website_title: str):
        index = self.get_index()

        url, website_title = handle_special_jira_cases(url, website_title)
        url = url.split('?')[0]
        filename = get_filename(website_title)

        if url not in index.keys():
            # url not yet indexed, create new file
            filename = self.create_new_file(filename, website_title, url)

        else:
            # url indexed
            prefixed_filename = self.get_prefixed_filename(filename)
            full_file_path = os.path.join(self._path, prefixed_filename)

            if os.path.exists(full_file_path):
                # Happy Flow, file found
                filename = prefixed_filename

            else:
                # file was either renamed, moved or deleted
                old_file_path = os.path.join(self._path, index[url])
                file_found = find([index[url], filename], self._path)
                if os.path.exists(old_file_path):
                    # file was renamed, but stayed at original location
                    head, _ = os.path.split(old_file_path)
                    new_path = os.path.join(head, filename)
                    os.rename(old_file_path, new_path)
                    filename = Path(new_path).relative_to(self._path).as_posix()

                elif file_found:
                    # file was moved, update location in index
                    filename = file_found

                else:
                    # file was moved and renamed or deleted

                    # maybe we can find the file cause its jira
                    issue_number = get_issue_number(filename)
                    found_jira_filename = find_jira(issue_number, self._path, filename)
                    if found_jira_filename:
                        # rename jira issue at its current location
                        existing_full_path = os.path.join(self._path, found_jira_filename)
                        head, tail = os.path.split(existing_full_path)
                        new_full_path = os.path.join(head, filename)
                        os.rename(existing_full_path, new_full_path)
                        filename = Path(new_full_path).relative_to(self._path).as_posix()

                    else:
                        # file must have been deleted, create new one
                        filename = self.create_new_file(filename, website_title, url)

        index[url] = filename
        self.write_index(index)
        return filename
