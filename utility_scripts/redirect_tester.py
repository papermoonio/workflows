#!/usr/bin/env python3
"""Redirect testing tool: validation only.

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict, List, Optional, Set, Tuple
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
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Failed to load redirects from {path}: {exc}")

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
            continue
        normalized[src_norm] = dst

    next_map: Dict[str, Optional[str]] = {}
    for src, dst in normalized.items():
        target_parts = urlsplit(dst)
        if target_parts.scheme:
            next_map[src] = None
            continue
        target_path = _normalize_path(target_parts.path)
        next_map[src] = target_path if target_path in normalized else None

    state: Dict[str, int] = {}
    hop_count: Dict[str, int] = {}
    looped: Dict[str, bool] = {}

    def dfs_iterative(start: str) -> None:
        stack: List[Tuple[str, bool]] = [(start, False)]
        while stack:
            node, expanded = stack.pop()
            node_state = state.get(node, 0)
            if not expanded:
                if node_state == 2:
                    continue
                if node_state == 1:
                    looped[node] = True
                    hop_count[node] = 0
                    state[node] = 2
                    continue
                state[node] = 1
                stack.append((node, True))
                next_node = next_map.get(node)
                if next_node and state.get(next_node, 0) != 2:
                    stack.append((next_node, False))
            else:
                # If this node was already finalized as part of a loop
                # (detected during forward phase), preserve that state
                if state.get(node, 0) == 2:
                    continue

                next_node = next_map.get(node)
                if not next_node:
                    hop = 0
                    is_loop = False
                else:
                    next_state = state.get(next_node, 0)
                    if next_state == 1:
                        # next_node is still being visited - we're in a cycle
                        hop = 1
                        is_loop = True
                    elif next_state == 2:
                        # next_node is fully processed
                        hop = 1 + hop_count.get(next_node, 0)
                        is_loop = looped.get(next_node, False)
                    else:
                        # next_node was never visited (shouldn't happen in valid graph)
                        hop = 0
                        is_loop = False

                state[node] = 2
                hop_count[node] = hop
                looped[node] = is_loop

    for src in normalized.keys():
        dfs_iterative(src)

    loops_count = sum(1 for src in normalized.keys() if looped.get(src, False))
    chains_count = sum(
        1
        for src in normalized.keys()
        if hop_count.get(src, 0) > 1 and not looped.get(src, False)
    )

    if loops_count:
        failures.append(f"Redirect loops detected: {loops_count}")
    if chains_count:
        failures.append(f"Redirect chains longer than 1 hop: {chains_count}")

    site_dir = mkdocs_site_dir
    existing_files: Set[str] = set()
    if not skip_static_check:
        if not site_dir:
            failures.append("Site dir is required unless --skip-static-check is set")
            site_dir = None
        elif not os.path.isdir(site_dir):
            failures.append(f"Site dir does not exist: {site_dir}")
            site_dir = None
        else:
            # Normalize site_dir to absolute path for consistent comparisons
            site_dir = os.path.abspath(site_dir)
            # Pre-scan site directory to avoid repeated os.path.isfile calls.
            # Trade-off: Uses O(M) memory where M = number of files in site_dir.
            # For typical documentation sites (thousands of files), this is ~1-2 MB.
            # For extremely large sites, consider targeted os.path.exists checks instead.
            for root, _, files in os.walk(site_dir):
                for filename in files:
                    full_path = os.path.normpath(os.path.join(root, filename))
                    existing_files.add(full_path)

    def check_target(path: str) -> None:
        target_parts = urlsplit(path)
        if target_parts.scheme:
            return
        target_path = target_parts.path

        if not site_dir:
            return

        if target_path.endswith("/"):
            candidate = os.path.normpath(
                os.path.join(site_dir, target_path.lstrip("/"), "index.html")
            )
            if candidate not in existing_files:
                failures.append(f"Missing target file: {candidate}")
        elif target_path.endswith(".html"):
            candidate = os.path.normpath(
                os.path.join(site_dir, target_path.lstrip("/"))
            )
            if candidate not in existing_files:
                failures.append(f"Missing target file: {candidate}")
        else:
            warnings.append(f"Target without trailing slash or .html: {target_path}")

    def check_source_not_exists(path: str) -> None:
        """Verify that the redirect source does NOT exist in site (would be a conflict)."""
        if not site_dir:
            return

        # Use _ensure_leading_slash (not _normalize_path) to preserve trailing slash
        source_path = _ensure_leading_slash(urlsplit(path).path)
        
        if source_path.endswith("/"):
            candidate = os.path.normpath(
                os.path.join(site_dir, source_path.lstrip("/"), "index.html")
            )
        else:
            candidate = os.path.normpath(
                os.path.join(site_dir, source_path.lstrip("/"))
            )

        if candidate in existing_files:
            failures.append(f"Redirect source exists as file (conflict): {candidate}")

    if not skip_static_check:
        for src, dst in redirects:
            check_target(dst)
            check_source_not_exists(src)

    report = {
        "failures": failures,
        "warnings": warnings,
        "redirects_total": len(redirects),
        "redirects_unique": len(normalized),
        "chains": chains_count,
        "loops": loops_count,
    }

    print("Redirect validation summary")
    print(f"- redirects: {report['redirects_total']} (unique: {report['redirects_unique']})")
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
    if loops_count:
        print(f"- loops: {loops_count}")
    if chains_count:
        print(f"- chains > 1 hop: {chains_count}")
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
        return 0

    exit_code, report = _validate_redirects(
        redirects=redirects,
        mkdocs_site_dir=site_dir,
        skip_static_check=args.skip_static_check,
    )

    if args.report:
        report_path = os.path.join(mkdocs_dir, "redirect_report.json")
        try:
            with open(report_path, "w", encoding="utf-8") as handle:
                json.dump(report, handle, indent=2)
        except OSError as exc:
            print(f"Failed to write report to {report_path}: {exc}", file=sys.stderr)
            return 2
        else:
            print(f"Report written to: {report_path}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
