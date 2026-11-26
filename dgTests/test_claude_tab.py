import json
import shlex
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from dg import claude_tab


def startup_command(config):
    line = [line for line in config.splitlines() if line.startswith("commands = [")][0]
    return json.loads(line[len("commands = "):])[0]


class TabConfig(unittest.TestCase):
    def test_prompt_reaches_claude_as_one_argument(self):
        argv = shlex.split(claude_tab.claude_command("/next Kretschi fragen"))

        self.assertEqual(argv, ["claude", "/next Kretschi fragen"])

    def test_command_stays_on_one_line(self):
        self.assertNotIn("\n", claude_tab.claude_command("erste Zeile\nzweite Zeile"))

    def test_shell_metacharacters_in_the_prompt_stay_literal(self):
        prompt = "/next Label 'A' mit \"B\", $HOME und `whoami`; rm -rf x"

        argv = shlex.split(startup_command(claude_tab.tab_config("next", "/vault", prompt)))

        self.assertEqual(argv, ["claude", prompt])

    def test_tab_is_one_terminal_pane_in_the_given_directory(self):
        config = claude_tab.tab_config("end-day-p", "/Users/x/notes-domi", "/end-day")

        self.assertEqual(config.count("[[panes]]"), 1)
        self.assertIn('type = "terminal"', config)
        self.assertIn('directory = "/Users/x/notes-domi"', config)
        self.assertIn('title = "end-day-p"', config)

    @unittest.skipIf(sys.version_info < (3, 11), "tomllib needs Python 3.11")
    def test_config_is_valid_toml_even_with_quotes_and_backslashes(self):
        import tomllib

        prompt = "/next Pfad C:\\temp mit \"Anführung\" und 'Apostroph' – Umlaut ä"

        parsed = tomllib.loads(claude_tab.tab_config("next", "/vault", prompt))

        self.assertEqual(parsed["name"], "next")
        self.assertEqual(len(parsed["panes"]), 1)
        self.assertEqual(shlex.split(parsed["panes"][0]["commands"][0]), ["claude", prompt])


class TabConfigStem(unittest.TestCase):
    def test_stem_is_lowercase_with_underscores(self):
        self.assertEqual(claude_tab.tab_config_stem("start-day"), "start_day")
        self.assertEqual(claude_tab.tab_config_stem("Story"), "story")
        self.assertEqual(claude_tab.tab_config_stem("sb-planning-day"), "sb_planning_day")


class OpenClaudeTab(unittest.TestCase):
    def test_writes_the_config_and_opens_it_by_its_file_stem(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(
            claude_tab, "WARP_TAB_CONFIGS", Path(folder) / "tab_configs"
        ), mock.patch.object(claude_tab.subprocess, "run") as run:
            claude_tab.open_claude_tab("harvest-todos", "/vault", "/harvest-todos")

            written = (Path(folder) / "tab_configs" / "harvest_todos.toml").read_text(encoding="utf-8")

        self.assertEqual(shlex.split(startup_command(written)), ["claude", "/harvest-todos"])
        run.assert_called_once_with(["open", "warp://tab_config/harvest_todos"], check=True)

    def test_wrong_argument_count_opens_nothing(self):
        with mock.patch.object(claude_tab, "open_claude_tab") as open_claude_tab, mock.patch.object(
            claude_tab.sys, "argv", ["claude_tab", "next", "/vault"]
        ):
            with self.assertRaises(SystemExit):
                claude_tab.main()

        open_claude_tab.assert_not_called()


if __name__ == "__main__":
    unittest.main()
