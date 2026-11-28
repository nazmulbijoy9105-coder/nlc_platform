#!/usr/bin/env python3
"""Strict structural validation for GitHub Actions workflow YAML files.

PyYAML's default SafeLoader silently accepts duplicate mapping keys. GitHub's
workflow parser does not treat a duplicate-key document as a reliable config,
so this gate rejects duplicates before checking the required top-level shape.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import yaml
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode


class UniqueKeySafeLoader(yaml.SafeLoader):
    """SafeLoader variant that rejects duplicate mapping keys at every depth."""


def _construct_unique_mapping(loader: UniqueKeySafeLoader, node: MappingNode, deep: bool = False):
    if not isinstance(node, MappingNode):
        raise ConstructorError(None, None, "expected a mapping node", node.start_mark)
    loader.flatten_mapping(node)
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in result
        except TypeError as exc:
            raise ConstructorError(
                "while constructing a mapping", node.start_mark,
                "found an unhashable mapping key", key_node.start_mark,
            ) from exc
        if duplicate:
            raise ConstructorError(
                "while constructing a mapping", node.start_mark,
                f"found duplicate key {key!r}", key_node.start_mark,
            )
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def validate_workflow(path: Path) -> list[str]:
    """Return validation errors for one workflow file; empty means valid."""
    try:
        with path.open("r", encoding="utf-8") as stream:
            document = yaml.load(stream, Loader=UniqueKeySafeLoader)
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        return [f"{path}: invalid YAML: {exc}"]

    if not isinstance(document, dict):
        return [f"{path}: workflow document must be a top-level mapping"]
    jobs = document.get("jobs")
    if not isinstance(jobs, dict):
        return [f"{path}: top-level 'jobs' must be a mapping"]
    if not jobs:
        return [f"{path}: top-level 'jobs' mapping must not be empty"]
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workflow-dir",
        type=Path,
        default=Path(".github/workflows"),
        help="directory containing GitHub Actions workflow YAML files",
    )
    args = parser.parse_args(argv)
    paths = sorted(
        path for path in (*args.workflow_dir.glob("*.yml"), *args.workflow_dir.glob("*.yaml"))
        if path.is_file()
    )
    if not paths:
        print(f"no workflow YAML files found in {args.workflow_dir}", file=sys.stderr)
        return 1

    errors = [error for path in paths for error in validate_workflow(path)]
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"validated {len(paths)} workflow YAML files (unique keys; top-level jobs mapping)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
