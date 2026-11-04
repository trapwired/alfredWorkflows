# Alfred Workflow
Download the workflow here (Add Link)

# Usage
- install [alfred](https://www.alfredapp.com/)
- download and install [workflow](www.google.com)
- install [Obsidian](https://obsidian.md/download)
- copy `sample_config.ini` to `config.ini` and fill in `[OPTIONS]`:
  - `vault_root`: absolute path to the Obsidian vault
  - `notes_dir`: folder inside the vault where notes are created, relative to `vault_root`
  - `templates_dir`: folder with the note templates, relative to `vault_root`
  - `jira_template`, `jira_sup_template`, `jira_pr_template`: template file names inside `templates_dir`
  - `jira_folder_name`, `jira_sup_folder_name`, `jira_pr_folder_name`: folders inside `notes_dir` for Jira, SUP and PR notes

# How a URL finds its note
Every note created from a URL carries that URL in its frontmatter as `link:` (PR notes additionally carry the
story URL as `story-link:`). Looking up a URL scans `notes_dir` for a note with that `link:`, so notes may be
renamed or moved freely. Only when no note carries the URL is a new one created from the matching template.
