import sys
from dataclasses import dataclass
from typing import List, Optional

from dg.alfred_items import emit, load_generated, query_tokens
from dg.erp import erp_base_url
from dg.selection import Catalog, Link, Target, load_overrides, rows_or_regen_hint, select_rows, targets_in_order

TDF_TARGETS = targets_in_order(("dev", "test"), ("ch", "eu"))
TDF_CLASS_SUFFIX = "TestDataFactory"


@dataclass(frozen=True)
class TestDataFactory:
    keyword: str
    title: str
    factory_full_name: Optional[str]

    @property
    def summary(self) -> str:
        return self.factory_full_name.rsplit(".", 1)[-1] if self.factory_full_name else "TestData overview"


ALL_TEST_DATA_FACTORIES = TestDataFactory("alltdf", "All Test Data Factories", None)


def derived_keyword(factory_full_name) -> str:
    class_name = factory_full_name.rsplit(".", 1)[-1]
    return class_name.removesuffix(TDF_CLASS_SUFFIX).lower()


def factories_from(tdfs_data, overrides) -> List[TestDataFactory]:
    tdf_overrides = overrides.get("tdfs", {})
    factories = []
    for tdf in tdfs_data["tdfs"]:
        full_name = tdf["factory_full_name"]
        override = tdf_overrides.get(full_name, {})
        factories.append(
            TestDataFactory(
                keyword=override.get("keyword", derived_keyword(full_name)),
                title=override.get("title", tdf["name"]),
                factory_full_name=full_name,
            )
        )
    return factories + [ALL_TEST_DATA_FACTORIES]


def tdf_link(factory: TestDataFactory, target: Target, remaining) -> Link:
    url = f"{erp_base_url(target)}/de/TestData"
    if factory.factory_full_name:
        url += f"/ConfigureDataFactory?factoryFullName={factory.factory_full_name}"
    return Link(url)


def tdf_rows(tokens, factories: List[TestDataFactory]):
    return select_rows(Catalog("test data factories", factories, lambda _: TDF_TARGETS, tdf_link), tokens)


def load_factories() -> List[TestDataFactory]:
    return factories_from(load_generated("tdfs.json"), load_overrides())


def main():
    emit(rows_or_regen_hint(query_tokens(sys.argv), load_factories, tdf_rows))


if __name__ == "__main__":
    main()
