import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, List, Optional

from dg.alfred_items import emit, hint_row, query_tokens, url_row

ORGANISATION_URL = "https://github.com/DigitecGalaxus"
MINE_COMMAND = "mine"
GH_FALLBACK_PATH = "/opt/homebrew/bin/gh"
GH_TIMEOUT_SECONDS = 8
CACHE_MAX_AGE_SECONDS = 60
CACHE_FILE_NAME = "gh-mine.json"
PR_NUMBER_PATTERN = re.compile(r"#?(\d+)")

MY_OPEN_PULL_REQUESTS_QUERY = """
query {
  viewer {
    pullRequests(first: 30, states: OPEN, orderBy: {field: UPDATED_AT, direction: DESC}) {
      nodes {
        number
        title
        url
        isDraft
        reviewDecision
        repository { name nameWithOwner }
        commits(last: 1) { nodes { commit { statusCheckRollup { state } } } }
      }
    }
  }
}
"""

REVIEW_DECISION_WORDS = {
    "APPROVED": "approved",
    "CHANGES_REQUESTED": "changes requested",
    "REVIEW_REQUIRED": "review required",
    None: "no review required",
}

CI_STATE_WORDS = {
    "SUCCESS": "CI green",
    "FAILURE": "CI failing",
    "ERROR": "CI failing",
    "PENDING": "CI pending",
    "EXPECTED": "CI pending",
    None: "no CI",
}


class FetchError(Exception):
    pass


@dataclass(frozen=True)
class PullRequestLink:
    repo_name: str
    number: int
    url: str

    @property
    def label(self):
        return f"{self.repo_name} #{self.number}"

    @property
    def markdown(self):
        return f"[{self.label}]({self.url})"


@dataclass(frozen=True)
class Repo:
    key: str
    name: str

    @property
    def url(self):
        return f"{ORGANISATION_URL}/{self.name}"

    def pull_request_link(self, number):
        return PullRequestLink(self.name, number, f"{self.url}/pull/{number}")


@dataclass(frozen=True)
class Subpage:
    key: str
    title: str
    path: str


@dataclass(frozen=True)
class OpenPullRequest:
    repo_name: str
    number: int
    title: str
    url: str
    is_draft: bool
    review_decision: Optional[str]
    ci_state: Optional[str]

    @property
    def link(self):
        return PullRequestLink(self.repo_name, self.number, self.url)


REPOS = (
    Repo("packing", "Dg.Packing"),
    Repo("devinite", "devinite"),
)

SUBPAGES = (
    Subpage("pr", "Pull Requests", "/pulls?q=sort%3Aupdated-desc+is%3Apr+is%3Aopen"),
    Subpage("actions", "Actions", "/actions"),
)

FetchMyPullRequests = Callable[[], List[OpenPullRequest]]


def rows_for(tokens, fetch_my_pull_requests: FetchMyPullRequests):
    words = [token.lower() for token in tokens]
    if words[:1] == [MINE_COMMAND]:
        return my_pull_request_rows(fetch_my_pull_requests, words[1:])
    number = pr_number(words[0]) if words else None
    if number is not None:
        return pull_request_jump_rows(REPOS, number)
    return repo_navigation_rows(words) or overview_rows()


def overview_rows():
    return repo_navigation_rows([])


def repo_navigation_rows(words):
    repo_word = words[0] if words else ""
    repos = [repo for repo in REPOS if repo.key.startswith(repo_word)]
    if len(words) < 2:
        return [row for repo in repos for row in repo_rows(repo)] + mine_suggestion_rows(repo_word)
    number = pr_number(words[1])
    if number is not None:
        return pull_request_jump_rows(repos, number)
    return [
        subpage_row(repo, subpage)
        for repo in repos
        for subpage in SUBPAGES
        if subpage.key.startswith(words[1])
    ]


def pr_number(word):
    match = PR_NUMBER_PATTERN.fullmatch(word)
    return int(match.group(1)) if match else None


def repo_rows(repo):
    return [url_row(repo.name, repo.url)] + [subpage_row(repo, subpage) for subpage in SUBPAGES]


def subpage_row(repo, subpage):
    return url_row(f"{repo.name} {subpage.title}", repo.url + subpage.path)


def mine_suggestion_rows(word):
    if not MINE_COMMAND.startswith(word):
        return []
    return [hint_row(MINE_COMMAND, "My open pull requests in all repos", autocomplete=MINE_COMMAND + " ")]


def pull_request_jump_rows(repos, number):
    return [pull_request_row(repo.pull_request_link(number)) for repo in repos]


