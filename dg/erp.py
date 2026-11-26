import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, NamedTuple, Optional
from urllib.parse import quote

from dg.alfred_items import emit, hint_row, load_generated, query_tokens
from dg.selection import (
    Catalog,
    Link,
    Target,
    candidate_rows,
    classify_tokens,
    read_json,
    rows_or_regen_hint,
    select_rows,
    targets_in_order,
)

ERP_PAGES_PATH = Path(__file__).parent / "erp_pages.json"
ERP_TARGETS = targets_in_order(("prod", "test", "dev"), ("ch", "eu"))

ERP_HOSTS = {
    ("ch", "prod"): "erp.digitecgalaxus.ch",
    ("ch", "test"): "test-erp.digitecgalaxus.ch",
    ("ch", "dev"):  "dev-erp.digitecgalaxus.ch",
    ("eu", "prod"): "erp.galaxus.eu",
    ("eu", "test"): "test-erp.galaxus.eu",
    ("eu", "dev"):  "dev-erp.galaxus.eu",
}


def erp_base_url(target: Target) -> str:
    return "https://" + ERP_HOSTS[(target.mandator, target.environment)]


@dataclass(frozen=True)
class ErpPage:
    keyword: str
    title: str
    summary: str
    path: str
    id_path: Optional[str]


class ErpPages(NamedTuple):
    shortcuts: List[ErpPage]
    controllers: List[ErpPage]

    @property
    def all(self) -> List[ErpPage]:
        return self.shortcuts + self.controllers


def default_id_path(path) -> Optional[str]:
    return None if "?" in path else path + "/{id}"


def shortcut_page(shortcut) -> ErpPage:
    path = shortcut["path"]
    return ErpPage(
        keyword=shortcut["keyword"],
        title=shortcut["title"],
        summary=path,
        path=path,
        id_path=shortcut["id_path"] if "id_path" in shortcut else default_id_path(path),
    )


def controller_page(controller) -> ErpPage:
    return ErpPage(
        keyword=controller["name"],
        title=controller["name"],
        summary=f"{controller['module']} · {controller['path']}",
        path=controller["path"],
        id_path=default_id_path(controller["path"]),
    )


def erp_pages_from(shortcuts_data, controllers_data) -> ErpPages:
    shortcuts = [shortcut_page(shortcut) for shortcut in shortcuts_data]
    shortcut_paths = {page.path.lower() for page in shortcuts}
    controllers = [
        controller_page(controller)
        for controller in controllers_data["controllers"]
        if controller["path"].lower() not in shortcut_paths
    ]
    return ErpPages(shortcuts, controllers)


def erp_link(page: ErpPage, target: Target, remaining) -> Link:
    page_path = page.path
    if remaining and page.id_path:
        page_path = page.id_path.replace("{id}", quote(remaining[0], safe=""))
    return Link(f"{erp_base_url(target)}/en/{page_path}")


def erp_rows(tokens, pages: ErpPages):
    catalog = Catalog("ERP pages", pages.all, lambda _: ERP_TARGETS, erp_link, default_mandators=("ch",))
    if tokens:
        return select_rows(catalog, tokens)
    return candidate_rows(catalog, pages.shortcuts, classify_tokens([])) + [
        hint_row(
            f"Type a name to search {len(pages.controllers)} more ERP controllers",
            "Add an id, test/dev or eu to narrow, e.g. 'trolley 55 eu'",
        )
    ]


def load_erp_pages() -> ErpPages:
    return erp_pages_from(read_json(ERP_PAGES_PATH), load_generated("erp_controllers.json"))


def main():
    emit(rows_or_regen_hint(query_tokens(sys.argv), load_erp_pages, erp_rows))


if __name__ == "__main__":
    main()
