import unittest

from dg.generate import (
    Controller,
    Deployment,
    Generation,
    Tdf,
    build_deployment,
    build_summary,
    devinite_controllers,
    merge_controllers,
    packing_website_controllers,
    parse_hostnames,
    parse_tdf,
    stale_overrides,
    values_files_by_folder,
)

XMP_VALUES_DEV = """# Default values for dg-module-host DEV.

appname: dg-packing-workflow-xmp
team: phoenix

httpRoute:
  hostnames:
    - dg-packing-workflow-xmp-eu.core.dev.int.devinite.com
  rules:
    - matches:
        - path:
            value: "/"
            type: PathPrefix
"""

UNIPACK_VALUES_PROD = """appname: dg-packing-workflow-unipack
httpRoute:
  hostnames:
    - dg-packing-workflow-unipack-ch.core.prod.int.devinite.com
    - dg-packing-workflow-unipack-eu.core.prod.int.devinite.com
  rules:
    - matches: []
"""

WEBSITE_VALUES_DEV = """spotSchedulable: false
autoscaling:
  enabled: false
"""

WEBSITE_VALUES = """# Default values for dg-module-host.
appname: dg-packing-website
team: phoenix
"""

WEBAPI_VALUES_TEST = """appname: dg-packing-webapi
# https://publicapi.core.test.pub.devinite.com/api/public/packing/v1/rea-carton-information
httpRoutePublic:
  enabled: true
"""

ODD_HOST_VALUES_TEST = """appname: dg-packing-odd
httpRoute:
  hostnames:
    - "packing.example.com"
"""

ETK_TDF = """using Dg.Something;

namespace Dg.Packing.TestDataFactory;

[ClassDisplay(
    Name = "ETK Packing Workflow",
    Description = "Creates packing units (Swiss Post parcel orders in Wohlen) for the products "
        + "batches to the ETK unloading station (count by TestCase), fill it in the ERP before calling.",
    TeamFilters = [TeamFilter.Phoenix]
)]
public class EtkTestDataFactory(
    IDbReadDeviniteDbo db
"""

MSA_TDF = """namespace Dg.Packing.TestDataFactory.ManualStorageArea;

[ClassDisplay(
    Name = "MSA Packing Workflow",
    Description = "Creates sales orders … "
        + "more text",
    TeamFilters = [TeamFilter.Phoenix]
)]
public class ManualStorageAreaPackingAvailableTestDataFactory(
"""


class ValuesFilesByFolderTest(unittest.TestCase):
    def test_keeps_only_values_files_directly_under_a_kubernetes_folder(self):
        tree = [
            "deploy/dg-packing-website/kubernetes/values.yaml",
            "deploy/dg-packing-website/kubernetes/values-dev.yaml",
            "deploy/dg-packing-website/kubernetes/templates/route.yaml",
            "deploy/database/Dockerfile",
            "deploy/dg-packing-kubernetesjobs/job/values-dev.yaml",
        ]
        self.assertEqual({"dg-packing-website": ["values-dev.yaml", "values.yaml"]}, values_files_by_folder(tree))


class ParseHostnamesTest(unittest.TestCase):
    def test_reads_only_the_hostnames_list(self):
        self.assertEqual(["dg-packing-workflow-xmp-eu.core.dev.int.devinite.com"], parse_hostnames(XMP_VALUES_DEV))

    def test_ignores_urls_in_comments(self):
        self.assertEqual([], parse_hostnames(WEBAPI_VALUES_TEST))


class BuildDeploymentTest(unittest.TestCase):
    def test_takes_appname_and_hosts_from_the_files(self):
        scan = build_deployment("dg-packing-workflow-xmp", {"values-dev.yaml": XMP_VALUES_DEV})
        expected = Deployment(
            "dg-packing-workflow-xmp",
            "dg-packing-workflow-xmp",
            {"eu": {"dev": "dg-packing-workflow-xmp-eu.core.dev.int.devinite.com"}},
        )
        self.assertEqual(expected, scan.deployment)
        self.assertEqual([], scan.warnings)

    def test_splits_ch_and_eu_hostnames_and_orders_environments(self):
        scan = build_deployment(
            "dg-packing-workflow-unipack",
            {"values-prod.yaml": UNIPACK_VALUES_PROD, "values-dev.yaml": UNIPACK_VALUES_PROD.replace(".prod.", ".dev.")},
        )
        self.assertEqual(
            {
                "ch": {
                    "dev": "dg-packing-workflow-unipack-ch.core.dev.int.devinite.com",
                    "prod": "dg-packing-workflow-unipack-ch.core.prod.int.devinite.com",
                },
                "eu": {
                    "dev": "dg-packing-workflow-unipack-eu.core.dev.int.devinite.com",
                    "prod": "dg-packing-workflow-unipack-eu.core.prod.int.devinite.com",
                },
            },
            scan.deployment.hosts,
        )
        self.assertEqual(["dev", "prod"], list(scan.deployment.hosts["ch"]))

    def test_falls_back_to_values_yaml_for_the_appname(self):
        scan = build_deployment("dg-packing-website", {"values-dev.yaml": WEBSITE_VALUES_DEV, "values.yaml": WEBSITE_VALUES})
        self.assertEqual(Deployment("dg-packing-website", "dg-packing-website", {}), scan.deployment)

    def test_falls_back_to_the_folder_name_without_any_appname(self):
        scan = build_deployment("external-secrets", {"values-dev.yaml": "secretStore:\n  name: x\n"})
        self.assertEqual("external-secrets", scan.deployment.appname)

    def test_keeps_a_hostname_that_does_not_fit_under_other_and_warns(self):
        scan = build_deployment("dg-packing-odd", {"values-test.yaml": ODD_HOST_VALUES_TEST})
        self.assertEqual({"other": {"test": "packing.example.com"}}, scan.deployment.hosts)
        self.assertEqual(1, len(scan.warnings))
        self.assertIn("packing.example.com", scan.warnings[0])


