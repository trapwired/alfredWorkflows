from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, Iterable, List, NamedTuple, Optional

DG_DIR = Path(__file__).parent
GENERATED_DIR = DG_DIR / "generated"
OVERRIDES_FILE = DG_DIR / "overrides.json"

SOURCE_REF = "origin/master"
DEPLOYMENTS_FILE = "deployments.json"
TDFS_FILE = "tdfs.json"
ERP_CONTROLLERS_FILE = "erp_controllers.json"

ENVIRONMENT_ORDER = ("dev", "test", "prod")
UNMATCHED_MANDATOR = "other"
BASE_VALUES_ENVIRONMENT = "default"

VALUES_FILE = re.compile(r"^deploy/(?P<folder>[^/]+)/kubernetes/(?P<file>values[^/]*\.yaml)$")
VALUES_FILE_ENVIRONMENT = re.compile(r"^values-(?P<environment>[^.]+)\.yaml$")
APPNAME_LINE = re.compile(r"^appname:\s*(?P<value>\S.*)$", re.MULTILINE)
HOSTNAME = re.compile(r"^.+-(?P<mandator>ch|eu)\.core\.(?P<environment>dev|test|prod)\.int\.devinite\.com$")

NAMESPACE = re.compile(r"^\s*namespace\s+(?P<namespace>[\w.]+)", re.MULTILINE)
CLASS_DISPLAY = re.compile(r"\[ClassDisplay\((?P<arguments>.*?)\)\]", re.DOTALL)
DISPLAY_NAME = re.compile(r'\bName\s*=\s*"(?P<name>(?:[^"\\]|\\.)*)"')
CLASS_DECLARATION = re.compile(r"\bclass\s+(?P<class_name>\w+)")

TDF_MARKER = "TeamFilter.Phoenix"
ERP_CONTROLLER_MARKERS = (": ErpController", "ControllerApplication.Erp")
CONTROLLER_SUFFIX = "Controller.cs"
API_CONTROLLER_SUFFIX = "ApiController.cs"
PACKING_WEBSITE_MODULE = "Dg.Packing.Website"
PACKING_WEBSITE_CONTROLLER_DIR = "src/Dg.Packing.Website/Controller/"
PACKING_WEBSITE_ROUTE_PREFIX = "ui/Packing/"


class Clone(NamedTuple):
    repo: str
    path: Path


PACKING_CLONE = Clone("Dg.Packing", Path.home() / "dev" / "Dg.Packing")
DEVINITE_CLONE = Clone("devinite", Path.home() / "dev" / "devinite")


class Source(NamedTuple):
    repo: str
    commit: str

    def to_json(self) -> dict:
        return {"repo": self.repo, "ref": SOURCE_REF, "commit": self.commit}


class HostSlot(NamedTuple):
    mandator: str
    environment: str


class Deployment(NamedTuple):
    folder: str
    appname: str
    hosts: Dict[str, Dict[str, str]]

    def to_json(self) -> dict:
        return {"folder": self.folder, "appname": self.appname, "hosts": self.hosts}


class DeploymentScan(NamedTuple):
    deployment: Deployment
    warnings: List[str]


class Tdf(NamedTuple):
    name: str
    factory_full_name: str
    file: str

    def to_json(self) -> dict:
        return {"name": self.name, "factory_full_name": self.factory_full_name, "file": self.file}


class TdfScan(NamedTuple):
    tdfs: List[Tdf]
    unparsed_files: List[str]


class Controller(NamedTuple):
    name: str
    path: str
    module: str
    file: str

    def to_json(self) -> dict:
        return {"name": self.name, "path": self.path, "module": self.module}


class ControllerMerge(NamedTuple):
    controllers: List[Controller]
    dropped_duplicates: List[Controller]


class Generation(NamedTuple):
    deployments: List[Deployment]
    tdfs: List[Tdf]
    controllers: List[Controller]
    warnings: List[str]
    dropped_controller_duplicates: List[Controller]


def values_files_by_folder(tree_paths: Iterable[str]) -> Dict[str, List[str]]:
    folders: Dict[str, List[str]] = {}
    for tree_path in tree_paths:
        match = VALUES_FILE.match(tree_path)
        if match:
            folders.setdefault(match["folder"], []).append(match["file"])
    return {folder: sorted(files) for folder, files in folders.items()}


