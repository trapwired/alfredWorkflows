import os
import shutil
import unittest
from unittest.mock import patch

from webnotes import NotesInterface


def setup_file(filename, path='temp', content=''):
    full_filename = os.path.join(path, filename)
    with open(full_filename, 'w') as file:
        file.write(content)


class TestWebnotes(unittest.TestCase):
    def setUp(self):
        notes_interface = NotesInterface.NotesInterface('asdfasdfa')
        jira_template_name = 'Jira Template.md'
        # set global variables
        notes_interface._index_path = ''
        notes_interface._path = 'temp'
        notes_interface._jira_path = os.path.join('temp', jira_template_name)
        notes_interface._jira_folder_name = 'jira'
        notes_interface._jira_sup_path = os.path.join('temp', jira_template_name)
        notes_interface._jira_sup_folder_name = 'jira-sup'
        # index setup
        if os.path.exists('index.txt'):
            os.remove('index.txt')
        notes_interface.get_index_file('r').close()
        # temp directory
        if os.path.exists('temp'):
            shutil.rmtree('temp')
        os.mkdir('temp')
        os.mkdir(os.path.join('temp', 'jira'))
        os.mkdir(os.path.join('temp', 'jira-sup'))
        # templates
        setup_file(jira_template_name, content='')
        self.testee = notes_interface

    def tearDown(self):
        # reset index file
        os.remove('index.txt')
        # empty temp folder
        shutil.rmtree('temp')

    def setup_index(self, index):
        self.testee.write_index(index)

    def test_getOrCreateFile_newIndex_FileCreatedIndexIsUpdated(self):
        website = 'www.website.com'
        title = 'Website Title'
        filename = title + '.md'
        ref_index = {website: filename}

        result = self.testee.get_or_create_file(website, title)

        self.assertEqual(result, filename)
        self.assertEqual(ref_index, self.testee.get_index())
        self.assertTrue(os.path.exists(os.path.join('temp', filename)))

    def test_getOrCreateFile_newIndex_FileOutOfJiraTemplateCreateIndexIsUpdated(self):
        website = 'www.website.com'
        title = 'Website - Jira'
        filename = os.path.join('jira', title + '.md')
        ref_index = {website: filename}

        result = self.testee.get_or_create_file(website, title)

        self.assertEqual(result, filename)
        self.assertEqual(ref_index, self.testee.get_index())
        self.assertTrue(os.path.exists(os.path.join('temp', filename)))

    @patch('webnotes.utilities.get_url_title')
    def test_getOrCreateFile_newIndex_FileOutOfJiraTemplateMainBacklogLinkCreateIndexIsUpdated(self, mock_get_url_title):
        website = 'https://jiradg.atlassian.net/jira/random_part/backlog?issueLimit=100&selectedIssue=PROJ-123'
        expected_website = 'https://jiradg.atlassian.net/browse/PROJ-123'
        title = 'Phoenix - Backlog - Jira'
        expected_title = 'PROJ-123 Some random Story - Jira'
        mock_get_url_title.return_value = expected_title
        filename = os.path.join('jira', expected_title + '.md')
        ref_index = {expected_website: filename}

        result = self.testee.get_or_create_file(website, title)

        self.assertEqual(result, filename)
        self.assertEqual(ref_index, self.testee.get_index())
        self.assertTrue(os.path.exists(os.path.join('temp', filename)))

    def test_getOrCreateFile_newIndex_FileOutOfJiraSupTemplateCreateIndexIsUpdated(self):
        website = 'www.website.com'
        title = 'SUP Website - Jira'
        filename = os.path.join('jira-sup', title + '.md')
        ref_index = {website: filename}

        result = self.testee.get_or_create_file(website, title)

        self.assertEqual(result, filename)
        self.assertEqual(ref_index, self.testee.get_index())
        self.assertTrue(os.path.exists(os.path.join('temp', filename)))

    def test_getOrCreateFile_existingIndex_FilenameIsReturned(self):
        website = 'www.website.com'
        title = 'Website Title'
        filename = title + '.md'
        ref_index = {website: filename}
        self.setup_index({website: filename})
        setup_file(filename)

        result = self.testee.get_or_create_file(website, title)

        self.assertEqual(result, filename)
        self.assertEqual(ref_index, self.testee.get_index())

    def test_getOrCreateFile_existingIndexJiraFile_FilenameIsReturned(self):
        website = 'www.website.com'
        title = 'OPA-42 Website Title - Jira'
        filename = os.path.join('jira', title + '.md')
        ref_index = {website: filename}
        self.setup_index({website: filename})
        setup_file(filename)

        result = self.testee.get_or_create_file(website, title)

        self.assertEqual(result, filename)
        self.assertEqual(ref_index, self.testee.get_index())

    def test_getOrCreateFile_fileRenamed_FilenameIsReturnedIndexUpdated(self):
        website = 'www.website.com'
        old_title = 'Website Title'
        new_title = 'Website Title New'
        old_filename = old_title + '.md'
        new_filename = new_title + '.md'
        ref_index = {website: new_filename}
        self.setup_index({website: old_filename})
        setup_file(old_filename)

        result = self.testee.get_or_create_file(website, new_title)

        self.assertEqual(result, new_filename)
        self.assertEqual(ref_index, self.testee.get_index())
        self.assertTrue(os.path.exists(os.path.join('temp', new_filename)))

    def test_getOrCreateFile_fileMoved_FilenameIsReturnedIndexUpdated(self):
        website = 'www.website.com'
        title = 'Website Title'
        filename = title + '.md'
        new_filename = os.path.join('temp2', filename)
        new_path = os.path.join('temp', 'temp2')
        os.mkdir(new_path)
        ref_index = {website: new_filename}
        self.setup_index({website: filename})
        setup_file(filename, new_path)

        result = self.testee.get_or_create_file(website, title)

        self.assertEqual(result, new_filename)
        self.assertEqual(ref_index, self.testee.get_index())
        self.assertTrue(os.path.exists(os.path.join('temp', new_filename)))

    @patch('webnotes.NotesInterface.randint')
    def test_getOrCreateFile_duplicateFilename_RandomFilenameIsReturnedIndexUpdated(self, mock_randint):
        mock_randint.return_value = 42
        website = 'www.website.com'
        title = 'Website Title'
        filename = title + '42.md'
        setup_file(title + '.md')
        ref_index = {website: filename}

        result = self.testee.get_or_create_file(website, title)

        self.assertEqual(result, filename)
        self.assertEqual(ref_index, self.testee.get_index())
        self.assertTrue(os.path.exists(os.path.join('temp', filename)))

    def test_getOrCreateFile_jiraFileRenamed_FilenameIsReturnedIndexUpdated(self):
        website = 'www.website.com'
        old_title = 'OPA-42 Website - Jira'
        old_filename = os.path.join('jira', old_title + '.md')
        new_title = 'OPA-42 Website 2 - Jira'
        new_filename = os.path.join('jira', new_title + '.md')

        ref_index = {website: new_filename}
        self.setup_index({website: old_filename})
        setup_file(old_filename)

        result = self.testee.get_or_create_file(website, new_title)

        self.assertEqual(result, new_filename)
        self.assertEqual(ref_index, self.testee.get_index())
        self.assertTrue(os.path.exists(os.path.join('temp', new_filename)))

    def test_getOrCreateFile_FileDeleted_FileOutOfTemplateCreateIndexIsUpdated(self):
        website = 'www.website.com'
        title = 'Website - Jira'
        filename = os.path.join('jira', title + '.md')
        ref_index = {website: filename}
        self.setup_index({website: filename})

        result = self.testee.get_or_create_file(website, title)

        self.assertEqual(result, filename)
        self.assertEqual(ref_index, self.testee.get_index())
        self.assertTrue(os.path.exists(os.path.join('temp', filename)))

    # jira renamed and moved
    def test_getOrCreateFile_jiraTitleRenamedAndMoved_FilenameIsReturnedIndexUpdated(self):
        website = 'www.website.com'
        old_title = 'OPA-42 Website - Jira'
        old_filename = old_title + '.md'
        new_title = 'OPA-42 Website 2 - Jira'
        new_filename = new_title + '.md'

        ref_index = {website: new_filename}
        self.setup_index({website: old_filename})
        setup_file(old_filename)

        result = self.testee.get_or_create_file(website, new_title)

        self.assertEqual(result, new_filename)
        self.assertEqual(ref_index, self.testee.get_index())
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
        self.setup_index({website: old_filename})
        setup_file(renamed_filename)

        result = self.testee.get_or_create_file(website, new_title)

        self.assertEqual(result, new_filename)
        self.assertEqual(ref_index, self.testee.get_index())
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
        self.setup_index({website: old_filename})
        os.mkdir(os.path.join('temp', 'jira', 'jirainside'))
        setup_file(renamed_filename)

        result = self.testee.get_or_create_file(website, new_title)

        self.assertEqual(result, new_filename)
        self.assertEqual(ref_index, self.testee.get_index())
        self.assertTrue(os.path.exists(os.path.join('temp', new_filename)))