class ParseTdfTest(unittest.TestCase):
    def test_reads_name_and_full_name_across_a_multi_line_description(self):
        file = "src/Packing/Dg.Packing/TestDataFactory/EtkTestDataFactory.cs"
        self.assertEqual(
            Tdf("ETK Packing Workflow", "Dg.Packing.TestDataFactory.EtkTestDataFactory", file),
            parse_tdf(file, ETK_TDF),
        )

    def test_uses_the_nested_namespace(self):
        tdf = parse_tdf("x.cs", MSA_TDF)
        self.assertEqual("MSA Packing Workflow", tdf.name)
        self.assertEqual(
            "Dg.Packing.TestDataFactory.ManualStorageArea.ManualStorageAreaPackingAvailableTestDataFactory",
            tdf.factory_full_name,
        )

    def test_returns_none_without_class_display(self):
        self.assertIsNone(parse_tdf("x.cs", "namespace A;\n// TeamFilter.Phoenix\npublic class B {}\n"))


class ControllersTest(unittest.TestCase):
    def test_devinite_controllers_skip_api_controllers_and_take_the_module_after_src(self):
        paths = [
            "src/Packing/Dg.Packing/Parcels/ParcelController.cs",
            "src/Packing/Dg.Packing/Parcels/ParcelApiController.cs",
        ]
        self.assertEqual(
            [Controller("Parcel", "Parcel", "Packing", "src/Packing/Dg.Packing/Parcels/ParcelController.cs")],
            devinite_controllers(paths),
        )

    def test_packing_website_controllers_get_the_ui_route(self):
        path = "src/Dg.Packing.Website/Controller/Package/PackageController.cs"
        self.assertEqual(
            [Controller("Package", "ui/Packing/Package", "Dg.Packing.Website", path)],
            packing_website_controllers([path, "src/Dg.Packing.Website/Controller/Package/PackageViewModel.cs"]),
        )

    def test_merge_drops_a_duplicate_path_case_insensitively_keeping_the_first_file(self):
        first = Controller("Department", "Department", "HumanResources", "src/HumanResources/A/DepartmentController.cs")
        second = Controller("department", "department", "HumanResources", "src/HumanResources/B/departmentController.cs")
        parcel = Controller("Parcel", "Parcel", "Packing", "src/Packing/ParcelController.cs")
        merge = merge_controllers([second, parcel, first])
        self.assertEqual([first, parcel], merge.controllers)
        self.assertEqual([second], merge.dropped_duplicates)


class SummaryTest(unittest.TestCase):
    def generation(self):
        return Generation(
            deployments=[Deployment("dg-packing-workflow-atk2", "a", {}), Deployment("dg-packing-workflow-problemhandling", "p", {})],
            tdfs=[Tdf("ATK Packing Workflow", "Dg.Atk", "a.cs"), Tdf("MSA Packing Workflow", "Dg.Msa", "m.cs")],
            controllers=[Controller("A", "A", "M", "a"), Controller("B", "B", "M", "b"), Controller("C", "C", "M", "c")],
            warnings=[],
            dropped_controller_duplicates=[],
        )

    def test_first_run_shows_counts_only(self):
        summary = build_summary(self.generation(), {}, [], [])
        self.assertEqual("deploy 2 · tdf 2 · erp 3 · stale overrides: none", summary)

    def test_lists_added_and_removed_names_and_counts_controller_changes(self):
        previous = {
            "deployments.json": {"deployments": [{"folder": "dg-packing-workflow-atk2"}, {"folder": "dg-packing-workflow-gone"}]},
            "tdfs.json": {"tdfs": [{"name": "ATK Packing Workflow"}]},
            "erp_controllers.json": {"controllers": [{"path": "A"}, {"path": "Z"}]},
        }
        summary = build_summary(self.generation(), previous, ["Dg.Old"], ["devinite"])
        self.assertEqual(
            "deploy 2 (+dg-packing-workflow-problemhandling, −dg-packing-workflow-gone)"
            " · tdf 2 (+MSA Packing Workflow) · erp 3 (+2 −1) · stale overrides: Dg.Old"
            " · fetch failed: devinite (used existing ref)",
            summary,
        )

    def test_stale_overrides_names_keys_without_a_generated_entry(self):
        overrides = {
            "workflows": {"dg-packing-workflow-atk2": {}, "dg-packing-workflow-gone": {}},
            "extra_workflows": [{"keyword": "flow"}],
            "tdfs": {"Dg.Atk": {}, "Dg.CrossMandator": {}},
        }
        self.assertEqual(
            ["dg-packing-workflow-gone", "Dg.CrossMandator"],
            stale_overrides(overrides, ["dg-packing-workflow-atk2"], ["Dg.Atk"]),
        )


if __name__ == "__main__":
    unittest.main()
