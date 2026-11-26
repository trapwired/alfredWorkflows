import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import unquote

from dg.deploy import deploy_rows, deployments_from, load_deployments
from dg.selection import rows_or_regen_hint

DEPLOYMENTS = {
    "source": {},
    "deployments": [
        {"folder": "dg-packing-messaging", "appname": "dg-packing-messaging", "hosts": {}},
        {"folder": "dg-packing-workflow-atk2", "appname": "dg-packing-workflow-atk2", "hosts": {"ch": {"dev": "x"}}},
        {"folder": "dg-packing-workflow-atk3", "appname": "dg-packing-workflow-atk3", "hosts": {}},
    ],
}
DEPLOYMENTS_ENTRIES = deployments_from(DEPLOYMENTS)
LOGS = "https://app.datadoghq.eu/logs?query="
ERROR_STATUS = " status:(error OR critical OR alert OR emergency)"


def rows(query):
    return deploy_rows(query.split(), DEPLOYMENTS_ENTRIES)


def logs_query(row, key="arg"):
    value = row[key] if key == "arg" else row["mods"][key]["arg"]
    return unquote(value).removeprefix(LOGS)


class DeploymentsFromTest(unittest.TestCase):
    def test_keyword_is_folder_without_prefix_and_title_is_folder(self):
        self.assertEqual(
            [(deployment.keyword, deployment.title) for deployment in DEPLOYMENTS_ENTRIES],
            [
                ("messaging", "dg-packing-messaging"),
                ("workflow-atk2", "dg-packing-workflow-atk2"),
                ("workflow-atk3", "dg-packing-workflow-atk3"),
            ],
        )


class DeployRowsTest(unittest.TestCase):
    def test_empty_query_lists_every_deployment_opening_prod(self):
        result = rows("")
        self.assertEqual(len(result), 3)
        self.assertEqual(logs_query(result[0]), "kube_deployment:dg-packing-messaging* env:prod")

    def test_single_match_lists_prod_test_dev(self):
        self.assertEqual(
            [row["title"] for row in rows("messaging")],
            ["dg-packing-messaging - PROD", "dg-packing-messaging - TEST", "dg-packing-messaging - DEV"],
        )

    def test_environment_narrows_and_mandator_is_ignored(self):
        self.assertEqual([row["title"] for row in rows("messaging te ch")], ["dg-packing-messaging - TEST"])

    def test_substring_with_several_matches_lists_candidates(self):
        self.assertEqual([row["autocomplete"] for row in rows("atk")], ["workflow-atk2 ", "workflow-atk3 "])

    def test_level_tokens_append_status_filter(self):
        self.assertEqual(logs_query(rows("messaging prod info")[0]), "kube_deployment:dg-packing-messaging* env:prod status:info")
        self.assertEqual(logs_query(rows("messaging prod warn")[0]), "kube_deployment:dg-packing-messaging* env:prod status:warn")
        self.assertEqual(logs_query(rows("messaging prod crit")[0]), "kube_deployment:dg-packing-messaging* env:prod" + ERROR_STATUS)
        self.assertEqual(logs_query(rows("messaging prod error")[0]), "kube_deployment:dg-packing-messaging* env:prod" + ERROR_STATUS)

    def test_level_token_drops_alt_and_ctrl(self):
        self.assertEqual(set(rows("messaging prod crit")[0]["mods"]), {"cmd"})

    def test_without_level_alt_opens_errors_and_ctrl_opens_warnings(self):
        row = rows("messaging dev")[0]
        self.assertEqual(logs_query(row, "alt"), "kube_deployment:dg-packing-messaging* env:dev" + ERROR_STATUS)
        self.assertEqual(logs_query(row, "ctrl"), "kube_deployment:dg-packing-messaging* env:dev status:warn")
        self.assertTrue(row["mods"]["alt"]["subtitle"].startswith("Errors only"))
        self.assertTrue(row["mods"]["ctrl"]["subtitle"].startswith("Warnings only"))

    def test_cmd_copies_the_url(self):
        row = rows("messaging prod")[0]
        self.assertEqual(row["mods"]["cmd"]["arg"], row["arg"])

    def test_level_applies_to_candidates(self):
        self.assertTrue(logs_query(rows("atk warn")[0]).endswith("env:prod status:warn"))

    def test_missing_generated_file_is_a_regen_hint(self):
        with patch("dg.alfred_items.GENERATED_DIR", Path("/nonexistent")):
            result = rows_or_regen_hint(["messaging"], load_deployments, deploy_rows)
        self.assertEqual(len(result), 1)
        self.assertIn("dg regen", result[0]["title"])


if __name__ == "__main__":
    unittest.main()
