import json
from pathlib import Path
from typing import Any, Callable, List, NamedTuple, Optional, Protocol, Sequence, Tuple

from dg.alfred_items import hint_row, url_row

OVERRIDES_PATH = Path(__file__).parent / "overrides.json"

ENVIRONMENTS = ("dev", "test", "prod")
MANDATORS = ("ch", "eu")
UNREADABLE_INPUT = (OSError, ValueError, KeyError)


class Selectable(Protocol):
    keyword: str
    title: str
    summary: str


class Target(NamedTuple):
    mandator: Optional[str]
    environment: str

    @property
    def label(self) -> str:
        if self.mandator is None:
            return self.environment.upper()
        return f"{self.mandator.upper()} {self.environment.upper()}"


class Narrowing(NamedTuple):
    environments: frozenset
    mandators: frozenset
    remaining: Tuple[str, ...]


class Query(NamedTuple):
    entry_token: Optional[str]
    narrowing: Narrowing


class Modifier(NamedTuple):
    subtitle: str
    url: str


class Link(NamedTuple):
    url: str
    subtitle: Optional[str] = None
    alt: Optional[Modifier] = None
    ctrl: Optional[Modifier] = None


class Catalog(NamedTuple):
    noun: str
    entries: Sequence[Selectable]
    targets: Callable[[Any], List[Target]]
    link: Callable[[Any, Target, Tuple[str, ...]], Link]
    default_mandators: Tuple[str, ...] = ()


def targets_in_order(environments, mandators) -> List[Target]:
    return [Target(mandator, environment) for environment in environments for mandator in mandators]


def classify_tokens(tokens) -> Narrowing:
    environments, mandators, remaining = set(), set(), []
    for token in tokens:
        lowered = token.lower()
        environment = next((env for env in ENVIRONMENTS if env.startswith(lowered)), None)
        if environment:
            environments.add(environment)
        elif lowered in MANDATORS:
            mandators.add(lowered)
        else:
            remaining.append(token)
    return Narrowing(frozenset(environments), frozenset(mandators), tuple(remaining))


def parse_query(tokens) -> Query:
    if not tokens:
        return Query(None, classify_tokens([]))
    return Query(tokens[0], classify_tokens(tokens[1:]))


def matching_entries(entries: Sequence[Selectable], entry_token: Optional[str]) -> List[Selectable]:
    if entry_token is None:
        return list(entries)
    needle = entry_token.lower()
    exact = [entry for entry in entries if entry.keyword.lower() == needle]
    return exact or [
        entry for entry in entries if needle in entry.keyword.lower() or needle in entry.title.lower()
    ]


def narrowed_targets(catalog: Catalog, entry, narrowing: Narrowing) -> List[Target]:
    mandators = narrowing.mandators or catalog.default_mandators
    return [
        target
        for target in catalog.targets(entry)
        if (not narrowing.environments or target.environment in narrowing.environments)
        and (target.mandator is None or not mandators or target.mandator in mandators)
    ]


def candidate_rows(catalog: Catalog, entries, narrowing: Narrowing):
    return [_candidate_row(catalog, entry, narrowing) for entry in entries]


def _candidate_row(catalog: Catalog, entry, narrowing: Narrowing):
    default_target = (narrowed_targets(catalog, entry, narrowing) or catalog.targets(entry))[0]
    link = catalog.link(entry, default_target, narrowing.remaining)
    return url_row(
        entry.title,
        link.url,
        subtitle=f"{entry.summary} · Enter: {default_target.label} · Tab: all targets",
        alt=link.alt,
        ctrl=link.ctrl,
        autocomplete=f"{entry.keyword} ",
    )


def target_rows(catalog: Catalog, entry, narrowing: Narrowing):
    targets = narrowed_targets(catalog, entry, narrowing)
    if not targets:
        available = ", ".join(target.label for target in catalog.targets(entry))
        return [hint_row(f"No target of {entry.title} matches", f"Available: {available}")]
    return [_target_row(catalog, entry, target, narrowing.remaining) for target in targets]


def _target_row(catalog: Catalog, entry, target: Target, remaining):
    link = catalog.link(entry, target, remaining)
    return url_row(
        f"{entry.title} - {target.label}",
        link.url,
        subtitle=link.subtitle,
        alt=link.alt,
        ctrl=link.ctrl,
    )


def select_rows(catalog: Catalog, tokens):
    query = parse_query(tokens)
    matches = matching_entries(catalog.entries, query.entry_token)
    if not matches:
        return [hint_row(f"No matching {catalog.noun}", "Try a different search term")]
    if query.entry_token is None or len(matches) > 1:
        return candidate_rows(catalog, matches, query.narrowing)
    return target_rows(catalog, matches[0], query.narrowing)


def read_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_overrides():
    return read_json(OVERRIDES_PATH)


def rows_or_regen_hint(tokens, load_entries, build_rows):
    try:
        entries = load_entries()
    except UNREADABLE_INPUT as error:
        return [hint_row("Data missing or unreadable - run the keyword 'dg regen'", str(error))]
    return build_rows(tokens, entries)
