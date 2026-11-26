import json
import shlex
import sys
import unittest

from dg.story import claude_command, tab_config


def startup_command(config):
    line = [line for line in config.splitlines() if line.startswith("commands = [")][0]
    return json.loads(line[len("commands = "):])[0]


class StoryTabConfig(unittest.TestCase):
    def test_prompt_reaches_claude_as_one_argument_with_the_idea(self):
        argv = shlex.split(claude_command("REA Verdeckler liest Stückgut-Label"))

        self.assertEqual(argv[0], "claude")
        self.assertEqual(len(argv), 2)
        self.assertTrue(argv[1].startswith("/jira Neue Story erfassen"))
        self.assertIn("REA Verdeckler liest Stückgut-Label", argv[1])
        self.assertIn("erst nach meinem OK", argv[1])

    def test_command_stays_on_one_line(self):
        self.assertNotIn("\n", claude_command("erste Zeile\nzweite Zeile"))

    def test_shell_metacharacters_in_the_idea_stay_literal(self):
        idea = "Label 'A' mit \"B\", $HOME und `whoami`; rm -rf x"

        argv = shlex.split(startup_command(tab_config(idea)))

        self.assertEqual(len(argv), 2)
        self.assertIn(idea, argv[1])

    def test_tab_is_one_terminal_pane_in_the_work_vault(self):
        config = tab_config("x")

        self.assertEqual(config.count("[[panes]]"), 1)
        self.assertIn('type = "terminal"', config)
        self.assertIn("notes-dg", [line for line in config.splitlines() if line.startswith("directory = ")][0])

    @unittest.skipIf(sys.version_info < (3, 11), "tomllib needs Python 3.11")
    def test_config_is_valid_toml_even_with_quotes_and_backslashes(self):
        import tomllib

        idea = "Pfad C:\\temp mit \"Anführung\" und 'Apostroph' – Umlaut ä"

        parsed = tomllib.loads(tab_config(idea))

        self.assertEqual(parsed["name"], "Story")
        self.assertEqual(len(parsed["panes"]), 1)
        self.assertIn(idea, shlex.split(parsed["panes"][0]["commands"][0])[1])


if __name__ == "__main__":
    unittest.main()
