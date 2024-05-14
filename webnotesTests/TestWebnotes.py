import os
import shutil
import unittest
from unittest.mock import patch, mock_open
import webnotes


def setup_index(index):
    webnotes.main.write_index(index)


def setup_file(filename, path='temp', content=''):
    full_filename = os.path.join(path, filename)
    with open(full_filename, 'w') as file:
        file.write(content)


class TestWebnotes(unittest.TestCase):
    def setUp(self):
        jira_template_name = 'Jira Template.md'
        # set global variables
        webnotes.main.INDEX_PATH = ''
        webnotes.main.PATH = 'temp'
        webnotes.main.JIRA_PATH = os.path.join('temp', jira_template_name)
        webnotes.main.JIRA_FOLDER_NAME = 'jira'
        # index setup
        if os.path.exists('index.txt'):
            os.remove('index.txt')
        webnotes.main.get_index_file('r').close()
        # temp directory
        if os.path.exists('temp'):
            shutil.rmtree('temp')
        os.mkdir('temp')
        os.mkdir(os.path.join('temp', 'jira'))
        # templates
        setup_file(jira_template_name, content='')

    def tearDown(self):
        # reset index file
        os.remove('index.txt')
        # empty temp folder
        shutil.rmtree('temp')

    def test_getOrCreateFile_newIndex_FileCreatedIndexIsUpdated(self):
        website = 'www.website.com'
        title = 'Website Title'
        filename = title + '.md'
        ref_index = {website: filename}

        result = webnotes.main.get_or_create_file(website, title)

        self.assertEqual(result, filename)
        self.assertEqual(ref_index, webnotes.main.get_index())
        self.assertTrue(os.path.exists(os.path.join('temp', filename)))

    def test_getOrCreateFile_newIndex_FileOutOfTemplateCreateIndexIsUpdated(self):
        website = 'www.website.com'
        title = 'Website - Jira'
        filename = os.path.join('jira', title + '.md')
        ref_index = {website: filename}

        result = webnotes.main.get_or_create_file(website, title)

        self.assertEqual(result, filename)
        self.assertEqual(ref_index, webnotes.main.get_index())
        self.assertTrue(os.path.exists(os.path.join('temp', filename)))

    def test_getOrCreateFile_existingIndex_FilenameIsReturned(self):
        website = 'www.website.com'
        title = 'Website Title'
        filename = title + '.md'
        ref_index = {website: filename}
        setup_index({website: filename})
        setup_file(filename)

        result = webnotes.main.get_or_create_file(website, title)

        self.assertEqual(result, filename)
        self.assertEqual(ref_index, webnotes.main.get_index())

    def test_getOrCreateFile_existingIndexJiraFile_FilenameIsReturned(self):
        website = 'www.website.com'
        title = 'OPA-42 Website Title - Jira'
        filename = os.path.join('jira', title + '.md')
        ref_index = {website: filename}
        setup_index({website: filename})
        setup_file(filename)

        result = webnotes.main.get_or_create_file(website, title)

        self.assertEqual(result, filename)
        self.assertEqual(ref_index, webnotes.main.get_index())

    def test_getOrCreateFile_fileRenamed_FilenameIsReturnedIndexUpdated(self):
        website = 'www.website.com'
        old_title = 'Website Title'
        new_title = 'Website Title New'
        old_filename = old_title + '.md'
        new_filename = new_title + '.md'
        ref_index = {website: new_filename}
        setup_index({website: old_filename})
        setup_file(old_filename)

        result = webnotes.main.get_or_create_file(website, new_title)

        self.assertEqual(result, new_filename)
        self.assertEqual(ref_index, webnotes.main.get_index())
        self.assertTrue(os.path.exists(os.path.join('temp', new_filename)))

    def test_getOrCreateFile_fileMoved_FilenameIsReturnedIndexUpdated(self):
        website = 'www.website.com'
        title = 'Website Title'
        filename = title + '.md'
        new_filename = os.path.join('temp2', filename)
        new_path = os.path.join('temp', 'temp2')
        os.mkdir(new_path)
        ref_index = {website: new_filename}
        setup_index({website: filename})
        setup_file(filename, new_path)

        result = webnotes.main.get_or_create_file(website, title)

        self.assertEqual(result, new_filename)
        self.assertEqual(ref_index, webnotes.main.get_index())
        self.assertTrue(os.path.exists(os.path.join('temp', new_filename)))

    @patch('webnotes.main.randint')
    def test_getOrCreateFile_duplicateFilename_RandomFilenameIsReturnedIndexUpdated(self, mock_randint):
        mock_randint.return_value = 42
        website = 'www.website.com'
        title = 'Website Title'
        filename = title + '42.md'
        setup_file(title + '.md')
        ref_index = {website: filename}

        result = webnotes.main.get_or_create_file(website, title)

        self.assertEqual(result, filename)
        self.assertEqual(ref_index, webnotes.main.get_index())
        self.assertTrue(os.path.exists(os.path.join('temp', filename)))

    def test_getOrCreateFile_jiraFileRenamed_FilenameIsReturnedIndexUpdated(self):
        website = 'www.website.com'
        old_title = 'OPA-42 Website - Jira'
        old_filename = os.path.join('jira', old_title + '.md')
        new_title = 'OPA-42 Website 2 - Jira'
        new_filename = os.path.join('jira', new_title + '.md')

        ref_index = {website: new_filename}
        setup_index({website: old_filename})
        setup_file(old_filename)

        result = webnotes.main.get_or_create_file(website, new_title)

        self.assertEqual(result, new_filename)
        self.assertEqual(ref_index, webnotes.main.get_index())
        self.assertTrue(os.path.exists(os.path.join('temp', new_filename)))

    def test_getOrCreateFile_FileDeleted_FileOutOfTemplateCreateIndexIsUpdated(self):
        website = 'www.website.com'
        title = 'Website - Jira'
        filename = os.path.join('jira', title + '.md')
        ref_index = {website: filename}
        setup_index({website: filename})

        result = webnotes.main.get_or_create_file(website, title)

        self.assertEqual(result, filename)
        self.assertEqual(ref_index, webnotes.main.get_index())
        self.assertTrue(os.path.exists(os.path.join('temp', filename)))

    # jira renamed and moved
    def test_getOrCreateFile_jiraTitleRenamedAndMoved_FilenameIsReturnedIndexUpdated(self):
        website = 'www.website.com'
        old_title = 'OPA-42 Website - Jira'
        old_filename = old_title + '.md'
        new_title = 'OPA-42 Website 2 - Jira'
        new_filename = new_title + '.md'

        ref_index = {website: new_filename}
        setup_index({website: old_filename})
        setup_file(old_filename)

        result = webnotes.main.get_or_create_file(website, new_title)

        self.assertEqual(result, new_filename)
        self.assertEqual(ref_index, webnotes.main.get_index())
        self.assertTrue(os.path.exists(os.path.join('temp', new_filename)))

    # jira renamed and moved
    def test_getOrCreateFile_jiraFileRenamedAndMoved_FilenameIsReturnedIndexUpdated(self):
        website = 'www.website.com'
        old_title = 'OPA-42 Website - Jira'
        old_filename = old_title + '.md'
        renamed_title = 'OPA-42 Website 345 - Jira'
        renamed_filename = renamed_title + '.md'
        new_title = 'OPA-42 Website 2 - Jira'
        new_filename = new_title + '.md'

        ref_index = {website: new_filename}
        setup_index({website: old_filename})
        setup_file(renamed_filename)

        result = webnotes.main.get_or_create_file(website, new_title)

        self.assertEqual(result, new_filename)
        self.assertEqual(ref_index, webnotes.main.get_index())
        self.assertTrue(os.path.exists(os.path.join('temp', new_filename)))

    def test_getOrCreateFile_jiraFileRenamedAndMoved2_FilenameIsReturnedIndexUpdated(self):
        website = 'www.website.com'
        old_title = 'OPA-42 Website - Jira'
        old_filename = old_title + '.md'
        renamed_title = 'OPA-42 Website 345 - Jira'
        renamed_filename = os.path.join('jira', 'jirainside', renamed_title + '.md')
        new_title = 'OPA-42 Website 2 - Jira'
        new_filename = os.path.join('jira', 'jirainside', new_title + '.md')

        ref_index = {website: new_filename}
        setup_index({website: old_filename})
        os.mkdir(os.path.join('temp', 'jira', 'jirainside'))
        setup_file(renamed_filename)

        result = webnotes.main.get_or_create_file(website, new_title)

        self.assertEqual(result, new_filename)
        self.assertEqual(ref_index, webnotes.main.get_index())
        self.assertTrue(os.path.exists(os.path.join('temp', new_filename)))

