#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests"]
# ///
"""Copy nested parent+child Solr documents (including RisReport) to another core.

Reads Category:parent blocks from Solr 7 with [child] and posts them as
_childDocuments_ trees to Solr 10. Resume by saving the Solr cursorMark.

Examples:
  uv run crawler/copy_solr_nested.py --limit 50
  uv run crawler/copy_solr_nested.py --execute
  uv run crawler/copy_solr_nested.py --execute --resume
  uv run crawler/copy_solr_nested.py --execute --only-with-report
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.text import fix_utf8_mojibake_tree

DEFAULT_SRC = "http://meqpacscrllt01.uhbs.ch:8983/solr/ris_pacs_2"
DEFAULT_DST = "http://localhost:8984/solr/pacs_crawler"
PARENT_FILTER = "Category:parent"
STRIP_FIELDS = ("_version_", "_root_", "_nest_path_", "_nest_parent_")
DEFAULT_CURSOR_FILE = "solr10-copy.cursor"


def clean_doc(doc: dict[str, Any]) -> dict[str, Any]:
    out = {k: v for k, v in doc.items() if k not in STRIP_FIELDS}
    children = out.get("_childDocuments_")
    if isinstance(children, list):
        out["_childDocuments_"] = [
            clean_doc(c) if isinstance(c, dict) else c for c in children
        ]
    return out


def select(session: requests.Session, base: str, params: dict, timeout: int) -> dict:
    url = f"{base.rstrip('/')}/select"
    r = session.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()


def count(session: requests.Session, base: str, q: str, timeout: int) -> int:
    data = select(session, base, {"q": q, "rows": 0, "wt": "json"}, timeout)
    return int(data["response"]["numFound"])


def update_docs(
    session: requests.Session,
    base: str,
    docs: list[dict[str, Any]],
    timeout: int,
    commit: bool,
) -> dict:
    url = f"{base.rstrip('/')}/update"
    r = session.post(
        url,
        params={"commit": "true" if commit else "false", "wt": "json"},
        json=docs,
        timeout=timeout,
    )
    r.raise_for_status()
    return r.json()


def commit_core(session: requests.Session, base: str, timeout: int) -> None:
    url = f"{base.rstrip('/')}/update"
    r = session.post(
        url,
        params={"commit": "true", "wt": "json"},
        json={},
        timeout=timeout,
    )
    r.raise_for_status()


def load_cursor(path: Path) -> str | None:
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return None
    try:
        data = json.loads(text)
        return data.get("cursorMark") or None
    except json.JSONDecodeError:
        return text


def save_cursor(path: Path, cursor: str, extra: dict[str, Any]) -> None:
    payload = {"cursorMark": cursor, **extra}
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--src", default=DEFAULT_SRC, help="Source core URL")
    p.add_argument("--dst", default=DEFAULT_DST, help="Destination core URL")
    p.add_argument("--batch-size", type=int, default=100)
    p.add_argument(
        "--child-limit",
        type=int,
        default=10000,
        help="Max children attached per parent (Solr [child] limit)",
    )
    p.add_argument(
        "--commit-every",
        type=int,
        default=20,
        help="Hard-commit after this many successful batches (0 = only at end)",
    )
    p.add_argument("--limit", type=int, default=0, help="Stop after N parents (0 = all)")
    p.add_argument(
        "--only-with-report",
        action="store_true",
        help="Copy only parents that have RisReport",
    )
    p.add_argument(
        "--cursor-file",
        default=DEFAULT_CURSOR_FILE,
        help="File used to persist cursorMark for --resume",
    )
    p.add_argument(
        "--resume",
        action="store_true",
        help="Continue from --cursor-file if it exists",
    )
    p.add_argument("--timeout", type=int, default=180)
    p.add_argument(
        "--execute",
        action="store_true",
        help="Index into destination (otherwise dry-run fetch only)",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    session = requests.Session()
    session.headers["Accept"] = "application/json"

    q = PARENT_FILTER
    if args.only_with_report:
        q = f"{PARENT_FILTER} AND RisReport:*"

    cursor_path = Path(args.cursor_file)
    cursor = "*"
    if args.resume:
        saved = load_cursor(cursor_path)
        if saved:
            cursor = saved
            print(f"Resuming from {cursor_path}")
        else:
            print(f"No cursor in {cursor_path}, starting from the beginning")

    try:
        n_src = count(session, args.src, q, args.timeout)
        n_dst_parents = count(session, args.dst, PARENT_FILTER, args.timeout)
        n_dst_all = count(session, args.dst, "*:*", args.timeout)
    except requests.RequestException as exc:
        print(f"Failed to query Solr: {exc}", file=sys.stderr)
        return 1

    print(f"Source: {args.src}")
    print(f"Dest:   {args.dst}")
    print(f"Parents matching query: {n_src}")
    print(f"Dest now: {n_dst_parents} parents, {n_dst_all} docs")
    print(
        "Each parent is copied with nested _childDocuments_ "
        "(Category:child) and RisReport when present."
    )
    if not args.execute:
        print("Dry-run: will fetch batches but not index. Re-run with --execute.")

    fl = f"*,[child parentFilter={PARENT_FILTER} limit={args.child_limit}]"
    copied_parents = 0
    copied_children = 0
    batches = 0
    t0 = time.perf_counter()
    last_id = ""

    try:
        while True:
            if args.limit and copied_parents >= args.limit:
                break
            rows = args.batch_size
            if args.limit:
                rows = min(rows, args.limit - copied_parents)
            data = select(
                session,
                args.src,
                {
                    "q": q,
                    "fl": fl,
                    "sort": "id asc",
                    "rows": rows,
                    "cursorMark": cursor,
                    "wt": "json",
                },
                args.timeout,
            )
            docs = [
                fix_utf8_mojibake_tree(clean_doc(d))
                for d in data["response"]["docs"]
            ]
            nxt = data.get("nextCursorMark")
            if not docs:
                break

            n_child = sum(len(d.get("_childDocuments_") or []) for d in docs)
            if args.execute:
                do_commit = (
                    args.commit_every > 0
                    and (batches + 1) % args.commit_every == 0
                )
                update_docs(session, args.dst, docs, args.timeout, commit=do_commit)

            copied_parents += len(docs)
            copied_children += n_child
            batches += 1
            last_id = docs[-1].get("id", last_id)
            elapsed = time.perf_counter() - t0
            rate = copied_parents / elapsed if elapsed else 0
            remaining = max(n_src - copied_parents, 0)
            if args.limit:
                remaining = max(args.limit - copied_parents, 0)
            eta = remaining / rate if rate else 0
            print(
                f"batch {batches}: +{len(docs)} parents +{n_child} children "
                f"total={copied_parents}/{n_src} "
                f"{rate:.1f} parents/s eta={eta / 3600:.1f}h"
            )

            if nxt is None or nxt == cursor:
                cursor = nxt or cursor
                break
            cursor = nxt
            save_cursor(
                cursor_path,
                cursor,
                {
                    "copied_parents": copied_parents,
                    "copied_children": copied_children,
                    "last_id": last_id,
                    "src": args.src,
                    "dst": args.dst,
                },
            )
    except KeyboardInterrupt:
        print(
            f"\nInterrupted. Resume with:\n"
            f"  uv run crawler/copy_solr_nested.py --execute --resume "
            f"--cursor-file {cursor_path}",
            file=sys.stderr,
        )
        return 130
    except requests.RequestException as exc:
        print(f"Copy failed after {copied_parents} parents: {exc}", file=sys.stderr)
        print(f"Cursor saved in {cursor_path}; re-run with --resume", file=sys.stderr)
        return 1

    if args.execute:
        try:
            commit_core(session, args.dst, args.timeout)
        except requests.RequestException as exc:
            print(f"Final commit failed: {exc}", file=sys.stderr)
            return 1

    elapsed = time.perf_counter() - t0
    print(
        f"Done. parents={copied_parents} children={copied_children} "
        f"batches={batches} elapsed={elapsed / 60:.1f} min "
        f"execute={args.execute}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
