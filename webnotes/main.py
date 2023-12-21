import configparser
import os.path
from random import randint
import sys
from pathlib import Path

PATH = 'SAMPLE/PATH'
FILE_EXTENSION = '.md'
DELIMITER = '漢'


def replace_multiple(input_str: str, characters: str, replace_with: str):
    result = input_str
    for char in characters:
        result = result.replace(char, replace_with)
    return result


def get_filename(name: str):
    filename = replace_multiple(name, '/[]', ' ')
    filename += FILE_EXTENSION
    return filename


def parse_index(index_file):
    result_dict = dict()
    for line in index_file.readlines():
        line_split = line.split(DELIMITER)
        if len(line_split) > 1:
            result_dict[line_split[0]] = line_split[1].rstrip()
    return result_dict


def get_index_file(option: str):
    index_filename = os.path.join(PATH, 'index.txt')
    if not os.path.exists(index_filename):
        index_file = open(index_filename, "w")
        index_file.close()
    index_file = open(index_filename, option)
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
        for name in names:
            if name in files:
                new_path = os.path.join(root, name)
                return Path(new_path).relative_to(path).as_posix()


def get_or_create_file(url: str, website_title: str):
    filename = get_filename(website_title)
    filename_fullpath = os.path.join(PATH, filename)
    index = get_index()

    if url not in index.keys():
        while os.path.exists(filename_fullpath):
            filename = website_title + str(randint(0, 100)) + FILE_EXTENSION
            filename_fullpath = os.path.join(PATH, filename)
        file = open(filename_fullpath, 'w')
        file.close()

    else:
        if not os.path.exists(filename_fullpath):
            # file was either renamed, moved or deleted
            old_file_path = os.path.join(PATH, index[url])
            if os.path.exists(filename_fullpath):
                # file was renamed
                os.rename(old_file_path, filename_fullpath)
            else:
                # file was removed or deleted
                filenames = [index[url], filename]
                filename = find(filenames, PATH)
                if filename is None:
                    print("file was deleted!")

    index[url] = filename
    write_index(index)
    correct_filename = index[url]
    # correct_fullpath = os.path.join(PATH, correct_filename)
    return correct_filename


def init_config():
    global PATH
    config = configparser.RawConfigParser()
    config.read('config.ini', encoding='utf8')
    PATH = config.get('OPTIONS', 'path')


if __name__ == '__main__':
    init_config()
    # get url and title from command-line arguments
    url_arg = sys.argv[1]
    website_title_arg = ' '.join(sys.argv[2:])

    # get filename, create file if it does not exist
    file_to_open = get_or_create_file(url_arg, website_title_arg)

    # export to alfred, opens obsidian
    print(file_to_open, end='')
