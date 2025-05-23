import configparser
import os.path
from enum import Enum
from random import randint
import sys
from pathlib import Path
import shutil

INDEX_PATH = 'SAMPLE/PATH'
PATH = 'SAMPLE/PATH'

JIRA_PATH = 'SAMPLE/JIRA/TEMPLATE/PATH'
JIRA_SUP_PATH = 'SAMPLE/JIRA/TEMPLATE/PATH'
JIRA_FOLDER_NAME = 'SAMPLE_JIRA_FOLDER_NAME'
JIRA_SUP_FOLDER_NAME = 'SAMPLE_JIRA_FOLDER_NAME'
JIRA_PR_PATH = 'SAMPLE/JIRA/PR/TEMPLATE/PATH'
JIRA_PR_FOLDER_NAME = 'SAMPLE_JIRA_PR_FOLDER_NAME'

FILE_EXTENSION = '.md'
DELIMITER = '漢'

OPTIONS = ['OPA', 'SUP']


class TEMPLATE(Enum):
    NO_TEMPLATE = 0
    JIRA = 1
    JIRA_PR = 2
    JIRA_SUP = 3


def jira_template_values(url):
    return {
        '漢JIRA_LINK漢': url
    }


def jira_pr_template_values(url, issue_url):
    return {
        '漢JIRA_PR_LINK漢': url,
        '漢JIRA_LINK漢': issue_url
    }


def get_header_with_link(url):
    return f'---\nlink: {url}\n---'


def replace_multiple(input_str: str, characters: str, replace_with: str):
    result = input_str
    for char in characters:
        result = result.replace(char, replace_with)
    return result


def get_filename(name: str):
    filename = replace_multiple(name, '/[]&"', ' ')
    filename = filename.strip()
    filename += FILE_EXTENSION
    return filename


def parse_index(index_file):
    result_dict = dict()
    for line in index_file.readlines():
        line_split = line.split(DELIMITER)
        if len(line_split) > 1:
            link = line_split[0].split('?')[0]
            title = line_split[1].rstrip()
            if title == 'None':
                continue
            if title.endswith(f'{FILE_EXTENSION}{FILE_EXTENSION}'):
                title = title.split(f'{FILE_EXTENSION}')[0] + f'{FILE_EXTENSION}'
            result_dict[link] = title
    return result_dict


def get_index_file(option: str):
    index_path = INDEX_PATH
    if index_path == 'SAMPLE/PATH':
        index_path = PATH
    index_filename = os.path.join(index_path, 'index.txt')
    if not os.path.exists(index_filename):
        index_file = open(index_filename, "w", encoding='utf-8')
        index_file.close()
    index_file = open(index_filename, option, encoding='utf-8')
    return index_file


def get_index():
    index_file = get_index_file('r')
    result = parse_index(index_file)
    index_file.close()
    return result


def write_index(index):
    index_file = get_index_file('w')
    for key, value in index.items():
        index_file.write(f'{key}{DELIMITER}{value}\n')
    index_file.close()


def find(names, path):
    for root, dirs, files in os.walk(path):
        files = [x.rstrip() for x in files]
        for name in names:
            name = name.rstrip()
            if name in files:
                new_path = os.path.join(root, name)
                return Path(new_path).relative_to(path).as_posix()


def is_jira(filename):
    return (JIRA_PATH != 'SAMPLE/JIRA/TEMPLATE/PATH'
            and JIRA_FOLDER_NAME != 'SAMPLE_JIRA_FOLDER_NAME'
            and filename.strip().endswith(f'- Jira{FILE_EXTENSION}'))

def is_jira_sup(filename):
    return (JIRA_PATH != 'SAMPLE/JIRA/TEMPLATE/PATH'
            and JIRA_SUP_FOLDER_NAME != 'SAMPLE_JIRA_FOLDER_NAME'
            and filename.strip().startswith(f'SUP'))


def is_jira_pr(filename):
    return (JIRA_PATH != 'SAMPLE/JIRA/PR/TEMPLATE/PATH'
            and JIRA_FOLDER_NAME != 'SAMPLE_JIRA_PR_FOLDER_NAME'
            and filename.startswith('Pull request'))


def is_template(filename):
    if is_jira_sup(filename):
        return TEMPLATE.JIRA_SUP
    elif is_jira(filename):
        return TEMPLATE.JIRA
    elif is_jira_pr(filename):
        return TEMPLATE.JIRA_PR

    return TEMPLATE.NO_TEMPLATE


def get_issue_number(filename):
    potential_issue_number = filename.split()[0]
    if any([x in potential_issue_number for x in OPTIONS]):
        return potential_issue_number
    return None


def find_jira(issue_number, path, filename):
    if not issue_number:
        return
    for root, dirs, files in os.walk(path):
        files = [x.rstrip() for x in files]
        for file in files:
            if file.startswith(issue_number):
                new_path = os.path.join(root, file)
                return Path(new_path).relative_to(path).as_posix()


def create_new_file(filename, website_title, url):
    while os.path.exists(os.path.join(PATH, filename)):
        filename = website_title + str(randint(0, 100)) + FILE_EXTENSION

    template = is_template(filename)
    match template:
        case TEMPLATE.JIRA:
            return create_jira_template(filename, url)
        case TEMPLATE.JIRA_SUP:
            return create_jira_sup_template(filename, url)
        case TEMPLATE.JIRA_PR:
            return create_jira_pr_template(filename, url)
        case _:
            with open(os.path.join(PATH, filename), 'w') as file:
                file.write(get_header_with_link(url))
            return filename


