import sys
from dataclasses import dataclass
from typing import List, Optional

from dg.alfred_items import datadog_logs_url, emit, load_generated, query_tokens
from dg.selection import Catalog, Link, Modifier, Target, rows_or_regen_hint, select_rows, targets_in_order

DEPLOYMENT_FOLDER_PREFIX = "dg-packing-"
DEPLOYMENT_TARGETS = targets_in_order(("prod", "test", "dev"), (None,))

ERROR_STATUS = "status:(error OR critical OR alert OR emergency)"
WARN_STATUS = "status:warn"
STATUS_FILTERS = {
    "info": "status:info",
    "warn": WARN_STATUS,
    "crit": ERROR_STATUS,
    "error": ERROR_STATUS,
}


@dataclass(frozen=True)
class Deployment:
    keyword: str
    title: str
    appname: str

    @property
    def summary(self) -> str:
        return self.appname


def kube_deployment_query(appname) -> str:
    return f"kube_deployment:{appname}*"


def logs_query(base_query, environment, status_filter: Optional[str] = None) -> str:
    parts = [base_query, f"env:{environment}"] + ([status_filter] if status_filter else [])
    return " ".join(parts)


def deployments_from(deployments_data) -> List[Deployment]:
    return [
        Deployment(
            keyword=deployment["folder"].removeprefix(DEPLOYMENT_FOLDER_PREFIX),
            title=deployment["folder"],
            appname=deployment["appname"],
        )
        for deployment in deployments_data["deployments"]
    ]


def status_filter_in(remaining) -> Optional[str]:
    return next((STATUS_FILTERS[token.lower()] for token in remaining if token.lower() in STATUS_FILTERS), None)


def logs_modifier(label, query) -> Modifier:
    return Modifier(f"{label}: {query}", datadog_logs_url(query))


def deployment_link(deployment: Deployment, target: Target, remaining) -> Link:
    base_query = kube_deployment_query(deployment.appname)
    status_filter = status_filter_in(remaining)
    query = logs_query(base_query, target.environment, status_filter)
    if status_filter:
        return Link(datadog_logs_url(query), subtitle=query)
    return Link(
        datadog_logs_url(query),
        subtitle=query,
        alt=logs_modifier("Errors only", logs_query(base_query, target.environment, ERROR_STATUS)),
        ctrl=logs_modifier("Warnings only", logs_query(base_query, target.environment, WARN_STATUS)),
    )


def deploy_rows(tokens, deployments: List[Deployment]):
    catalog = Catalog("deployments", deployments, lambda _: DEPLOYMENT_TARGETS, deployment_link)
    return select_rows(catalog, tokens)


def load_deployments() -> List[Deployment]:
    return deployments_from(load_generated("deployments.json"))


def main():
    emit(rows_or_regen_hint(query_tokens(sys.argv), load_deployments, deploy_rows))


if __name__ == "__main__":
    main()
