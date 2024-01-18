import configparser
import os.path
from enum import Enum
from random import randint
import sys
from pathlib import Path
import shutil

PATH = 'SAMPLE/PATH'
JIRA_PATH = 'SAMPLE/JIRA/TEMPLATE/PATH'
JIRA_FOLDER_NAME = 'SAMPLE_JIRA_FOLDER_NAME'
FILE_EXTENSION = '.md'
DELIMITER = '漢'


class TEMPLATE(Enum):
    NO_TEMPLATE = 0
    JIRA = 1


def jira_template_values(url):
    return {
        '漢JIRA_LINK漢': url
    }


def replace_multiple(input_str: str, characters: str, replace_with: str):
    result = input_str
    for char in characters:
        result = result.replace(char, replace_with)
    return result


def get_filename(name: str):
    filename = replace_multiple(name, '/[]', ' ')
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
            if title.endswith('.md.md'):
                title = title.split('.md')[0] + '.md'
            result_dict[link] = title
    return result_dict


def get_index_file(option: str):
    index_filename = os.path.join(PATH, 'index.txt')
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


def get_fullpath(filename):
    return os.path.join(PATH, filename)


def is_jira(filename):
    return (JIRA_PATH != 'SAMPLE/JIRA/TEMPLATE/PATH'
            and JIRA_FOLDER_NAME != 'SAMPLE_JIRA_FOLDER_NAME'
            and filename.startswith('OPA-'))


def is_template(filename):
    if is_jira(filename):
        return TEMPLATE.JIRA
    return TEMPLATE.NO_TEMPLATE


def get_issue_number(filename):
    return filename.split()[0]


def find_jira(issue_number, path, filename):
    for root, dirs, files in os.walk(path):
        files = [x.rstrip() for x in files]
        for file in files:
            if file.startswith(issue_number):
                new_path = os.path.join(root, filename)
                return Path(new_path).relative_to(path).as_posix()


def get_or_create_file(url: str, website_title: str):
    filename = get_filename(website_title)
    filename_fullpath = get_fullpath(filename)
    index = get_index()

    if url not in index.keys():
        filename = create_new_file(filename, filename_fullpath, website_title, url)

    else:
        if not os.path.exists(filename_fullpath):
            # file was either renamed, moved or deleted
            old_file_path = os.path.join(PATH, index[url])
            if os.path.exists(filename_fullpath):
                # file was renamed
                os.rename(old_file_path, filename_fullpath)
            else:
                # file was moved or deleted
                filenames = [index[url], filename]
                found_filename = find_file(filename, filenames)
                filename = create_new_if_not_found(filename, filename_fullpath, found_filename, website_title, url)

    index[url] = filename
    write_index(index)
    correct_filename = index[url]
    return correct_filename


def find_file(filename, filenames):
    template = is_template(filename)
    match template:
        case TEMPLATE.JIRA:
            issue_number = get_issue_number(filename)
            found_filename = find_jira(issue_number, PATH, filename)
        case _:
            found_filename = find(filenames, PATH)
    return found_filename


def create_new_if_not_found(filename, filename_fullpath, found_filename, website_title, url):
    if found_filename is None:
        # file was deleted, create new one
        filename = create_new_file(filename, filename_fullpath, website_title, url)
    else:
        filename = found_filename
    return filename


def create_new_file(filename, filename_fullpath, website_title, url):
    while os.path.exists(filename_fullpath):
        filename = website_title + str(randint(0, 100)) + FILE_EXTENSION
        filename_fullpath = os.path.join(PATH, filename)

    template = is_template(filename)
    match template:
        case TEMPLATE.JIRA:
            return create_jira_template(filename, url)
        case _:
            file = open(filename_fullpath, 'w')
            file.close()
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


def init_config(main_path: str):
    global PATH, JIRA_PATH, JIRA_FOLDER_NAME
    config = configparser.RawConfigParser()
    config_path = os.path.join(main_path[:-7], 'config.ini')
    config.read(config_path, encoding='utf8')
    PATH = config.get('OPTIONS', 'path')
    try:
        JIRA_PATH = config.get('OPTIONS', 'jira_template_path')
        JIRA_FOLDER_NAME = config.get('OPTIONS', 'jira_folder_name')
    except Exception:
        pass


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
