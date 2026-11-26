import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

WARP_TAB_CONFIGS = Path.home() / ".warp" / "tab_configs"


def tab_config_stem(tab_name):
    return re.sub(r"[^a-z0-9]+", "_", tab_name.lower()).strip("_")


def claude_command(prompt):
    single_line_prompt = " ".join(prompt.split())
    return "claude " + shlex.quote(single_line_prompt)


def toml_string(text):
    # JSON string escapes are valid in a TOML basic string, so quotes and backslashes in a prompt cannot break the file.
    return json.dumps(text, ensure_ascii=False)


def tab_config(tab_name, directory, prompt):
    return "\n".join(
        [
            "name = " + toml_string(tab_name),
            "title = " + toml_string(tab_name),
            "",
            "[[panes]]",
            'id = "claude"',
            'type = "terminal"',
            "directory = " + toml_string(str(directory)),
            "commands = [" + toml_string(claude_command(prompt)) + "]",
            "",
        ]
    )


def open_claude_tab(tab_name, directory, prompt):
    stem = tab_config_stem(tab_name)
    WARP_TAB_CONFIGS.mkdir(parents=True, exist_ok=True)
    (WARP_TAB_CONFIGS / (stem + ".toml")).write_text(tab_config(tab_name, directory, prompt), encoding="utf-8")
    # A tab config opens as a tab in the active Warp window; a launch configuration always opens a new window.
    subprocess.run(["open", "warp://tab_config/" + stem], check=True)


def main():
    if len(sys.argv) != 4 or not all(argument.strip() for argument in sys.argv[1:]):
        sys.exit("usage: python3 -m dg.claude_tab <tab name> <directory> <prompt>")
    open_claude_tab(*sys.argv[1:])


if __name__ == "__main__":
    main()
