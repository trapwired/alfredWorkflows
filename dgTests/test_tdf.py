import unittest
from pathlib import Path
from unittest.mock import patch

from dg.selection import rows_or_regen_hint
from dg.tdf import factories_from, load_factories, tdf_rows

TDFS = {
    "source": {},
    "tdfs": [
        {
            "name": "ATK Packing Workflow",
            "factory_full_name": "Dg.Packing.TestDataFactory.AtkTestDataFactory",
            "file": "AtkTestDataFactory.cs",
        },
        {
            "name": "ETK Packing Workflow",
            "factory_full_name": "Dg.Packing.TestDataFactory.EtkTestDataFactory",
            "file": "EtkTestDataFactory.cs",
        },
        {
            "name": "CrossMandator Packing workflow (XMP)",
            "factory_full_name": "Dg.Packing.TestDataFactory.CrossMandator.CrossMandatorPackingAvailableTestDataFactory",
            "file": "CrossMandatorPackingAvailableTestDataFactory.cs",
        },
    ],
}
OVERRIDES = {"tdfs": {"Dg.Packing.TestDataFactory.CrossMandator.CrossMandatorPackingAvailableTestDataFactory": {"keyword": "xmp"}}}

FACTORIES = factories_from(TDFS, OVERRIDES)
ATK_URL = "/de/TestData/ConfigureDataFactory?factoryFullName=Dg.Packing.TestDataFactory.AtkTestDataFactory"


def rows(query):
    return tdf_rows(query.split(), FACTORIES)


def titles(result):
    return [row["title"] for row in result]


class TestDataFactoriesFromTest(unittest.TestCase):
    def test_keyword_is_derived_from_class_name_without_override(self):
        self.assertEqual([factory.keyword for factory in FACTORIES], ["atk", "etk", "xmp", "alltdf"])


class TdfRowsTest(unittest.TestCase):
    def test_empty_query_lists_all_including_overview_opening_ch_dev(self):
        result = rows("")
        self.assertEqual(titles(result)[-1], "All Test Data Factories")
        self.assertEqual(result[0]["arg"], "https://dev-erp.digitecgalaxus.ch" + ATK_URL)
        self.assertEqual(result[0]["autocomplete"], "atk ")

    def test_exact_keyword_wins_over_substring(self):
        self.assertEqual(len(rows("atk")), 4)
        self.assertEqual(titles(rows("packing")), ["ATK Packing Workflow", "ETK Packing Workflow", "CrossMandator Packing workflow (XMP)"])

    def test_single_match_lists_dev_and_test_for_ch_and_eu(self):
        self.assertEqual(
            [row["arg"] for row in rows("atk")],
            [
                "https://dev-erp.digitecgalaxus.ch" + ATK_URL,
                "https://dev-erp.galaxus.eu" + ATK_URL,
                "https://test-erp.digitecgalaxus.ch" + ATK_URL,
                "https://test-erp.galaxus.eu" + ATK_URL,
            ],
        )

    def test_environment_and_mandator_narrow_targets(self):
        self.assertEqual(titles(rows("atk te eu")), ["ATK Packing Workflow - EU TEST"])

    def test_prod_is_not_a_target(self):
        self.assertFalse(rows("atk prod")[0]["valid"])

    def test_overview_links_to_test_data_page(self):
        self.assertEqual(rows("alltdf test ch")[0]["arg"], "https://test-erp.digitecgalaxus.ch/de/TestData")

    def test_cmd_copies_the_url(self):
        row = rows("atk dev ch")[0]
        self.assertEqual(row["mods"]["cmd"]["arg"], row["arg"])

    def test_missing_generated_file_is_a_regen_hint(self):
        with patch("dg.alfred_items.GENERATED_DIR", Path("/nonexistent")):
            result = rows_or_regen_hint(["atk"], load_factories, tdf_rows)
        self.assertEqual(len(result), 1)
        self.assertIn("dg regen", result[0]["title"])


if __name__ == "__main__":
    unittest.main()
