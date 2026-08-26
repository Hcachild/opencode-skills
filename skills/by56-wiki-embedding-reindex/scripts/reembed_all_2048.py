#!/usr/bin/env python
"""Re-embed chunk tables with configured embedding model (idempotent).

Template for by56_wiki pgvector reindex. Upload to server /root/scripts/by56_wiki/
(not in git), run with nohup, one process per table, independent logs.

Usage: reembed_all_2048.py [table_name ...] [concurrency]
  - without table names: run all tables in TABLES
  - concurrency: default EMBEDDING_MAX_CONCURRENCY from settings
  - idempotent: only processes rows where embedding IS NULL

Server-side tips (measured 2026-08, volcengine ark doubao-embedding-vision):
  - ark multimodal endpoint does NOT support batching (input list = one
    multimodal input -> one vector). Verify batch support per model first;
    if unsupported, tell the user and use concurrency instead.
  - rate limit (429) is the hard constraint: 8-16 concurrency optimal
    (~5-6/s zero failure); 32 slower; 256 hammers the box and ~45% fail.
  - backoff on 429: 3/6/9/12/15s, 6 attempts, then log to error file.
"""
from __future__ import annotations

import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.database import (
    HSCodeChunkRecord,
    KnowledgeChunkRecord,
    ProductCertificationRequirementChunkRecord,
    TradeRestrictionGoodsChunkRecord,
    TransportChannelProductChunkRecord,
    get_session_factory,
)

# NOTE: document_parent_child_chunks was dropped as redundant (2026-08-06).
TABLES = [
    (KnowledgeChunkRecord, lambda r: r.question or r.title or r.search_text or r.content or ""),
    (HSCodeChunkRecord, lambda r: r.product_name_simplified or r.product_name or ""),
    (TradeRestrictionGoodsChunkRecord, lambda r: r.product_name_simplified or r.product_name or ""),
    (TransportChannelProductChunkRecord, lambda r: r.channel_name_simplified or r.channel_name or r.search_text or r.content or ""),
    (ProductCertificationRequirementChunkRecord, lambda r: r.product_name_simplified or r.product_name or ""),
]

MODEL = get_settings().embedding_model
DIM = get_settings().embedding_dim
CONCURRENCY = get_settings().embedding_max_concurrency

_session_factory = get_session_factory()


def _parse_args():
    args = [a for a in sys.argv[1:] if a]
    tables = [a for a in args if not a.isdigit()]
    conc = [int(a) for a in args if a.isdigit()]
    return tables, (conc[0] if conc else CONCURRENCY)


def _patch_conc(conc):
    global CONCURRENCY
    CONCURRENCY = conc


def _reembed_table(model, text_fn, table_name):
    print(f"[init] model={MODEL} dim={DIM} concurrency={CONCURRENCY}", flush=True)
    with _session_factory() as db:
        total = db.scalar(select(func.count()).select_from(model.__table__))
        rows = db.execute(
            select(model.id, model.embedding).where(model.embedding.is_(None)).order_by(model.id)
        ).all()
    need_ids = [row[0] for row in rows]
    print(f"[{table_name}] total={total} to_embed={len(need_ids)}", flush=True)
    if not need_ids:
        print(f"[{table_name}] nothing to do", flush=True)
        return {"table": table_name, "ok": 0, "failed": 0}

    with _session_factory() as db:
        text_map = {}
        for rid in need_ids:
            obj = db.get(model, rid)
            if obj is not None:
                text_map[rid] = text_fn(obj)

    from app.core.config import get_embedding_provider

    provider = get_embedding_provider()
    ids = [rid for rid in need_ids if rid in text_map]
    ok = 0
    failed = 0

    def _embed(rid):
        for attempt in range(6):
            try:
                return rid, provider.embed(text_map[rid])
            except Exception as exc:
                is_429 = "429" in str(exc)
                if attempt == 5:
                    return rid, None, repr(exc)
                if is_429:
                    time.sleep(3.0 * (attempt + 1))
                else:
                    time.sleep(1.0 + attempt)

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        futures = [pool.submit(_embed, rid) for rid in ids]
        done = 0
        for fut in as_completed(futures):
            done += 1
            result = fut.result()
            rid, vec, *err = result
            if vec is None:
                failed += 1
                with open(f"/root/scripts/by56_wiki/reembed_errors_{table_name}.log", "a", encoding="utf-8") as fh:
                    fh.write(f"{rid}\t{err[0] if err else 'unknown'}\n")
                continue
            with _session_factory() as db:
                row = db.get(model, rid)
                if row is None:
                    failed += 1
                    continue
                if row.embedding is not None:
                    ok += 1
                    continue
                row.embedding = vec
                row.embedding_json = vec
                row.embedding_dim = len(vec)
                row.embedding_model = MODEL
                db.commit()
            ok += 1
            if done % 500 == 0 or done == len(futures):
                print(f"[{table_name}] {done}/{len(futures)} ok={ok} failed={failed}", flush=True)
    print(f"[{table_name}] DONE ok={ok} failed={failed}", flush=True)
    return {"table": table_name, "ok": ok, "failed": failed}


def main():
    args, conc = _parse_args()
    summary = []
    for model, text_fn in TABLES:
        if args and model.__tablename__ not in args:
            continue
        try:
            _patch_conc(conc)
            summary.append(_reembed_table(model, text_fn, model.__tablename__))
        except Exception as exc:
            print(f"[{model.__tablename__}] FAILED: {exc}", flush=True)
            summary.append({"table": model.__tablename__, "ok": -1, "failed": -1, "error": str(exc)})
    print("[summary]", flush=True)
    for item in summary:
        print(item, flush=True)


if __name__ == "__main__":
    main()
