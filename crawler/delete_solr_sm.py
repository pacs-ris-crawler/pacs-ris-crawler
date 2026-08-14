#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests"]
# ///
"""Delete Solr nested parent+child blocks that have a child with Modality=SM.

Core layout (this repo): parent studies (Category:parent) nest series
(Category:child). Modality lives on children. Nested docs share _root_ = parent id.

This deletes the whole block (parent and all sibling children) whenever any
child has the given modality. Dry-run is the default.

Example:
  uv run crawler/delete_solr_sm.py
  uv run crawler/delete_solr_sm.py --execute
"""
from __future__ import annotations

import argparse
import sys
from typing import Iterator

import requests

DEFAULT_BASE = "http://meqpacscrllt01.uhbs.ch:8983/solr/ris_pacs_2"
PARENT_FILTER = "Category:parent"


def solr_escape(value: str) -> str:
    specials = r'+-&|!(){}[]^"~*?:\\/'
    out = []
    for ch in value:
        if ch in specials or ch.isspace():
            out.append("\\")
        out.append(ch)
    return "".join(out)


def solr_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def select(session: requests.Session, base: str, params: dict) -> dict:
    url = f"{base.rstrip('/')}/select"
    r = session.get(url, params=params, timeout=120)
    r.raise_for_status()
    return r.json()


def count(session: requests.Session, base: str, q: str) -> int:
    data = select(session, base, {"q": q, "rows": 0, "wt": "json"})
    return int(data["response"]["numFound"])


def iter_parent_ids(
    session: requests.Session, base: str, modality: str, page_size: int
) -> Iterator[str]:
    q = f"{{!parent which={PARENT_FILTER}}}Modality:{solr_escape(modality)}"
    cursor = "*"
    while True:
        data = select(
            session,
            base,
            {
                "q": q,
                "fl": "id",
                "sort": "id asc",
                "rows": page_size,
                "cursorMark": cursor,
                "wt": "json",
            },
        )
        for doc in data["response"]["docs"]:
            yield doc["id"]
        nxt = data.get("nextCursorMark")
        if nxt is None or nxt == cursor:
            break
        cursor = nxt


def delete_by_query(
    session: requests.Session, base: str, query: str, commit: bool
) -> dict:
    url = f"{base.rstrip('/')}/update"
    payload = {"delete": {"query": query}}
    r = session.post(
        url,
        params={"commit": "true" if commit else "false", "wt": "json"},
        json=payload,
        timeout=300,
    )
    r.raise_for_status()
    return r.json()


def block_delete_query(parent_id: str) -> str:
    qid = solr_quote(parent_id)
    # Nested Solr docs share _root_ = parent id. Quoted ids because they
    # contain hyphens (PatientID-AccessionNumber).
    return f"_root_:{qid} OR id:{qid}"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--solr",
        default=DEFAULT_BASE,
        help="Core base URL (no /#/ admin hash). Default: %(default)s",
    )
    p.add_argument("--modality", default="SM", help="Child Modality to match")
    p.add_argument("--page-size", type=int, default=500)
    p.add_argument("--batch-size", type=int, default=50)
    p.add_argument(
        "--execute",
        action="store_true",
        help="Actually send deletes (otherwise dry-run)",
    )
    p.add_argument(
        "--no-commit",
        action="store_true",
        help="Do not commit after each batch (not recommended)",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    session = requests.Session()
    session.headers["Accept"] = "application/json"

    parent_q = f"{{!parent which={PARENT_FILTER}}}Modality:{solr_escape(args.modality)}"
    child_q = f"Category:child AND Modality:{solr_escape(args.modality)}"

    try:
        n_parents = count(session, args.solr, parent_q)
        n_sm_children = count(session, args.solr, child_q)
    except requests.RequestException as exc:
        print(f"Failed to query Solr at {args.solr}: {exc}", file=sys.stderr)
        return 1

    print(f"Solr core: {args.solr}")
    print(f"Parents with at least one child Modality={args.modality}: {n_parents}")
    print(f"Child docs with Modality={args.modality}: {n_sm_children}")
    print(
        "Each matching parent will be deleted together with ALL of its children "
        "(including non-SM sibling series)."
    )

    if n_parents == 0:
        print("Nothing to delete.")
        return 0

    parent_ids = list(iter_parent_ids(session, args.solr, args.modality, args.page_size))
    print(f"Collected {len(parent_ids)} parent id(s).")
    preview = parent_ids[:10]
    print("Sample parent ids:", ", ".join(preview) + (" ..." if len(parent_ids) > 10 else ""))

    if not args.execute:
        print("Dry-run only. Re-run with --execute to delete.")
        return 0

    commit = not args.no_commit
    deleted_batches = 0
    for i in range(0, len(parent_ids), args.batch_size):
        batch = parent_ids[i : i + args.batch_size]
        query = " OR ".join(f"({block_delete_query(pid)})" for pid in batch)
        try:
            resp = delete_by_query(session, args.solr, query, commit=commit)
        except requests.RequestException as exc:
            print(f"Delete batch starting at {i} failed: {exc}", file=sys.stderr)
            return 1
        status = resp.get("responseHeader", {}).get("status")
        print(f"Batch {i // args.batch_size + 1}: {len(batch)} parents, status={status}")
        deleted_batches += 1

    print(f"Done. Batches: {deleted_batches}. Commit={'yes' if commit else 'no'}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
