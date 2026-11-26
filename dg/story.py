import sys
from pathlib import Path

from dg.claude_tab import open_claude_tab

VAULT = Path.home() / "notes-dg"
TAB_NAME = "Story"
PROMPT = (
    "/jira Neue Story erfassen (OPA, Team Phoenix). Zeig mir zuerst den Entwurf und frag nach, was fehlt. "
    "Leg die Story erst nach meinem OK in Jira an. Danach die Jira-Notiz anlegen und im heutigen Daily verlinken. "
    "Idee: {idea}"
)


def story_prompt(idea):
    return PROMPT.format(idea=idea.strip())


def main():
    idea = " ".join(sys.argv[1:]).strip()
    if not idea:
        sys.exit("story: Einzeiler fehlt")
    open_claude_tab(TAB_NAME, VAULT, story_prompt(idea))


if __name__ == "__main__":
    main()
