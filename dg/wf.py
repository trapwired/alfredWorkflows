import sys
from dataclasses import dataclass
from typing import Dict, List

from dg.alfred_items import emit, load_generated, query_tokens
from dg.deploy import kube_deployment_query, logs_modifier, logs_query
from dg.selection import (
    ENVIRONMENTS,
    MANDATORS,
    Catalog,
    Link,
    Target,
    load_overrides,
    rows_or_regen_hint,
    select_rows,
)

WORKFLOW_FOLDER_PREFIX = "dg-packing-workflow-"
SHORT_NAME_PREFIXES = (WORKFLOW_FOLDER_PREFIX, "dg-packing-")


@dataclass(frozen=True)
class Workflow:
    keyword: str
    title: str
    appname: str
    hosts: Dict[str, Dict[str, str]]
    path: str
    datadog_query: str

    @property
    def summary(self) -> str:
        return self.appname


def short_name(folder) -> str:
    prefix = next((prefix for prefix in SHORT_NAME_PREFIXES if folder.startswith(prefix)), "")
    return folder[len(prefix):]


def title_from(name) -> str:
    return " ".join(word.capitalize() for word in name.split("-"))


def build_workflow(keyword, title, appname, hosts, settings) -> Workflow:
    return Workflow(
        keyword=keyword,
        title=title,
        appname=appname,
        hosts=hosts,
        path=settings.get("path", ""),
        datadog_query=settings.get("datadog_query") or kube_deployment_query(appname),
    )


def workflow_from_deployment(deployment, override) -> Workflow:
    name = short_name(deployment["folder"])
    return build_workflow(
        keyword=override.get("keyword", name.replace("-", "")),
        title=override.get("title", title_from(name)),
        appname=deployment["appname"],
        hosts=deployment["hosts"],
        settings=override,
    )


def workflows_from(deployments_data, overrides) -> List[Workflow]:
    workflow_overrides = overrides.get("workflows", {})
    from_deployments = [
        workflow_from_deployment(deployment, workflow_overrides.get(deployment["folder"], {}))
        for deployment in deployments_data["deployments"]
        if deployment["folder"].startswith(WORKFLOW_FOLDER_PREFIX) or deployment["folder"] in workflow_overrides
    ]
    extras = [
        build_workflow(extra["keyword"], extra["title"], extra["appname"], extra["hosts"], extra)
        for extra in overrides.get("extra_workflows", [])
    ]
    return [workflow for workflow in from_deployments + extras if workflow_targets(workflow)]


def ordered_mandators(hosts) -> List[str]:
    return [mandator for mandator in MANDATORS if mandator in hosts] + sorted(set(hosts) - set(MANDATORS))


def workflow_targets(workflow: Workflow) -> List[Target]:
    return [
        Target(mandator, environment)
        for environment in ENVIRONMENTS
        for mandator in ordered_mandators(workflow.hosts)
        if workflow.hosts[mandator].get(environment)
    ]


def workflow_link(workflow: Workflow, target: Target, remaining) -> Link:
    query = logs_query(workflow.datadog_query, target.environment)
    return Link(
        f"https://{workflow.hosts[target.mandator][target.environment]}{workflow.path}",
        alt=logs_modifier("Datadog logs", query),
    )


def workflow_rows(tokens, workflows: List[Workflow]):
    return select_rows(Catalog("workflows", workflows, workflow_targets, workflow_link), tokens)


def load_workflows() -> List[Workflow]:
    return workflows_from(load_generated("deployments.json"), load_overrides())


def main():
    emit(rows_or_regen_hint(query_tokens(sys.argv), load_workflows, workflow_rows))


if __name__ == "__main__":
    main()
