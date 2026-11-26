import json
import unittest
from dataclasses import dataclass

from dg.selection import (
    Catalog,
    Link,
    Target,
    classify_tokens,
    matching_entries,
    rows_or_regen_hint,
    select_rows,
    targets_in_order,
)


@dataclass(frozen=True)
class Entry:
    keyword: str
    title: str
    summary: str = "summary"


ENTRIES = [Entry("flow", "Flow Pos 3"), Entry("unipack", "UniPack Workflow"), Entry("etk", "ETK Workflow")]
TARGETS = targets_in_order(("dev", "test", "prod"), ("ch", "eu"))


def link(entry, target, remaining):
    return Link(f"https://{entry.keyword}/{target.mandator}/{target.environment}/{'/'.join(remaining)}")


CATALOG = Catalog("entries", ENTRIES, lambda _: TARGETS, link)


def titles(rows):
    return [row["title"] for row in rows]


class ClassifyTokensTest(unittest.TestCase):
    def test_environment_prefixes_and_mandators_are_recognised(self):
        narrowing = classify_tokens(["pr", "T", "eu", "123"])
        self.assertEqual(narrowing.environments, frozenset({"prod", "test"}))
        self.assertEqual(narrowing.mandators, frozenset({"eu"}))
        self.assertEqual(narrowing.remaining, ("123",))

    def test_mandator_needs_the_full_token(self):
        self.assertEqual(classify_tokens(["e"]).remaining, ("e",))

    def test_remaining_tokens_keep_their_case(self):
        self.assertEqual(classify_tokens(["AbC"]).remaining, ("AbC",))


class MatchingEntriesTest(unittest.TestCase):
    def test_exact_keyword_wins_over_substring(self):
        self.assertEqual(matching_entries(ENTRIES, "flow"), [ENTRIES[0]])

    def test_substring_matches_keyword_and_title_case_insensitively(self):
        self.assertEqual(matching_entries(ENTRIES, "WORK"), [ENTRIES[1], ENTRIES[2]])

    def test_no_token_lists_everything(self):
        self.assertEqual(matching_entries(ENTRIES, None), ENTRIES)


class SelectRowsTest(unittest.TestCase):
    def test_empty_query_lists_candidates_with_autocomplete(self):
        rows = select_rows(CATALOG, [])
        self.assertEqual(titles(rows), ["Flow Pos 3", "UniPack Workflow", "ETK Workflow"])
        self.assertEqual(rows[1]["autocomplete"], "unipack ")
        self.assertEqual(rows[1]["arg"], "https://unipack/ch/dev/")

    def test_nothing_found_is_one_hint_row(self):
        rows = select_rows(CATALOG, ["zzz"])
        self.assertEqual(len(rows), 1)
        self.assertFalse(rows[0]["valid"])

    def test_single_match_lists_every_target_in_order(self):
        rows = select_rows(CATALOG, ["uni"])
        self.assertEqual(
            titles(rows),
            [f"UniPack Workflow - {mandator} {env}" for env in ("DEV", "TEST", "PROD") for mandator in ("CH", "EU")],
        )

    def test_environment_and_mandator_tokens_narrow_the_targets(self):
        rows = select_rows(CATALOG, ["unipack", "pr", "eu"])
        self.assertEqual(titles(rows), ["UniPack Workflow - EU PROD"])

    def test_remaining_tokens_reach_the_link(self):
        rows = select_rows(CATALOG, ["etk", "test", "ch", "42"])
        self.assertEqual([row["arg"] for row in rows], ["https://etk/ch/test/42"])

    def test_candidates_open_the_first_target_the_narrowing_allows(self):
        rows = select_rows(CATALOG, ["work", "prod"])
        self.assertEqual(rows[0]["arg"], "https://unipack/ch/prod/")

    def test_default_mandators_apply_without_a_mandator_token(self):
        catalog = CATALOG._replace(default_mandators=("ch",))
        self.assertEqual(len(select_rows(catalog, ["etk"])), 3)
        self.assertEqual(titles(select_rows(catalog, ["etk", "eu", "dev"])), ["ETK Workflow - EU DEV"])

    def test_targets_without_mandator_ignore_mandator_tokens(self):
        catalog = CATALOG._replace(targets=lambda _: [Target(None, "prod")])
        self.assertEqual(titles(select_rows(catalog, ["etk", "eu"])), ["ETK Workflow - PROD"])

    def test_narrowing_that_excludes_every_target_is_a_hint(self):
        catalog = CATALOG._replace(targets=lambda _: [Target("eu", "dev")])
        rows = select_rows(catalog, ["etk", "ch"])
        self.assertEqual(len(rows), 1)
        self.assertFalse(rows[0]["valid"])
        self.assertIn("EU DEV", rows[0]["subtitle"])


class RowsOrRegenHintTest(unittest.TestCase):
    def test_unreadable_input_becomes_a_regen_hint(self):
        def broken_json():
            return json.loads("{")

        rows = rows_or_regen_hint(["x"], broken_json, lambda tokens, entries: self.fail("must not build rows"))
        self.assertEqual(len(rows), 1)
        self.assertIn("dg regen", rows[0]["title"])
        self.assertFalse(rows[0]["valid"])


if __name__ == "__main__":
    unittest.main()
