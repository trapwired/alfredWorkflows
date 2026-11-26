import json
import tempfile
import unittest
from pathlib import Path

from dg.gh import (
    CI_STATE_WORDS,
    REVIEW_DECISION_WORDS,
    FetchError,
    OpenPullRequest,
    cached,
    parse_pull_requests,
    rows_for,
)

PACKING_URL = "https://github.com/DigitecGalaxus/Dg.Packing"
DEVINITE_URL = "https://github.com/DigitecGalaxus/devinite"
OPEN_PRS_PATH = "/pulls?q=sort%3Aupdated-desc+is%3Apr+is%3Aopen"


def pull_request(repo_name="Dg.Packing", number=1431, title="Fix label", is_draft=False,
                 review_decision="APPROVED", ci_state="SUCCESS"):
    return OpenPullRequest(
        repo_name=repo_name,
        number=number,
        title=title,
        url=f"https://github.com/DigitecGalaxus/{repo_name}/pull/{number}",
        is_draft=is_draft,
        review_decision=review_decision,
        ci_state=ci_state,
    )


def fetch_never():
    raise AssertionError("must not fetch")


def fetch_returning(*pull_requests):
    return lambda: list(pull_requests)


def run(query, fetch=fetch_never):
    return rows_for(query.split(), fetch)


def titles(rows):
    return [row["title"] for row in rows]


class FakeClock:
    def __init__(self, now):
        self.now = now

    def __call__(self):
        return self.now


class CountingFetch:
    def __init__(self, pull_requests):
        self.pull_requests = pull_requests
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return list(self.pull_requests)


class RepoNavigationTests(unittest.TestCase):
    def test_empty_query_lists_both_repos_with_subpages_and_mine(self):
        self.assertEqual(
            titles(run("")),
            [
                "Dg.Packing", "Dg.Packing Pull Requests", "Dg.Packing Actions",
                "devinite", "devinite Pull Requests", "devinite Actions",
                "mine",
            ],
        )

    def test_mine_suggestion_autocompletes_and_is_not_actionable(self):
        mine = run("")[-1]
        self.assertEqual(mine["autocomplete"], "mine ")
        self.assertFalse(mine["valid"])

    def test_repo_prefix_selects_that_repo(self):
        self.assertEqual(titles(run("pack")), ["Dg.Packing", "Dg.Packing Pull Requests", "Dg.Packing Actions"])
        self.assertEqual(titles(run("devinite")), ["devinite", "devinite Pull Requests", "devinite Actions"])

    def test_repo_match_ignores_case(self):
        self.assertEqual(titles(run("Packing"))[0], "Dg.Packing")

    def test_pr_subcommand_opens_open_pr_list(self):
        rows = run("packing pr")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["arg"], PACKING_URL + OPEN_PRS_PATH)

    def test_subcommand_matches_by_prefix(self):
        rows = run("devinite act")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["arg"], DEVINITE_URL + "/actions")

    def test_cmd_copies_url(self):
        row = run("packing pr")[0]
        self.assertEqual(row["mods"]["cmd"]["arg"], PACKING_URL + OPEN_PRS_PATH)

    def test_unknown_query_falls_back_to_overview(self):
        self.assertEqual(titles(run("xyz")), titles(run("")))
        self.assertEqual(titles(run("packing xyz")), titles(run("")))

    def test_prefix_of_mine_shows_only_the_suggestion(self):
        self.assertEqual(titles(run("mi")), ["mine"])


class PullRequestJumpTests(unittest.TestCase):
    def test_repo_and_number_opens_that_pull_request(self):
        rows = run("packing 1431")
        self.assertEqual(titles(rows), ["Dg.Packing #1431"])
        self.assertEqual(rows[0]["arg"], PACKING_URL + "/pull/1431")

    def test_number_may_carry_a_hash(self):
        self.assertEqual(run("packing #1431")[0]["arg"], PACKING_URL + "/pull/1431")

    def test_number_alone_gives_one_row_per_repo_packing_first(self):
        rows = run("1431")
        self.assertEqual(titles(rows), ["Dg.Packing #1431", "devinite #1431"])
        self.assertEqual([row["arg"] for row in rows], [PACKING_URL + "/pull/1431", DEVINITE_URL + "/pull/1431"])

    def test_hash_number_alone(self):
        self.assertEqual(titles(run("#1431")), ["Dg.Packing #1431", "devinite #1431"])

    def test_cmd_copies_url_and_alt_copies_markdown_link(self):
        row = run("packing 1431")[0]
        self.assertEqual(row["mods"]["cmd"]["arg"], PACKING_URL + "/pull/1431")
        self.assertEqual(
            row["mods"]["alt"]["arg"],
            "[Dg.Packing #1431](https://github.com/DigitecGalaxus/Dg.Packing/pull/1431)",
        )