def get_prefixed_filename(filename):
    template = is_template(filename)
    match template:
        case TEMPLATE.JIRA:
            return os.path.join(JIRA_FOLDER_NAME, filename)
        case TEMPLATE.JIRA_SUP:
            return os.path.join(JIRA_FOLDER_NAME, filename)
        case TEMPLATE.JIRA_PR:
            return os.path.join(JIRA_PR_FOLDER_NAME, filename)
        case _:
            return os.path.join(filename)


def create_jira_pr_template(filename, url):
    filename = os.path.join(JIRA_PR_FOLDER_NAME, filename)
    jira_folder_path = os.path.join(PATH, filename)
    shutil.copyfile(JIRA_PR_PATH, jira_folder_path)

    filename_fullpath = os.path.join(PATH, filename)
    with open(filename_fullpath, 'r') as file:
        filedata = file.read()

    issue_number = get_jira_issue_link_from_pr_title(filename)
    for key, value in jira_pr_template_values(url, issue_number).items():
        if value:
            filedata = filedata.replace(key, value)

    with open(filename_fullpath, 'w') as file:
        file.write(filedata)
    return filename


def create_jira_template(filename, url):
    filename = os.path.join(JIRA_FOLDER_NAME, filename)
    jira_folder_path = os.path.join(PATH, filename)
    shutil.copyfile(JIRA_PATH, jira_folder_path)

    filename_fullpath = os.path.join(PATH, filename)
    with open(filename_fullpath, 'r') as file:
        filedata = file.read()

    for key, value in jira_template_values(url).items():
        filedata = filedata.replace(key, value)

    with open(filename_fullpath, 'w') as file:
        file.write(filedata)
    return filename

def create_jira_sup_template(filename, url):
    filename = os.path.join(JIRA_SUP_FOLDER_NAME, filename)
    jira_folder_path = os.path.join(PATH, filename)
    shutil.copyfile(JIRA_SUP_PATH, jira_folder_path)

    filename_fullpath = os.path.join(PATH, filename)
    with open(filename_fullpath, 'r') as file:
        filedata = file.read()

    for key, value in jira_template_values(url).items():
        filedata = filedata.replace(key, value)

    with open(filename_fullpath, 'w') as file:
        file.write(filedata)
    return filename


def get_jira_issue_link_from_pr_title(filename):
    if 'noissue' in filename.lower():
        return '#NOISSUE-PR'

    for option in OPTIONS:
        split_1 = filename.split(f'{option}-')
        if len(split_1) == 1:
            # we are not in this option
            continue
        split_2 = split_1[1].split(' ')
        number = split_2[0]
        return f'https://jiradg.atlassian.net/browse/{option}-{number}'


def init_config(main_path: str):
    global PATH, JIRA_PATH, JIRA_FOLDER_NAME, JIRA_PR_PATH, JIRA_PR_FOLDER_NAME, INDEX_PATH, JIRA_SUP_FOLDER_NAME, JIRA_SUP_PATH
    config = configparser.RawConfigParser()
    config_path = os.path.join(main_path[:-7], 'config.ini')
    config.read(config_path, encoding='utf8')
    PATH = config.get('OPTIONS', 'path')
    try:
        JIRA_PATH = config.get('OPTIONS', 'jira_template_path')
        JIRA_FOLDER_NAME = config.get('OPTIONS', 'jira_folder_name')
        JIRA_SUP_PATH = config.get('OPTIONS', 'jira_sup_template_path')
        JIRA_SUP_FOLDER_NAME = config.get('OPTIONS', 'jira_sup_folder_name')
        JIRA_PR_PATH = config.get('OPTIONS', 'jira_pr_template_path')
        JIRA_PR_FOLDER_NAME = config.get('OPTIONS', 'jira_pr_folder_name')
        INDEX_PATH = config.get('OPTIONS', 'index_path')
    except Exception:
        pass


def get_or_create_file(url: str, website_title: str):
    index = get_index()
    filename = get_filename(website_title)

    if url not in index.keys():
        # url not yet indexed, create new file
        filename = create_new_file(filename, website_title, url)

    else:
        # url indexed
        prefixed_filename = get_prefixed_filename(filename)
        full_file_path = os.path.join(PATH, prefixed_filename)

        if os.path.exists(full_file_path):
            # Happy Flow, file found
            filename = prefixed_filename

        else:
            # file was either renamed, moved or deleted
            old_file_path = os.path.join(PATH, index[url])
            file_found = find([index[url], filename], PATH)
            if os.path.exists(old_file_path):
                # file was renamed, but stayed at original location
                head, _ = os.path.split(old_file_path)
                new_path = os.path.join(head, filename)
                os.rename(old_file_path, new_path)
                filename = Path(new_path).relative_to(PATH).as_posix()

            elif file_found:
                # file was moved, update location in index
                filename = file_found

            else:
                # file was moved and renamed or deleted

                # maybe we can find the file cause its jira
                issue_number = get_issue_number(filename)
                found_jira_filename = find_jira(issue_number, PATH, filename)
                if found_jira_filename:
                    # rename jira issue at its current location
                    existing_full_path = os.path.join(PATH, found_jira_filename)
                    head, tail = os.path.split(existing_full_path)
                    new_full_path = os.path.join(head, filename)
                    os.rename(existing_full_path, new_full_path)
                    filename = Path(new_full_path).relative_to(PATH).as_posix()

                else:
                    # file must have been deleted, create new one
                    filename = create_new_file(filename, website_title, url)

    index[url] = filename
    write_index(index)
    return filename


if __name__ == '__main__':
    # get url and title from command-line arguments
    main_path = sys.argv[0]
    init_config(main_path)

    url_arg = sys.argv[1]
    website_title_arg = ' '.join(sys.argv[2:])

    url_arg = url_arg.split('?')[0]

    # get filename, create file if it does not exist
    file_to_open = get_or_create_file(url_arg, website_title_arg)

    # export to alfred, opens obsidian
    print(file_to_open, end='')
