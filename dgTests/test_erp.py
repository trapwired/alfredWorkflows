import json
import unittest
from pathlib import Path
from unittest.mock import patch

from dg.erp import ERP_PAGES_PATH, erp_pages_from, erp_rows, load_erp_pages
from dg.selection import rows_or_regen_hint

SHORTCUTS = [
    {"keyword": "feat", "title": "Feature Flags (Team Phoenix)", "path": "FeatureFlag/Filter?DepartmentId=285"},
    {"keyword": "parcel", "title": "Parcel", "path": "Parcel"},
    {"keyword": "pu", "title": "Packing Unit", "path": "PackingUnit"},
    {"keyword": "log", "title": "Packing Workflow Log", "path": "ui/Packing/PackingWorkflowLog", "id_path": None},
    {"keyword": "po", "title": "Packing Order", "path": "ui/Packing/PackingOrder", "id_path": "ui/Packing/PackingOrder/{id}"},
]
CONTROLLERS = {
    "sources": [],
    "controllers": [
        {"name": "Parcel", "path": "Parcel", "module": "Packing"},
        {"name": "Trolley", "path": "Trolley", "module": "Logistics"},
        {"name": "FeatureFlag", "path": "FeatureFlag", "module": "Core"},
        {"name": "PackingUnitHistory", "path": "PackingUnitHistory", "module": "Packing"},
    ],
}
PAGES = erp_pages_from(SHORTCUTS, CONTROLLERS)


def rows(query):
    return erp_rows(query.split(), PAGES)


def urls(result):
    return [row["arg"] for row in result]


class ErpPagesFromTest(unittest.TestCase):
    def test_controller_with_a_shortcut_path_is_not_listed_twice(self):
        self.assertEqual([page.keyword for page in PAGES.controllers], ["Trolley", "FeatureFlag", "PackingUnitHistory"])

    def test_controller_summary_mentions_module(self):
        self.assertIn("Logistics", PAGES.controllers[0].summary)

    def test_seeded_shortcut_file_is_valid(self):
        shortcuts = json.loads(ERP_PAGES_PATH.read_text(encoding="utf-8"))
        self.assertEqual(len({shortcut["keyword"] for shortcut in shortcuts}), 15)


class ErpRowsTest(unittest.TestCase):
    def test_empty_query_lists_shortcuts_and_a_controller_count_hint(self):
        result = rows("")
        self.assertEqual(len(result), len(SHORTCUTS) + 1)
        self.assertEqual(result[1]["arg"], "https://erp.digitecgalaxus.ch/en/Parcel")
        self.assertFalse(result[-1]["valid"])
        self.assertIn("3", result[-1]["title"])

    def test_parcel_with_id_lists_prod_test_dev(self):
        self.assertEqual(
            urls(rows("parcel 123456")),
            [
                "https://erp.digitecgalaxus.ch/en/Parcel/123456",
                "https://test-erp.digitecgalaxus.ch/en/Parcel/123456",
                "https://dev-erp.digitecgalaxus.ch/en/Parcel/123456",
            ],
        )

    def test_id_and_environment(self):
        self.assertEqual(urls(rows("pu 99 test")), ["https://test-erp.digitecgalaxus.ch/en/PackingUnit/99"])

    def test_exact_keyword_feat_opens_filter_and_ignores_id(self):
        self.assertEqual(rows("feat")[0]["arg"], "https://erp.digitecgalaxus.ch/en/FeatureFlag/Filter?DepartmentId=285")
        self.assertEqual(rows("feat 7")[0]["arg"], "https://erp.digitecgalaxus.ch/en/FeatureFlag/Filter?DepartmentId=285")

    def test_controller_with_id_on_eu(self):
        self.assertEqual(urls(rows("trolley 55 eu")), [
            "https://erp.galaxus.eu/en/Trolley/55",
            "https://test-erp.galaxus.eu/en/Trolley/55",
            "https://dev-erp.galaxus.eu/en/Trolley/55",
        ])

    def test_null_id_path_ignores_id(self):
        self.assertEqual(rows("log 5 prod")[0]["arg"], "https://erp.digitecgalaxus.ch/en/ui/Packing/PackingWorkflowLog")

    def test_explicit_id_path(self):
        self.assertEqual(rows("po 5 dev")[0]["arg"], "https://dev-erp.digitecgalaxus.ch/en/ui/Packing/PackingOrder/5")

    def test_shortcuts_rank_before_controllers(self):
        self.assertEqual([row["title"] for row in rows("packing")][:2], ["Packing Unit", "Packing Workflow Log"])
        self.assertEqual([row["title"] for row in rows("feature")], ["Feature Flags (Team Phoenix)", "FeatureFlag"])

    def test_candidates_carry_the_id_and_open_ch_prod(self):
        result = rows("unit 77")
        self.assertEqual(urls(result), ["https://erp.digitecgalaxus.ch/en/PackingUnit/77", "https://erp.digitecgalaxus.ch/en/PackingUnitHistory/77"])
        self.assertEqual(result[1]["autocomplete"], "PackingUnitHistory ")

    def test_missing_generated_file_is_a_regen_hint(self):
        with patch("dg.alfred_items.GENERATED_DIR", Path("/nonexistent")):
            result = rows_or_regen_hint(["parcel"], load_erp_pages, erp_rows)
        self.assertEqual(len(result), 1)
        self.assertIn("dg regen", result[0]["title"])


if __name__ == "__main__":
    unittest.main()
