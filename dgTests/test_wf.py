import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import unquote

from dg.selection import rows_or_regen_hint
from dg.wf import load_workflows, workflow_rows, workflows_from

DEPLOYMENTS = {
    "source": {},
    "deployments": [
        {
            "folder": "dg-packing-workflow-unipack",
            "appname": "dg-packing-workflow-unipack",
            "hosts": {
                "eu": {"dev": "unipack-eu.dev", "prod": "unipack-eu.prod"},
                "ch": {"dev": "unipack-ch.dev", "test": "unipack-ch.test", "prod": "unipack-ch.prod"},
            },
        },
        {
            "folder": "dg-packing-workflow-atk2",
            "appname": "dg-packing-workflow-atk2",
            "hosts": {"ch": {"dev": "atk2-ch.dev"}},
        },
        {
            "folder": "dg-packing-workflow-cmc-prepack",
            "appname": "dg-packing-workflow-cmc-prepack",
            "hosts": {"ch": {"test": "cmc-ch.test"}},
        },
        {
            "folder": "dg-packing-cache-inspector",
            "appname": "dg-packing-cache-inspector",
            "hosts": {"ch": {"dev": "inspector-ch.dev"}},
        },
        {"folder": "dg-packing-workflow-silent", "appname": "dg-packing-workflow-silent", "hosts": {}},
        {"folder": "dg-packing-messaging", "appname": "dg-packing-messaging", "hosts": {"ch": {"dev": "messaging.dev"}}},
    ],
}

OVERRIDES = {
    "workflows": {
        "dg-packing-workflow-atk2": {"keyword": "atk2", "title": "ATK 2 Workflow"},
        "dg-packing-workflow-unipack": {"title": "UniPack Workflow"},
        "dg-packing-cache-inspector": {"keyword": "inspector", "title": "Cache Inspector"},
    },
    "extra_workflows": [
        {
            "keyword": "flow",
            "title": "Flow Pos 3",
            "appname": "dg-packing-workflows",
            "hosts": {"ch": {"dev": "flow-ch.dev", "prod": "flow-ch.prod"}},
            "path": "/manual-packing/flow",
            "datadog_query": "@service:dg.packing.workflows*",
        }
    ],
    "tdfs": {},
}

WORKFLOWS = workflows_from(DEPLOYMENTS, OVERRIDES)


def rows(query):
    return workflow_rows(query.split(), WORKFLOWS)


def titles(result):
    return [row["title"] for row in result]


class WorkflowsFromTest(unittest.TestCase):
    def test_entries_are_workflow_folders_with_hosts_overridden_folders_and_extras(self):
        self.assertEqual(
            [workflow.keyword for workflow in WORKFLOWS],
            ["unipack", "atk2", "cmcprepack", "inspector", "flow"],
        )

    def test_keyword_and_title_are_derived_without_override(self):
        cmc = next(workflow for workflow in WORKFLOWS if workflow.keyword == "cmcprepack")
        self.assertEqual(cmc.title, "Cmc Prepack")

    def test_override_with_title_only_keeps_derived_keyword(self):
        self.assertEqual(WORKFLOWS[0].keyword, "unipack")
        self.assertEqual(WORKFLOWS[0].title, "UniPack Workflow")


class WorkflowRowsTest(unittest.TestCase):
    def test_empty_query_lists_all_workflows_opening_first_target(self):
        result = rows("")
        self.assertEqual(len(result), 5)
        self.assertEqual(result[0]["arg"], "https://unipack-ch.dev")
        self.assertEqual(result[0]["autocomplete"], "unipack ")
        cmc = next(row for row in result if row["title"] == "Cmc Prepack")
        self.assertEqual(cmc["arg"], "https://cmc-ch.test")

    def test_exact_keyword_flow_does_not_match_every_workflow(self):
        self.assertEqual(titles(rows("flow")), ["Flow Pos 3 - CH DEV", "Flow Pos 3 - CH PROD"])

    def test_substring_with_several_matches_lists_candidates(self):
        self.assertEqual(titles(rows("work")), ["UniPack Workflow", "ATK 2 Workflow"])

    def test_single_match_lists_targets_by_environment_then_mandator(self):
        self.assertEqual(
            titles(rows("unipack")),
            [
                "UniPack Workflow - CH DEV",
                "UniPack Workflow - EU DEV",
                "UniPack Workflow - CH TEST",
                "UniPack Workflow - CH PROD",
                "UniPack Workflow - EU PROD",
            ],
        )

    def test_environment_and_mandator_narrow_targets(self):
        self.assertEqual(titles(rows("unipack pr eu")), ["UniPack Workflow - EU PROD"])
        self.assertEqual(titles(rows("unipack dev")), ["UniPack Workflow - CH DEV", "UniPack Workflow - EU DEV"])

    def test_target_url_includes_path_of_extra_workflow(self):
        self.assertEqual(rows("flow prod")[0]["arg"], "https://flow-ch.prod/manual-packing/flow")

    def test_cmd_copies_the_url(self):
        row = rows("atk2")[0]
        self.assertEqual(row["mods"]["cmd"]["arg"], "https://atk2-ch.dev")

    def test_alt_opens_kube_deployment_logs_by_default(self):
        row = rows("unipack test")[0]
        self.assertEqual(
            unquote(row["mods"]["alt"]["arg"]),
            "https://app.datadoghq.eu/logs?query=kube_deployment:dg-packing-workflow-unipack* env:test",
        )

    def test_alt_uses_the_override_datadog_query(self):
        row = rows("flow prod")[0]
        self.assertEqual(
            unquote(row["mods"]["alt"]["arg"]),
            "https://app.datadoghq.eu/logs?query=@service:dg.packing.workflows* env:prod",
        )

    def test_nothing_found_is_a_hint(self):
        result = rows("zzz")
        self.assertEqual(len(result), 1)
        self.assertFalse(result[0]["valid"])

    def test_missing_generated_file_is_a_regen_hint(self):
        with patch("dg.alfred_items.GENERATED_DIR", Path("/nonexistent")):
            result = rows_or_regen_hint(["unipack"], load_workflows, workflow_rows)
        self.assertEqual(len(result), 1)
        self.assertIn("dg regen", result[0]["title"])


if __name__ == "__main__":
    unittest.main()
