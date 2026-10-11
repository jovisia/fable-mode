#!/usr/bin/env python3
"""Validate every SKILL.md in a repo against the Agent Skills spec.

Rules (https://agentskills.io/specification):
  name         required, 1-64 chars, a-z 0-9 and hyphens, no leading/trailing
               hyphen, no "--", must match the skill's folder name
  description  required, 1-1024 chars, non-empty
  compatibility optional, 1-500 chars if present
Warnings (non-fatal): unknown frontmatter fields, body over 500 lines.
Also rejected: duplicate frontmatter keys, files that are not UTF-8 (a BOM is fine).

Note: the spec's name rule reads "unicode lowercase alphanumeric characters
(a-z, 0-9)". This validator enforces the ASCII a-z/0-9 set named in the
parentheses, so a name like "café" is rejected. Stricter than a unicode
reading on purpose: folder names must survive every filesystem and shell.

A SKILL.md at the repo root has no folder of its own; its expected name is the
target install.sh copies it to (cp "$HERE/SKILL.md" "$SK/<name>/SKILL.md"),
falling back to the repo directory name.

Usage: python3 scripts/validate_skills.py [REPO_DIR]   (exit 1 on any error)
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
KNOWN_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
ROOT_INSTALL_RE = re.compile(r'cp\s+"\$HERE/SKILL\.md"\s+"\$SK/([^/"]+)/SKILL\.md"')


@dataclass
class Result:
    path: Path
    name: str | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def find_skills(repo: Path) -> list[Path]:
    return sorted(p for p in repo.rglob("SKILL.md") if ".git" not in p.relative_to(repo).parts)


def root_install_name(repo: Path) -> str:
    install = repo / "install.sh"
    if install.is_file():
        m = ROOT_INSTALL_RE.search(install.read_text())
        if m:
            return m.group(1)
    return repo.resolve().name


class _UniqueKeyLoader(yaml.SafeLoader):
    """SafeLoader that rejects duplicate keys (plain YAML silently keeps the last)."""


def _construct_unique_mapping(loader, node, deep=False):
    seen = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise yaml.constructor.ConstructorError(
                None, None, f"duplicate key {key!r}", key_node.start_mark)
        seen.add(key)
    return loader.construct_mapping(node, deep=deep)


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping)


def split_frontmatter(text: str) -> tuple[str | None, str, str | None]:
    """Return (frontmatter, body, error). Delimiters must be '---' at column 0,
    so an indented '---' inside a block scalar does not close the frontmatter."""
    lines = text.splitlines()
    if not lines or lines[0].rstrip() != "---":
        return None, text, "no YAML frontmatter (file must start with '---')"
    for i, line in enumerate(lines[1:], start=1):
        if line.rstrip() == "---":
            return "\n".join(lines[1:i]), "\n".join(lines[i + 1:]), None
    return None, text, "frontmatter opened with '---' but never closed"


def validate_file(path: Path, expected_name: str) -> Result:
    r = Result(path)
    try:
        text = path.read_text(encoding="utf-8-sig")  # utf-8-sig strips a leading BOM
    except UnicodeDecodeError as e:
        r.errors.append(f"file is not valid UTF-8 (byte {e.start})")
        return r
    fm_text, body, err = split_frontmatter(text)
    if err:
        r.errors.append(err)
        return r
    try:
        fm = yaml.load(fm_text, Loader=_UniqueKeyLoader)  # noqa: S506 — SafeLoader subclass
    except yaml.YAMLError as e:
        problem = getattr(e, "problem", None) or str(e).splitlines()[0]
        r.errors.append(f"invalid YAML in frontmatter: {problem}")
        return r
    if not isinstance(fm, dict):
        r.errors.append("frontmatter is not a key/value mapping")
        return r

    name = fm.get("name")
    r.name = name if isinstance(name, str) else None
    if name is None:
        r.errors.append("missing required field: name")
    elif not isinstance(name, str):
        r.errors.append(f"name must be a string, got {type(name).__name__}")
    else:
        if not 1 <= len(name) <= 64:
            r.errors.append(f"name is {len(name)} chars (must be 1-64)")
        if not NAME_RE.match(name):
            r.errors.append(f"name {name!r} must be lowercase a-z, 0-9 and single hyphens, "
                            "not starting or ending with a hyphen")
        if name != expected_name:
            r.errors.append(f"name {name!r} does not match folder {expected_name!r}")

    desc = fm.get("description")
    if desc is None:
        r.errors.append("missing required field: description")
    elif not isinstance(desc, str) or not desc.strip():
        r.errors.append("description must be a non-empty string")
    elif len(desc) > 1024:
        r.errors.append(f"description is {len(desc)} chars (max 1024)")

    if "compatibility" in fm:
        comp = fm["compatibility"]
        if not isinstance(comp, str) or not 1 <= len(comp) <= 500:
            r.errors.append("compatibility must be a 1-500 char string")

    for key in sorted(set(fm) - KNOWN_FIELDS):
        r.warnings.append(f"unknown frontmatter field: {key}")
    body_lines = len(body.splitlines())
    if body_lines > 500:
        r.warnings.append(f"body is {body_lines} lines (spec recommends under 500)")
    return r


def validate_repo(repo: Path) -> list[Result]:
    repo = Path(repo)
    results = []
    for path in find_skills(repo):
        expected = root_install_name(repo) if path.parent == repo else path.parent.name
        results.append(validate_file(path, expected))
    return results


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    repo = Path(argv[0]) if argv else Path(__file__).resolve().parent.parent
    results = validate_repo(repo)
    if not results:
        print(f"No SKILL.md files found under {repo}")
        return 1
    failed = 0
    for r in results:
        rel = r.path.relative_to(repo)
        status = "FAIL" if r.errors else "PASS"
        failed += bool(r.errors)
        print(f"{status}  {rel}  (name: {r.name})")
        for e in r.errors:
            print(f"      error:   {e}")
        for w in r.warnings:
            print(f"      warning: {w}")
    print(f"\n{len(results)} skill(s) checked, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
