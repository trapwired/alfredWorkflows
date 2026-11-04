import configparser
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class VaultPaths:
    root: Path
    notes_dir: str
    templates_dir: str
    jira_folder_name: str
    jira_sup_folder_name: str
    jira_pr_folder_name: str
    jira_template: str
    jira_sup_template: str
    jira_pr_template: str

    @property
    def notes(self) -> Path:
        return self.root / self.notes_dir

    @property
    def jira_dir(self) -> Path:
        return self.notes / self.jira_folder_name

    @property
    def jira_sup_dir(self) -> Path:
        return self.notes / self.jira_sup_folder_name

    @property
    def jira_pr_dir(self) -> Path:
        return self.notes / self.jira_pr_folder_name

    def template(self, name: str) -> Path:
        return self.root / self.templates_dir / name

    @classmethod
    def from_config(cls, config_path) -> 'VaultPaths':
        config = configparser.RawConfigParser()
        config.read(config_path, encoding='utf8')
        if not config.has_section('OPTIONS'):
            raise FileNotFoundError(f'No [OPTIONS] section found in {config_path}')
        options = config['OPTIONS']
        return cls(
            root=Path(options['vault_root']).expanduser(),
            notes_dir=options['notes_dir'],
            templates_dir=options['templates_dir'],
            jira_folder_name=options['jira_folder_name'],
            jira_sup_folder_name=options['jira_sup_folder_name'],
            jira_pr_folder_name=options['jira_pr_folder_name'],
            jira_template=options['jira_template'],
            jira_sup_template=options['jira_sup_template'],
            jira_pr_template=options['jira_pr_template'],
        )