def pull_request_row(link: PullRequestLink, *, pr_title=None, subtitle=None):
    title = link.label if pr_title is None else f"{link.label} · {pr_title}"
    return url_row(title, link.url, alt=("Copy Markdown link: " + link.markdown, link.markdown), subtitle=subtitle)


def my_pull_request_rows(fetch_my_pull_requests: FetchMyPullRequests, filter_words):
    try:
        pull_requests = fetch_my_pull_requests()
    except FetchError as error:
        return [hint_row("Could not load your pull requests", str(error))]
    matching = [pull_request for pull_request in pull_requests if matches(pull_request, filter_words)]
    if not matching:
        return [no_pull_requests_row(filter_words)]
    return [my_pull_request_row(pull_request) for pull_request in matching]


def matches(pull_request: OpenPullRequest, filter_words):
    searchable = f"{pull_request.link.label} {pull_request.title}".lower()
    return all(word in searchable for word in filter_words)


def no_pull_requests_row(filter_words):
    if filter_words:
        return hint_row(f"No open pull request matches '{' '.join(filter_words)}'", "Filter by repo, number or title")
    return hint_row("No open pull requests", "Nothing of yours is open on GitHub")


def my_pull_request_row(pull_request: OpenPullRequest):
    return pull_request_row(pull_request.link, pr_title=pull_request.title, subtitle=state_summary(pull_request))


def state_summary(pull_request: OpenPullRequest):
    parts = [
        REVIEW_DECISION_WORDS.get(pull_request.review_decision, pull_request.review_decision),
        CI_STATE_WORDS.get(pull_request.ci_state, pull_request.ci_state),
    ]
    if pull_request.is_draft:
        parts.append("draft")
    return " · ".join(parts)


def fetch_my_open_pull_requests():
    gh = shutil.which("gh") or GH_FALLBACK_PATH
    try:
        completed = subprocess.run(
            [gh, "api", "graphql", "-f", "query=" + MY_OPEN_PULL_REQUESTS_QUERY],
            capture_output=True,
            text=True,
            timeout=GH_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        raise FetchError(f"gh did not answer within {GH_TIMEOUT_SECONDS} s")
    except OSError as error:
        raise FetchError(first_line(str(error)))
    if completed.returncode != 0:
        raise FetchError(first_line(completed.stderr) or f"gh exited with code {completed.returncode}")
    return parse_pull_requests(completed.stdout)


def parse_pull_requests(graphql_output):
    try:
        nodes = json.loads(graphql_output)["data"]["viewer"]["pullRequests"]["nodes"]
        return [pull_request_from_node(node) for node in nodes]
    except (ValueError, KeyError, TypeError, IndexError) as error:
        raise FetchError("Unexpected answer from gh: " + first_line(repr(error)))


def pull_request_from_node(node):
    commits = node["commits"]["nodes"]
    rollup = commits[0]["commit"]["statusCheckRollup"] if commits else None
    return OpenPullRequest(
        repo_name=node["repository"]["name"],
        number=node["number"],
        title=node["title"],
        url=node["url"],
        is_draft=node["isDraft"],
        review_decision=node["reviewDecision"],
        ci_state=rollup["state"] if rollup else None,
    )


def first_line(text):
    lines = text.strip().splitlines()
    return lines[0] if lines else ""


def cached(fetch: FetchMyPullRequests, directory: Path, clock: Callable[[], float],
           max_age_seconds=CACHE_MAX_AGE_SECONDS) -> FetchMyPullRequests:
    cache_file = directory / CACHE_FILE_NAME

    def fetch_through_cache():
        now = clock()
        fresh = read_fresh_cache(cache_file, now, max_age_seconds)
        if fresh is not None:
            return fresh
        pull_requests = fetch()
        write_cache(cache_file, now, pull_requests)
        return pull_requests

    return fetch_through_cache


def read_fresh_cache(cache_file: Path, now, max_age_seconds):
    try:
        content = json.loads(cache_file.read_text(encoding="utf-8"))
        if now - content["fetched_at"] >= max_age_seconds:
            return None
        return [OpenPullRequest(**fields) for fields in content["pull_requests"]]
    except (OSError, ValueError, KeyError, TypeError):
        return None


def write_cache(cache_file: Path, now, pull_requests):
    content = {"fetched_at": now, "pull_requests": [asdict(pull_request) for pull_request in pull_requests]}
    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(content), encoding="utf-8")
    except OSError:
        pass


def cache_directory():
    return Path(os.environ.get("alfred_workflow_cache") or Path(tempfile.gettempdir()) / "dg-alfred")


def main():
    fetch = cached(fetch_my_open_pull_requests, cache_directory(), time.time)
    emit(rows_for(query_tokens(sys.argv), fetch))


if __name__ == "__main__":
    main()