class MineTests(unittest.TestCase):
    def test_row_shows_label_title_and_state(self):
        rows = run("mine", fetch_returning(pull_request()))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "Dg.Packing #1431 · Fix label")
        self.assertEqual(rows[0]["subtitle"], "approved · CI green")
        self.assertEqual(rows[0]["arg"], PACKING_URL + "/pull/1431")

    def test_cmd_copies_url_and_alt_copies_markdown_link_without_title(self):
        row = run("mine", fetch_returning(pull_request()))[0]
        self.assertEqual(row["mods"]["cmd"]["arg"], PACKING_URL + "/pull/1431")
        self.assertEqual(
            row["mods"]["alt"]["arg"],
            "[Dg.Packing #1431](https://github.com/DigitecGalaxus/Dg.Packing/pull/1431)",
        )

    def test_draft_with_review_required_and_failing_ci(self):
        draft = pull_request(is_draft=True, review_decision="REVIEW_REQUIRED", ci_state="FAILURE")
        self.assertEqual(run("mine", fetch_returning(draft))[0]["subtitle"], "review required · CI failing · draft")

    def test_null_review_decision_and_missing_rollup(self):
        bare = pull_request(review_decision=None, ci_state=None)
        self.assertEqual(run("mine", fetch_returning(bare))[0]["subtitle"], "no review required · no CI")

    def test_filter_over_repo_number_and_title_ignoring_case(self):
        fetch = fetch_returning(
            pull_request(number=1431, title="Fix label"),
            pull_request(repo_name="devinite", number=77, title="Rename Carrier"),
        )
        self.assertEqual(titles(run("mine DEVINITE", fetch)), ["devinite #77 · Rename Carrier"])
        self.assertEqual(titles(run("mine 1431", fetch)), ["Dg.Packing #1431 · Fix label"])
        self.assertEqual(titles(run("mine #77", fetch)), ["devinite #77 · Rename Carrier"])
        self.assertEqual(titles(run("mine carrier", fetch)), ["devinite #77 · Rename Carrier"])

    def test_no_match_gives_a_hint(self):
        rows = run("mine nothing", fetch_returning(pull_request()))
        self.assertEqual(len(rows), 1)
        self.assertFalse(rows[0]["valid"])

    def test_no_open_pull_requests_gives_a_hint(self):
        rows = run("mine", fetch_returning())
        self.assertEqual(len(rows), 1)
        self.assertFalse(rows[0]["valid"])

    def test_fetch_failure_gives_one_hint_with_the_error(self):
        def failing_fetch():
            raise FetchError("To get started with GitHub CLI, please run:  gh auth login")

        rows = run("mine", failing_fetch)
        self.assertEqual(len(rows), 1)
        self.assertFalse(rows[0]["valid"])
        self.assertEqual(rows[0]["subtitle"], "To get started with GitHub CLI, please run:  gh auth login")


class ParsePullRequestsTests(unittest.TestCase):
    def node(self, commits):
        return {
            "number": 1431,
            "title": "Fix label",
            "url": PACKING_URL + "/pull/1431",
            "isDraft": True,
            "reviewDecision": None,
            "repository": {"name": "Dg.Packing", "nameWithOwner": "DigitecGalaxus/Dg.Packing"},
            "commits": {"nodes": commits},
        }

    def output(self, *nodes):
        return json.dumps({"data": {"viewer": {"pullRequests": {"nodes": list(nodes)}}}})

    def test_reads_all_fields(self):
        commit = {"commit": {"statusCheckRollup": {"state": "PENDING"}}}
        self.assertEqual(
            parse_pull_requests(self.output(self.node([commit]))),
            [pull_request(is_draft=True, review_decision=None, ci_state="PENDING")],
        )

    def test_null_rollup_and_no_commits_mean_no_ci_state(self):
        null_rollup = {"commit": {"statusCheckRollup": None}}
        parsed = parse_pull_requests(self.output(self.node([null_rollup]), self.node([])))
        self.assertEqual([pr.ci_state for pr in parsed], [None, None])

    def test_unparsable_output_raises_fetch_error(self):
        for output in ("not json", "{}", json.dumps({"data": None})):
            with self.subTest(output=output):
                with self.assertRaises(FetchError):
                    parse_pull_requests(output)


class StateWordsTests(unittest.TestCase):
    def test_every_github_value_has_words(self):
        self.assertEqual(set(REVIEW_DECISION_WORDS), {"APPROVED", "CHANGES_REQUESTED", "REVIEW_REQUIRED", None})
        self.assertEqual(set(CI_STATE_WORDS), {"SUCCESS", "FAILURE", "ERROR", "PENDING", "EXPECTED", None})


class CacheTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name) / "cache"
        self.clock = FakeClock(1000.0)
        self.fetch = CountingFetch([pull_request()])
        self.cached_fetch = cached(self.fetch, self.directory, self.clock)

    def test_creates_the_directory_and_returns_fetched_list(self):
        self.assertEqual(self.cached_fetch(), [pull_request()])
        self.assertTrue(self.directory.is_dir())

    def test_hit_within_sixty_seconds(self):
        self.cached_fetch()
        self.clock.now += 59
        self.assertEqual(self.cached_fetch(), [pull_request()])
        self.assertEqual(self.fetch.calls, 1)

    def test_refetch_after_sixty_seconds(self):
        self.cached_fetch()
        self.clock.now += 60
        self.cached_fetch()
        self.assertEqual(self.fetch.calls, 2)

    def test_corrupt_cache_file_is_a_miss(self):
        self.directory.mkdir()
        (self.directory / "gh-mine.json").write_text("{half", encoding="utf-8")
        self.assertEqual(self.cached_fetch(), [pull_request()])
        self.assertEqual(self.fetch.calls, 1)

    def test_failure_propagates_and_is_not_cached(self):
        def failing_fetch():
            raise FetchError("offline")

        with self.assertRaises(FetchError):
            cached(failing_fetch, self.directory, self.clock)()
        self.assertEqual(self.cached_fetch(), [pull_request()])
        self.assertEqual(self.fetch.calls, 1)


if __name__ == "__main__":
    unittest.main()