def yaml_scalar(raw: str) -> str:
    value = raw.split(" #", 1)[0].strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def parse_appname(values_text: str) -> Optional[str]:
    match = APPNAME_LINE.search(values_text)
    return yaml_scalar(match["value"]) if match else None


def indentation(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def parse_hostnames(values_text: str) -> List[str]:
    hostnames = []
    list_indent = None
    for line in values_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped == "hostnames:":
            list_indent = indentation(line)
        elif list_indent is not None and stripped.startswith("- ") and indentation(line) >= list_indent:
            hostnames.append(yaml_scalar(stripped[2:]))
        else:
            list_indent = None
    return hostnames


def classify_hostname(hostname: str) -> Optional[HostSlot]:
    match = HOSTNAME.match(hostname)
    return HostSlot(match["mandator"], match["environment"]) if match else None


def values_file_environment(file_name: str) -> str:
    match = VALUES_FILE_ENVIRONMENT.match(file_name)
    return match["environment"] if match else BASE_VALUES_ENVIRONMENT


def resolve_appname(folder: str, values_texts: Dict[str, str]) -> str:
    for file_name in ("values-dev.yaml", "values.yaml"):
        appname = parse_appname(values_texts.get(file_name, ""))
        if appname:
            return appname
    return folder


def environment_sort_key(environment: str):
    if environment in ENVIRONMENT_ORDER:
        return 0, ENVIRONMENT_ORDER.index(environment), ""
    return 1, 0, environment


def ordered_hosts(hosts: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    return {
        mandator: {env: hosts[mandator][env] for env in sorted(hosts[mandator], key=environment_sort_key)}
        for mandator in sorted(hosts)
    }


def build_deployment(folder: str, values_texts: Dict[str, str]) -> DeploymentScan:
    hosts: Dict[str, Dict[str, str]] = {}
    warnings = []
    for file_name in sorted(values_texts):
        for hostname in parse_hostnames(values_texts[file_name]):
            slot = classify_hostname(hostname)
            if slot is None:
                slot = HostSlot(UNMATCHED_MANDATOR, values_file_environment(file_name))
                warnings.append(f"{folder}/{file_name}: hostname {hostname} does not fit the pattern, kept under '{UNMATCHED_MANDATOR}'")
            existing = hosts.setdefault(slot.mandator, {}).get(slot.environment)
            if existing is None:
                hosts[slot.mandator][slot.environment] = hostname
            elif existing != hostname:
                warnings.append(f"{folder}/{file_name}: second hostname {hostname} for {slot.mandator}/{slot.environment} ignored, kept {existing}")
    deployment = Deployment(folder, resolve_appname(folder, values_texts), ordered_hosts(hosts))
    return DeploymentScan(deployment, warnings)


def parse_tdf(file: str, text: str) -> Optional[Tdf]:
    namespace = NAMESPACE.search(text)
    class_display = CLASS_DISPLAY.search(text)
    if not namespace or not class_display:
        return None
    display_name = DISPLAY_NAME.search(class_display["arguments"])
    class_declaration = CLASS_DECLARATION.search(text, class_display.end())
    if not display_name or not class_declaration:
        return None
    factory_full_name = namespace["namespace"] + "." + class_declaration["class_name"]
    return Tdf(display_name["name"], factory_full_name, file)


def file_name_of(path: str) -> str:
    return path.rsplit("/", 1)[-1]


def controller_name(path: str) -> str:
    return file_name_of(path)[: -len(CONTROLLER_SUFFIX)]


def is_erp_controller_file(path: str) -> bool:
    file_name = file_name_of(path)
    return file_name.endswith(CONTROLLER_SUFFIX) and not file_name.endswith(API_CONTROLLER_SUFFIX)


def module_after_src(path: str) -> str:
    segments = path.split("/")
    return segments[segments.index("src") + 1]


def devinite_controllers(paths: Iterable[str]) -> List[Controller]:
    return [
        Controller(controller_name(path), controller_name(path), module_after_src(path), path)
        for path in paths
        if is_erp_controller_file(path)
    ]


def packing_website_controllers(paths: Iterable[str]) -> List[Controller]:
    return [
        Controller(controller_name(path), PACKING_WEBSITE_ROUTE_PREFIX + controller_name(path), PACKING_WEBSITE_MODULE, path)
        for path in paths
        if path.startswith(PACKING_WEBSITE_CONTROLLER_DIR) and is_erp_controller_file(path)
    ]


def merge_controllers(controllers: Iterable[Controller]) -> ControllerMerge:
    kept: Dict[str, Controller] = {}
    dropped = []
    for controller in sorted(controllers, key=lambda c: c.file):
        route_key = controller.path.lower()
        if route_key in kept:
            dropped.append(controller)
        else:
            kept[route_key] = controller
    return ControllerMerge(sorted(kept.values(), key=lambda c: (c.name, c.path)), dropped)


def describe_change(label: str, previous: Optional[Iterable[str]], current: Iterable[str], names_listed: bool) -> str:
    current_set = set(current)
    headline = f"{label} {len(current_set)}"
    if previous is None:
        return headline
    previous_set = set(previous)
    added = sorted(current_set - previous_set)
    removed = sorted(previous_set - current_set)
    if names_listed:
        changes = ", ".join(["+" + name for name in added] + ["−" + name for name in removed])
    else:
        counts = []
        if added:
            counts.append(f"+{len(added)}")
        if removed:
            counts.append(f"−{len(removed)}")
        changes = " ".join(counts)
    return f"{headline} ({changes})" if changes else headline


def stale_overrides(overrides: dict, deployment_folders: Iterable[str], factory_full_names: Iterable[str]) -> List[str]:
    stale_workflows = set(overrides.get("workflows", {})) - set(deployment_folders)
    stale_tdfs = set(overrides.get("tdfs", {})) - set(factory_full_names)
    return sorted(stale_workflows) + sorted(stale_tdfs)


def previous_entry_keys(document: Optional[dict], list_key: str, entry_key: str) -> Optional[List[str]]:
    return None if document is None else [entry[entry_key] for entry in document.get(list_key, [])]


def build_summary(
    generation: Generation,
    previous_documents: Dict[str, Optional[dict]],
    stale: List[str],
    failed_fetches: List[str],
) -> str:
    previous_folders = previous_entry_keys(previous_documents.get(DEPLOYMENTS_FILE), "deployments", "folder")
    previous_tdf_names = previous_entry_keys(previous_documents.get(TDFS_FILE), "tdfs", "name")
    previous_routes = previous_entry_keys(previous_documents.get(ERP_CONTROLLERS_FILE), "controllers", "path")
    parts = [
        describe_change("deploy", previous_folders, [d.folder for d in generation.deployments], names_listed=True),
        describe_change("tdf", previous_tdf_names, [t.name for t in generation.tdfs], names_listed=True),
        describe_change("erp", previous_routes, [c.path for c in generation.controllers], names_listed=False),
        "stale overrides: " + (", ".join(stale) if stale else "none"),
    ]
    if failed_fetches:
        parts.append("fetch failed: " + ", ".join(failed_fetches) + " (used existing ref)")
    if generation.warnings:
        parts.append(f"warnings {len(generation.warnings)} (see stderr)")
    return " · ".join(parts)


def git(clone: Clone, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(clone.path), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},  # a credential prompt would hang the Alfred run
    ).stdout


def fetch_succeeds(clone: Clone) -> bool:
    try:
        git(clone, "fetch", "-q", "origin", "master")
        return True
    except subprocess.CalledProcessError:
        return False


def read_source(clone: Clone) -> Source:
    return Source(clone.repo, git(clone, "rev-parse", SOURCE_REF).strip())


def list_tree(clone: Clone, path: str) -> List[str]:
    return git(clone, "ls-tree", "-r", "--name-only", SOURCE_REF, path).splitlines()


def show_file(clone: Clone, path: str) -> str:
    return git(clone, "show", f"{SOURCE_REF}:{path}")


def files_containing(clone: Clone, text: str, pathspec: str) -> List[str]:
    try:
        output = git(clone, "grep", "-l", "-F", text, SOURCE_REF, "--", pathspec)
    except subprocess.CalledProcessError as error:
        if error.returncode == 1:  # git grep exits 1 when nothing matches
            return []
        raise
    ref_prefix = SOURCE_REF + ":"
    return [line[len(ref_prefix):] for line in output.splitlines()]


def collect_deployments(clone: Clone) -> List[DeploymentScan]:
    folders = values_files_by_folder(list_tree(clone, "deploy"))
    return [
        build_deployment(folder, {file_name: show_file(clone, f"deploy/{folder}/kubernetes/{file_name}") for file_name in files})
        for folder, files in sorted(folders.items())
    ]


def collect_tdfs(clone: Clone) -> TdfScan:
    tdfs = []
    unparsed_files = []
    for path in sorted(files_containing(clone, TDF_MARKER, "*.cs")):
        tdf = parse_tdf(path, show_file(clone, path))
        if tdf is None:
            unparsed_files.append(path)
        else:
            tdfs.append(tdf)
    return TdfScan(sorted(tdfs, key=lambda t: (t.name, t.factory_full_name)), unparsed_files)


def collect_controllers(devinite: Clone, packing: Clone) -> ControllerMerge:
    devinite_files = set()
    for marker in ERP_CONTROLLER_MARKERS:
        devinite_files.update(files_containing(devinite, marker, "*" + CONTROLLER_SUFFIX))
    website_files = list_tree(packing, PACKING_WEBSITE_CONTROLLER_DIR)
    return merge_controllers(devinite_controllers(devinite_files) + packing_website_controllers(website_files))


def generate(devinite: Clone, packing: Clone) -> Generation:
    deployment_scans = collect_deployments(packing)
    tdf_scan = collect_tdfs(devinite)
    controller_merge = collect_controllers(devinite, packing)
    warnings = [warning for scan in deployment_scans for warning in scan.warnings]
    warnings += [f"{path}: contains {TDF_MARKER} but its ClassDisplay Name, namespace or class did not parse" for path in tdf_scan.unparsed_files]
    return Generation(
        [scan.deployment for scan in deployment_scans],
        tdf_scan.tdfs,
        controller_merge.controllers,
        warnings,
        controller_merge.dropped_duplicates,
    )


def generated_documents(generation: Generation, devinite: Source, packing: Source) -> Dict[str, dict]:
    return {
        DEPLOYMENTS_FILE: {
            "source": packing.to_json(),
            "deployments": [deployment.to_json() for deployment in generation.deployments],
        },
        TDFS_FILE: {
            "source": devinite.to_json(),
            "tdfs": [tdf.to_json() for tdf in generation.tdfs],
        },
        ERP_CONTROLLERS_FILE: {
            "sources": [devinite.to_json(), packing.to_json()],
            "controllers": [controller.to_json() for controller in generation.controllers],
        },
    }


def read_json(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_generated(file_name: str, document: dict) -> None:
    GENERATED_DIR.mkdir(exist_ok=True)
    text = json.dumps(document, indent=2, ensure_ascii=False) + "\n"
    (GENERATED_DIR / file_name).write_text(text, encoding="utf-8")


def report_to_stderr(generation: Generation) -> None:
    for warning in generation.warnings:
        print("warning: " + warning, file=sys.stderr)
    for controller in generation.dropped_controller_duplicates:
        print(f"dropped duplicate controller path {controller.path}: {controller.file}", file=sys.stderr)


def failure_reason(error: Exception) -> str:
    details = (getattr(error, "stderr", None) or str(error)).strip().splitlines()
    return details[0] if details else type(error).__name__


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Generate the dg Alfred lists from Dg.Packing and devinite origin/master.")
    parser.add_argument("--no-fetch", action="store_true", help="use the existing origin/master refs")
    args = parser.parse_args(argv)
    try:
        print(regenerate(args.no_fetch))
    except (subprocess.CalledProcessError, OSError, ValueError) as error:
        # stdout is the Alfred notification, so a failed run says so there instead of ending silently.
        print("dg regen failed, lists unchanged: " + failure_reason(error))
        sys.exit(1)


def regenerate(no_fetch: bool) -> str:
    clones = (DEVINITE_CLONE, PACKING_CLONE)
    failed_fetches = [] if no_fetch else [clone.repo for clone in clones if not fetch_succeeds(clone)]
    generation = generate(DEVINITE_CLONE, PACKING_CLONE)
    documents = generated_documents(generation, read_source(DEVINITE_CLONE), read_source(PACKING_CLONE))

    previous_documents = {file_name: read_json(GENERATED_DIR / file_name) for file_name in documents}
    for file_name, document in documents.items():
        write_generated(file_name, document)

    stale = stale_overrides(
        read_json(OVERRIDES_FILE) or {},
        [deployment.folder for deployment in generation.deployments],
        [tdf.factory_full_name for tdf in generation.tdfs],
    )
    report_to_stderr(generation)
    return build_summary(generation, previous_documents, stale, failed_fetches)


if __name__ == "__main__":
    main()
