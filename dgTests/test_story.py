import unittest
from unittest import mock

from dg import story


class Story(unittest.TestCase):
    def test_prompt_starts_with_the_jira_skill_and_carries_the_idea(self):
        prompt = story.story_prompt("  REA Verdeckler liest Stückgut-Label ")

        self.assertTrue(prompt.startswith("/jira Neue Story erfassen"))
        self.assertTrue(prompt.endswith("Idee: REA Verdeckler liest Stückgut-Label"))
        self.assertIn("erst nach meinem OK", prompt)

    def test_opens_one_tab_in_the_work_vault(self):
        with mock.patch.object(story, "open_claude_tab") as open_claude_tab, mock.patch.object(
            story.sys, "argv", ["story", "Label", "drehen"]
        ):
            story.main()

        open_claude_tab.assert_called_once_with("Story", story.VAULT, story.story_prompt("Label drehen"))
        self.assertEqual(story.VAULT.name, "notes-dg")

    def test_missing_idea_opens_nothing(self):
        with mock.patch.object(story, "open_claude_tab") as open_claude_tab, mock.patch.object(
            story.sys, "argv", ["story", "  "]
        ):
            with self.assertRaises(SystemExit):
                story.main()

        open_claude_tab.assert_not_called()


if __name__ == "__main__":
    unittest.main()
