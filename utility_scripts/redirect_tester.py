#!/usr/bin/env python3
"""Redirect testing tool: validation only.

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlsplit


def _ensure_leading_slash(path: str) -> str:
    if not path.startswith("/"):
        return f"/{path}"
    return path


def _normalize_path(path: str) -> str:
    path = _ensure_leading_slash(path)
    if path != "/" and path.endswith("/"):
        return path[:-1]
    return path


def _strip_query_fragment(path: str) -> str:
    parts = urlsplit(path)
    return parts.path


def _load_redirects(path: str) -> List[Tuple[str, str]]:
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    redirects: List[Tuple[str, str]] = []
    if isinstance(data, dict):
        if isinstance(data.get("data"), list):
            for entry in data["data"]:
                if not isinstance(entry, dict):
                    continue
                src = entry.get("key") or entry.get("from") or entry.get("source") or entry.get("src")
                dst = entry.get("value") or entry.get("to") or entry.get("target") or entry.get("dest")
                if src is None or dst is None:
                    continue
                redirects.append((str(src), str(dst)))
        else:
            for src, dst in data.items():
                redirects.append((str(src), str(dst)))
    elif isinstance(data, list):
        for entry in data:
            if isinstance(entry, dict):
                src = entry.get("from") or entry.get("source") or entry.get("src")
                dst = entry.get("to") or entry.get("target") or entry.get("dest")
                if src is None or dst is None:
                    continue
                redirects.append((str(src), str(dst)))
            elif isinstance(entry, list) and len(entry) >= 2:
                redirects.append((str(entry[0]), str(entry[1])))
    return redirects


def _validate_redirects(
    redirects: List[Tuple[str, str]],
    mkdocs_site_dir: Optional[str],
    skip_static_check: bool,
) -> Tuple[int, Dict[str, object]]:
    failures: List[str] = []
    warnings: List[str] = []

    normalized: Dict[str, str] = {}
    for src, dst in redirects:
        src_norm = _normalize_path(_strip_query_fragment(src))
        if src_norm in normalized:
            failures.append(f"Duplicate redirect from {src_norm}")
        normalized[src_norm] = dst

    chains: List[str] = []
    loops: List[str] = []

    for src, dst in normalized.items():
        target_parts = urlsplit(dst)
        if target_parts.scheme:
            continue
        target_path = _normalize_path(target_parts.path)
        visited = [src]
        hop = 0
        current = target_path
        while current in normalized:
            hop += 1
            if current in visited:
                loops.append(" -> ".join(visited + [current]))
                break
            visited.append(current)
            current_parts = urlsplit(normalized[current])
            if current_parts.scheme:
                break
            current = _normalize_path(current_parts.path)
        if hop > 1:
            chains.append(" -> ".join(visited))

    if loops:
        failures.append(f"Redirect loops detected: {len(loops)}")
    if chains:
        failures.append(f"Redirect chains longer than 1 hop: {len(chains)}")

    site_dir = mkdocs_site_dir
    if not skip_static_check:
        if not site_dir:
            failures.append("Site dir is required unless --skip-static-check is set")
            site_dir = None
        elif not os.path.isdir(site_dir):
            failures.append(f"Site dir does not exist: {site_dir}")
            site_dir = None

    def check_target(path: str) -> None:
        target_parts = urlsplit(path)
        if target_parts.scheme:
            return
        target_path = target_parts.path

        if not site_dir:
            return

        if target_path.endswith("/"):
            candidate = os.path.join(site_dir, target_path.lstrip("/"), "index.html")
            if not os.path.isfile(candidate):
                failures.append(f"Missing target file: {candidate}")
        elif target_path.endswith(".html"):
            candidate = os.path.join(site_dir, target_path.lstrip("/"))
            if not os.path.isfile(candidate):
                failures.append(f"Missing target file: {candidate}")
        else:
            warnings.append(f"Target without trailing slash or .html: {target_path}")

    if not skip_static_check:
        for _, dst in redirects:
            check_target(dst)

    report = {
        "failures": failures,
        "warnings": warnings,
        "redirects": len(redirects),
        "chains": len(chains),
        "loops": len(loops),
    }

    print("Redirect validation summary")
    print(f"- redirects: {report['redirects']}")
    print(f"- failures: {len(failures)}")
    print(f"- warnings: {len(warnings)}")
    if failures:
        print("Failures:")
        for item in failures:
            print(f"  - {item}")
    if warnings:
        print("Warnings:")
        for item in warnings:
            print(f"  - {item}")
    if loops:
        print(f"- loops: {len(loops)}")
    if chains:
        print(f"- chains > 1 hop: {len(chains)}")
    if failures:
        return 1, report
    return 0, report


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Redirect tester")
    parser.add_argument(
        "--mkdocs-dir",
        default=os.getcwd(),
        help="Path to mkdocs repo directory (must contain redirects.json)",
    )
    parser.add_argument(
        "--site-dir",
        default="site",
        help="Site output directory relative to mkdocs dir",
    )
    parser.add_argument(
        "--skip-static-check",
        action="store_true",
        help="Only validate duplicates, loops, and chains",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Write JSON report to mkdocs dir and print its path",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)
    mkdocs_dir = os.path.abspath(args.mkdocs_dir)
    redirects_path = os.path.join(mkdocs_dir, "redirects.json")
    site_dir = args.site_dir
    if not os.path.isabs(site_dir):
        site_dir = os.path.join(mkdocs_dir, site_dir)

    if not os.path.isfile(redirects_path):
        print(f"Redirects file not found: {redirects_path}", file=sys.stderr)
        return 2

    redirects = _load_redirects(redirects_path)
    if not redirects:
        print("No redirects found.")

    exit_code, report = _validate_redirects(
        redirects=redirects,
        mkdocs_site_dir=site_dir,
        skip_static_check=args.skip_static_check,
    )

    if args.report:
        report_path = os.path.join(mkdocs_dir, "redirect_report.json")
        with open(report_path, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2)
        print(f"Report written to: {report_path}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
