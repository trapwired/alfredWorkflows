import json
import shlex
import subprocess
import sys
from pathlib import Path

VAULT = Path.home() / "notes-dg"
WARP_TAB_CONFIGS = Path.home() / ".warp" / "tab_configs"
TAB_CONFIG_NAME = "story"
TAB_TITLE = "Story"
PROMPT = (
    "/jira Neue Story erfassen (OPA, Team Phoenix). Zeig mir zuerst den Entwurf und frag nach, was fehlt. "
    "Leg die Story erst nach meinem OK in Jira an. Danach die Jira-Notiz anlegen und im heutigen Daily verlinken. "
    "Idee: {idea}"
)


def claude_command(idea):
    single_line_idea = " ".join(idea.split())
    return "claude " + shlex.quote(PROMPT.format(idea=single_line_idea))


def toml_string(text):
    # JSON string escapes are valid in a TOML basic string, so quotes and backslashes in the idea cannot break the file.
    return json.dumps(text, ensure_ascii=False)


def tab_config(idea):
    return "\n".join(
        [
            "name = " + toml_string(TAB_TITLE),
            "title = " + toml_string(TAB_TITLE),
            "",
            "[[panes]]",
            'id = "claude"',
            'type = "terminal"',
            "directory = " + toml_string(str(VAULT)),
            "commands = [" + toml_string(claude_command(idea)) + "]",
            "",
        ]
    )


def main():
    idea = " ".join(sys.argv[1:]).strip()
    if not idea:
        sys.exit("story: Einzeiler fehlt")
    WARP_TAB_CONFIGS.mkdir(parents=True, exist_ok=True)
    (WARP_TAB_CONFIGS / (TAB_CONFIG_NAME + ".toml")).write_text(tab_config(idea), encoding="utf-8")
    # A tab config opens as a tab in the active Warp window; a launch configuration always opened a new window.
    subprocess.run(["open", "warp://tab_config/" + TAB_CONFIG_NAME], check=True)


if __name__ == "__main__":
    main()
