import os
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from webnotes import NotesInterface

JIRA_TEMPLATE = '''---
tags:
  - Jira
link: 漢JIRA_LINK漢
SP-done:
closedInSprint:
Total-SP: 漢JIRA_STORY_POINTS漢
Initiative: 漢JIRA_INITIATIVE漢
---
# Story Beschreibung
'''

JIRA_SUP_TEMPLATE = '''---
tags:
  - jira-sup
link: 漢JIRA_LINK漢
---
# Problem
'''

JIRA_PR_TEMPLATE = '''---
tags:
  - Jira-PR
link: 漢JIRA_PR_LINK漢
story-link: 漢JIRA_LINK漢
---
# Status
'''


def note_with_link(url, body='# Body\n'):
    return f'---\ntags:\n  - Jira\nlink: {url}\n---\n{body}'


class TestWebnotes(unittest.TestCase):
    def setUp(self):
        temp_root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, temp_root)

        self.vault = temp_root / 'vault'
        self.notes = self.vault / 'Spaces' / 'Home' / 'DG'
        for folder in ('Jira', 'Jira-SUP', 'Jira-PRs'):
            (self.notes / folder).mkdir(parents=True)

        templates = self.vault / 'Templates'
        templates.mkdir()
        (templates / 'Jira Template.md').write_text(JIRA_TEMPLATE, encoding='utf-8')
        (templates / 'Jira Template SUP.md').write_text(JIRA_SUP_TEMPLATE, encoding='utf-8')
        (templates / 'Jira-PR Template.md').write_text(JIRA_PR_TEMPLATE, encoding='utf-8')

        config_dir = temp_root / 'config'
        config_dir.mkdir()
        (config_dir / 'config.ini').write_text(f'''[OPTIONS]
vault_root = {self.vault}
notes_dir = Spaces/Home/DG
templates_dir = Templates
jira_template = Jira Template.md
jira_sup_template = Jira Template SUP.md
jira_pr_template = Jira-PR Template.md
jira_folder_name = Jira
jira_sup_folder_name = Jira-SUP
jira_pr_folder_name = Jira-PRs
''', encoding='utf-8')

        self.testee = NotesInterface.NotesInterface(config_dir)

    def setup_note(self, relative_filename, content):
        path = self.notes / relative_filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        return path

    def read_note(self, relative_filename):
        return (self.notes / relative_filename).read_text(encoding='utf-8')

    def test_getOrCreateFile_unknownUrl_genericNoteWithLinkHeaderCreated(self):
        website = 'www.website.com'
        title = 'Website Title'
        filename = title + '.md'

        result = self.testee.get_or_create_file(website, title)

        self.assertEqual(result, filename)
        self.assertEqual(self.read_note(filename), '---\nlink: www.website.com\n---')
        self.assertFalse((self.vault / 'index.txt').exists())
        self.assertFalse((self.notes / 'index.txt').exists())

    @patch('webnotes.JiraInterface.get_jira_issue')
    def test_getOrCreateFile_unknownJiraUrl_noteFromJiraTemplateInJiraFolder(self, mock_get_jira_issue):
        mock_get_jira_issue.return_value = SimpleNamespace(story_points='5', parent_topic='ATK')
        website = 'https://jiradg.atlassian.net/browse/OPA-123'
        title = 'OPA-123  Some story - Jira'
        filename = os.path.join('Jira', title + '.md')

        result = self.testee.get_or_create_file(website, title)

        self.assertEqual(result, filename)
        content = self.read_note(filename)
        self.assertIn('link: https://jiradg.atlassian.net/browse/OPA-123\n', content)
        self.assertIn('Total-SP: "5"\n', content)
        self.assertIn('Initiative: "ATK"\n', content)
        self.assertNotIn('漢', content)

    @patch('webnotes.JiraInterface.get_jira_issue')
    @patch('webnotes.utilities.get_url_title')
    def test_getOrCreateFile_backlogUrlWithSelectedIssue_noteForBrowseUrlCreated(self, mock_get_url_title,
                                                                                mock_get_jira_issue):
        mock_get_url_title.return_value = '[OPA-123] Some random Story - Jira'
        mock_get_jira_issue.return_value = None
        website = 'https://jiradg.atlassian.net/jira/random_part/backlog?issueLimit=100&selectedIssue=OPA-123'
        title = 'Phoenix - Backlog - Jira'
        filename = os.path.join('Jira', 'OPA-123  Some random Story - Jira.md')

        result = self.testee.get_or_create_file(website, title)

        self.assertEqual(result, filename)
        self.assertIn('link: https://jiradg.atlassian.net/browse/OPA-123\n', self.read_note(filename))

    def test_getOrCreateFile_unknownSupUrl_noteFromSupTemplateInSupFolder(self):
        website = 'https://jiradg.atlassian.net/browse/SUP-77'
        title = 'SUP-77  Something broken - Jira'
        filename = os.path.join('Jira-SUP', title + '.md')

        result = self.testee.get_or_create_file(website, title)

        self.assertEqual(result, filename)
        content = self.read_note(filename)
        self.assertIn('  - jira-sup\n', content)
        self.assertIn('link: https://jiradg.atlassian.net/browse/SUP-77\n', content)
        self.assertNotIn('漢', content)

    def test_getOrCreateFile_unknownPrUrl_noteWithLinkAndStoryLinkInPrFolder(self):
        website = 'https://dev.azure.com/org/project/_git/repo/pullrequest/42'
        title = 'Pull request 42: OPA-123 Add feature'
        filename = os.path.join('Jira-PRs', title + '.md')

        result = self.testee.get_or_create_file(website, title)

        self.assertEqual(result, filename)
        content = self.read_note(filename)
        self.assertIn('link: https://dev.azure.com/org/project/_git/repo/pullrequest/42\n', content)
        self.assertIn('story-link: https://jiradg.atlassian.net/browse/OPA-123\n', content)
        self.assertNotIn('漢', content)

    def test_getOrCreateFile_githubPrTitle_noteInPrFolderWithoutHash(self):
        website = 'https://github.com/DigitecGalaxus/Dg.Packing/pull/1371'
        title = 'OPA-56902 Add Report Problem by Hlynur3000 · Pull Request #1371 · DigitecGalaxus/Dg.Packing'
        filename = os.path.join('Jira-PRs',
                                'OPA-56902 Add Report Problem by Hlynur3000 · Pull Request  1371 · DigitecGalaxus Dg.Packing.md')

        result = self.testee.get_or_create_file(website, title)

        self.assertEqual(result, filename)
        content = self.read_note(filename)
        self.assertIn('link: https://github.com/DigitecGalaxus/Dg.Packing/pull/1371\n', content)
        self.assertIn('story-link: https://jiradg.atlassian.net/browse/OPA-56902\n', content)

    def test_getOrCreateFile_githubPrTitleWithSupKey_stillPrNotSup(self):
        website = 'https://github.com/org/repo/pull/5'
        title = 'SUP-77 Fix thing by me · Pull Request #5 · org/repo'

        result = self.testee.get_or_create_file(website, title)

        self.assertTrue(result.startswith('Jira-PRs/'))
        self.assertIn('story-link: https://jiradg.atlassian.net/browse/SUP-77\n', self.read_note(result))

    def test_getOrCreateFile_existingNoteWithSameTitle_returnedUnchanged(self):
        website = 'https://jiradg.atlassian.net/browse/OPA-42'
        existing_filename = os.path.join('Jira', 'OPA-42  Same name - Jira.md')
        self.setup_note(existing_filename, note_with_link(website, body='# Keep me\n'))

        result = self.testee.get_or_create_file(website, 'OPA-42  Same name - Jira')

        self.assertEqual(result, existing_filename)
        self.assertEqual(self.read_note(existing_filename), note_with_link(website, body='# Keep me\n'))

    def test_getOrCreateFile_existingNoteWithNewTitle_renamedInPlaceContentKept(self):
        website = 'https://jiradg.atlassian.net/browse/OPA-42'
        old_filename = os.path.join('Jira', 'OPA-42  Old name - Jira.md')
        new_filename = os.path.join('Jira', 'OPA-42  New name - Jira.md')
        self.setup_note(old_filename, note_with_link(website, body='# Keep me\n'))

        result = self.testee.get_or_create_file(website, 'OPA-42  New name - Jira')

        self.assertEqual(result, new_filename)
        self.assertFalse((self.notes / old_filename).exists())
        self.assertEqual(self.read_note(new_filename), note_with_link(website, body='# Keep me\n'))

    def test_getOrCreateFile_existingNoteRenamed_wikilinksAcrossVaultRepaired(self):
        website = 'https://jiradg.atlassian.net/browse/OPA-42'
        self.setup_note(os.path.join('Jira', 'OPA-42  Old name - Jira.md'), note_with_link(website))
        self.setup_note('Daily.md', 'See [[OPA-42  Old name - Jira]] and [[OPA-42  Old name - Jira|alias]]\n')
        outside_notes_dir = self.vault / 'Spaces' / 'Home' / 'Private' / 'Journal.md'
        outside_notes_dir.parent.mkdir(parents=True)
        outside_notes_dir.write_text('[[Spaces/Home/DG/Jira/OPA-42  Old name - Jira#AKs]]\n', encoding='utf-8')

        self.testee.get_or_create_file(website, 'OPA-42  New name - Jira')

        self.assertEqual(self.read_note('Daily.md'),
                         'See [[OPA-42  New name - Jira]] and [[OPA-42  New name - Jira|alias]]\n')
        self.assertEqual(outside_notes_dir.read_text(encoding='utf-8'),
                         '[[Spaces/Home/DG/Jira/OPA-42  New name - Jira#AKs]]\n')

    def test_getOrCreateFile_newTitleTakenByOtherNote_nothingRenamedOrOverwritten(self):
        website = 'https://jiradg.atlassian.net/browse/OPA-42'
        old_filename = os.path.join('Jira', 'OPA-42  Old name - Jira.md')
        taken_filename = os.path.join('Jira', 'OPA-42  New name - Jira.md')
        self.setup_note(old_filename, note_with_link(website))
        self.setup_note(taken_filename, '# Someone else\n')

        result = self.testee.get_or_create_file(website, 'OPA-42  New name - Jira')

        self.assertEqual(result, old_filename)
        self.assertEqual(self.read_note(taken_filename), '# Someone else\n')

    def test_getOrCreateFile_emptyTitle_existingNoteNotRenamed(self):
        website = 'https://jiradg.atlassian.net/browse/OPA-42'
        existing_filename = os.path.join('Jira', 'OPA-42  Old name - Jira.md')
        self.setup_note(existing_filename, note_with_link(website))

        result = self.testee.get_or_create_file(website, '')

        self.assertEqual(result, existing_filename)
        self.assertTrue((self.notes / existing_filename).exists())

    def test_getOrCreateFile_existingNoteInUnrelatedSubfolder_foundAndRenamedThere(self):
        website = 'www.website.com'
        existing_filename = os.path.join('Projects', 'deep', 'Some note.md')
        self.setup_note(existing_filename, note_with_link(website))

        result = self.testee.get_or_create_file(website, 'Website Title')

        self.assertEqual(result, 'Projects/deep/Website Title.md')
        self.assertFalse((self.notes / existing_filename).exists())
        self.assertFalse((self.notes / 'Website Title.md').exists())

    def test_getOrCreateFile_urlWithQuery_matchesNoteLinkedWithoutQuery(self):
        self.setup_note('Some note.md', note_with_link('www.website.com/page'))

        result = self.testee.get_or_create_file('www.website.com/page?utm=1', 'Website Title')

        self.assertEqual(result, 'Website Title.md')
        self.assertFalse((self.notes / 'Some note.md').exists())

    def test_getOrCreateFile_linkOutsideFrontmatter_notFoundNewNoteCreated(self):
        website = 'www.website.com'
        self.setup_note('Decoy.md', f'---\ntags:\n  - Jira\n---\nlink: {website}\n')

        result = self.testee.get_or_create_file(website, 'Website Title')

        self.assertEqual(result, 'Website Title.md')
        self.assertTrue((self.notes / 'Website Title.md').exists())
        self.assertTrue((self.notes / 'Decoy.md').exists())

    def test_getOrCreateFile_noteWithoutFrontmatter_notFoundNewNoteCreated(self):
        website = 'www.website.com'
        self.setup_note('Decoy.md', f'link: {website}\n# Body\n')

        result = self.testee.get_or_create_file(website, 'Website Title')

        self.assertEqual(result, 'Website Title.md')
        self.assertTrue((self.notes / 'Decoy.md').exists())

    @patch('webnotes.NotesInterface.randint')
    def test_getOrCreateFile_filenameTakenByUnlinkedNote_randomSuffixAppended(self, mock_randint):
        mock_randint.return_value = 42
        title = 'Website Title'
        self.setup_note(title + '.md', '# Unrelated note without link\n')

        result = self.testee.get_or_create_file('www.website.com', title)

        self.assertEqual(result, title + '42.md')
        self.assertTrue((self.notes / (title + '42.md')).exists())
        self.assertEqual(self.read_note(title + '.md'), '# Unrelated note without link\n')

    def test_findNoteByLink_jiraKeyInFilename_foundWithoutFullScan(self):
        website = 'https://jiradg.atlassian.net/browse/OPA-42'
        existing_filename = os.path.join('Jira', 'OPA-42  Old name - Jira.md')
        self.setup_note(existing_filename, note_with_link(website))

        with patch('webnotes.NotesInterface.os.walk', side_effect=AssertionError('full scan not expected')):
            result = self.testee.find_note_by_link(website)

        self.assertEqual(result, 'Jira/OPA-42  Old name - Jira.md')

    def test_findNoteByLink_filenameMatchesButLinkDiffers_fallbackFindsRealNote(self):
        website = 'https://jiradg.atlassian.net/browse/OPA-42'
        self.setup_note(os.path.join('Jira', 'OPA-42  Decoy - Jira.md'),
                        note_with_link('https://jiradg.atlassian.net/browse/OPA-421'))
        self.setup_note(os.path.join('Archive', 'OPA-42  Real - Jira.md'), note_with_link(website))

        result = self.testee.find_note_by_link(website)

        self.assertEqual(result, 'Archive/OPA-42  Real - Jira.md')

    def test_findNoteByLink_keyIsPrefixOfLongerKey_notReturned(self):
        self.setup_note(os.path.join('Jira', 'OPA-1234  Other story - Jira.md'),
                        note_with_link('https://jiradg.atlassian.net/browse/OPA-1234'))

        result = self.testee.find_note_by_link('https://jiradg.atlassian.net/browse/OPA-123')

        self.assertIsNone(result)

    def test_findNoteByLink_supKey_foundInSupFolderWithoutFullScan(self):
        website = 'https://jiradg.atlassian.net/browse/SUP-77'
        self.setup_note(os.path.join('Jira-SUP', 'SUP-77  Something broken - Jira.md'), note_with_link(website))

        with patch('webnotes.NotesInterface.os.walk', side_effect=AssertionError('full scan not expected')):
            result = self.testee.find_note_by_link(website)

        self.assertEqual(result, 'Jira-SUP/SUP-77  Something broken - Jira.md')

    def test_findNoteByLink_prUrl_foundInPrFolderWithoutFullScan(self):
        website = 'https://dev.azure.com/org/project/_git/repo/pullrequest/42'
        story = 'https://jiradg.atlassian.net/browse/OPA-123'
        self.setup_note(os.path.join('Jira-PRs', 'Pull request 41: OPA-123 Other.md'),
                        f'---\nlink: https://dev.azure.com/org/project/_git/repo/pullrequest/41\nstory-link: {story}\n---\n')
        self.setup_note(os.path.join('Jira-PRs', 'Pull request 42: OPA-123 Add feature.md'),
                        f'---\nlink: {website}\nstory-link: {story}\n---\n')

        with patch('webnotes.NotesInterface.os.walk', side_effect=AssertionError('full scan not expected')):
            result = self.testee.find_note_by_link(website)

        self.assertEqual(result, 'Jira-PRs/Pull request 42: OPA-123 Add feature.md')

    def test_findNoteByLink_githubPrUrl_foundInPrFolderWithoutFullScan(self):
        website = 'https://github.com/org/repo/pull/42'
        self.setup_note(os.path.join('Jira-PRs', 'Feature by me · Pull Request  42 · org repo.md'),
                        f'---\nlink: {website}\nstory-link: https://jiradg.atlassian.net/browse/OPA-123\n---\n')

        with patch('webnotes.NotesInterface.os.walk', side_effect=AssertionError('full scan not expected')):
            result = self.testee.find_note_by_link(website)

        self.assertEqual(result, 'Jira-PRs/Feature by me · Pull Request  42 · org repo.md')
