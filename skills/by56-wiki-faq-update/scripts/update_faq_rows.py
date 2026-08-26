"""by56_wiki 知识库 FAQ/文档行级数据更新通用脚本。

支持两种更新模式（可组合）：
- 模式 A（整体替换答案）：--new-answer-file 提供新答案文本，对"answer 命中 --match 文本"的 QA 条目整段替换 answer。
- 模式 B（局部文本替换）：--replace "旧文本=>新文本" 可多次，对所有定位条目的 answer/content/search_text 做子串替换。

流程：定位 -> 生成变更计划 ->（--apply 时）写 faq_items / knowledge_chunks / documents.parsed_preview_json
      -> 重嵌入 -> 重建 FAQ BM25 + chunk BM25 -> 更新源 Excel（可选，自动备份）-> 验证。
安全：未加 --apply 时只打印计划、不修改任何数据（含 Excel）。

用法示例：
  python update_faq_rows.py --match "182-190" --new-answer-file /tmp/new_answer.txt --apply
  python update_faq_rows.py --match "182-190" --replace "182-190=>162-170" --apply
  python update_faq_rows.py --match "海雄" --doc-title "FAQ入库-仓库" --verify-query "海雄仓收货信息" --apply
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

import openpyxl
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from app.core.config import get_settings
from app.core.database import session_scope
from app.core.database import DocumentRecord, FAQItemRecord, KnowledgeChunkRecord
from app.repositories import faq_items as faq_items_repo
from app.services.retrieval import chunking_service
from app.services.retrieval.chunk_retriever import retrieve_qa_chunks_by_vector
from app.services.retrieval.embedding_service import embed_persistent_texts
from app.stores import bm25_store
from app.stores import chunk_bm25_store


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--match", action="append", required=True,
                        help="定位用的内容子串（可重复，AND 关系），匹配 current chunk 的 content")
    parser.add_argument("--doc-title", default=None, help="限定文档标题（模糊匹配，如 FAQ入库-仓库）")
    parser.add_argument("--new-answer-file", default=None,
                        help="模式 A：新答案文本文件路径（整段替换 QA 条目 answer）")
    parser.add_argument("--replace", action="append", default=[],
                        help="模式 B：\"旧文本=>新文本\" 子串替换（可重复），作用于 answer/content/search_text/Excel")
    parser.add_argument("--excel", action="append", default=[],
                        help="要同步更新的源 Excel 路径（可重复），apply 前自动生成 .bak.YYYYMMDD 备份")
    parser.add_argument("--verify-query", default=None, help="验证用的检索问题（如 海雄仓收货信息）")
    parser.add_argument("--apply", action="store_true", help="实际写入；缺省为 dry-run 只打印计划")
    return parser.parse_args(argv)


def _parse_replace_pairs(raw: list[str]) -> list[tuple[str, str]]:
    pairs = []
    for item in raw:
        if "=>" not in item:
            raise ValueError(f"--replace 格式应为 旧文本=>新文本: {item}")
        old, new = item.split("=>", 1)
        if old == new:
            continue
        pairs.append((old, new))
    return pairs


def locate_columns(ws) -> tuple[int, int] | None:
    for row in ws.iter_rows(min_row=1, max_row=8, values_only=False):
        q_col = None
        for cell in row:
            if cell.value and "问题" in str(cell.value):
                q_col = cell.column - 1
                break
        if q_col is None:
            continue
        for cell in row:
            if cell.value and "答案" in str(cell.value):
                return q_col, cell.column - 1
    return None


def plan_excel_changes(ws, q_col: int, a_col: int, args: argparse.Namespace,
                       target_questions: set[str], replace_pairs: list[tuple[str, str]],
                       new_answer: str | None) -> list[tuple[int, int, str]]:
    """返回 [(excel_row_no, col_index, new_value)]，不修改任何单元格。"""
    changes = []
    for excel_row_no, row in enumerate(ws.iter_rows(min_row=2), start=2):
        q_cell, a_cell = row[q_col], row[a_col]
        q_text = str(q_cell.value or "").strip()
        a_text = str(a_cell.value or "")
        new_val = a_text
        if new_answer is not None and q_text in target_questions and any(m in a_text for m in args.match):
            new_val = new_answer
        for old, new in replace_pairs:
            if old in new_val:
                new_val = new_val.replace(old, new)
        if new_val != a_text:
            changes.append((excel_row_no, a_col, new_val))
    return changes


def main() -> int:
    args = parse_args()
    apply = args.apply
    replace_pairs = _parse_replace_pairs(args.replace)
    if args.new_answer_file:
        new_answer = Path(args.new_answer_file).read_text(encoding="utf-8").strip()
    else:
        new_answer = None
    if new_answer is None and not replace_pairs:
        raise SystemExit("必须提供 --new-answer-file 或 --replace")

    print(f"[{'APPLY' if apply else 'DRY-RUN'}] 未加 --apply 时不会写入任何数据")

    with session_scope() as db:
        settings = get_settings()
        stmt = select(KnowledgeChunkRecord).where(KnowledgeChunkRecord.is_current.is_(True))
        for m in args.match:
            stmt = stmt.where(KnowledgeChunkRecord.content.like(f"%{m}%"))
        if args.doc_title:
            doc_filter = db.scalar(
                select(DocumentRecord).where(DocumentRecord.title.contains(args.doc_title)).limit(1)
            )
            if doc_filter is None:
                print(f"  [ERR] 未找到文档标题包含 {args.doc_title}")
                return 2
            stmt = stmt.where(KnowledgeChunkRecord.document_id == doc_filter.id)
        chunks = list(db.scalars(stmt.order_by(KnowledgeChunkRecord.id)))
        print(f"定位到 {len(chunks)} 个 current chunk")
        if not chunks:
            print("  无匹配，结束")
            return 1
        for c in chunks:
            print(f"  chunk {c.id} doc={c.document_id} faq={c.faq_item_id} type={c.chunk_type} [{c.title or c.question}]")

        faq_ids = {c.faq_item_id for c in chunks if c.faq_item_id}
        faq_items = list(
            db.scalars(select(FAQItemRecord).where(FAQItemRecord.id.in_(faq_ids))) if faq_ids else []
        )
        faq_by_id = {item.id: item for item in faq_items}
        doc_ids = {c.document_id for c in chunks if c.document_id}
        docs = {d.id: d for d in db.scalars(select(DocumentRecord).where(DocumentRecord.id.in_(doc_ids))) if d.parsed_preview_json}

        plan = []  # {chunk, faq_item, field_updates: {field: new_value}}
        for chunk in chunks:
            faq_item = faq_by_id.get(chunk.faq_item_id)
            field_updates = {}
            if faq_item is not None and new_answer is not None and any(m in (chunk.answer or "") for m in args.match):
                if chunk.answer != new_answer:
                    field_updates["answer"] = new_answer
            for old, new in replace_pairs:
                for field in ("answer", "content", "search_text"):
                    cur = getattr(chunk, field) or ""
                    if old in cur:
                        field_updates[field] = cur.replace(old, new)
            if field_updates:
                plan.append({"chunk": chunk, "faq_item": faq_item, "field_updates": field_updates})
                print(f"  [PLAN] chunk {chunk.id} faq {chunk.faq_item_id} [{chunk.question or chunk.title}] -> {field_updates}")

        preview_plan = 0
        for chunk in chunks:
            if chunk.document_id not in docs:
                continue
            faq_item = faq_by_id.get(chunk.faq_item_id)
            if faq_item is None:
                continue
            doc = docs[chunk.document_id]
            for item in doc.parsed_preview_json:
                if not isinstance(item, dict) or item.get("row_no") != faq_item.row_no:
                    continue
                raw = item.get("raw_fields")
                answer_text = str(item.get("answer") or "")
                new_text = answer_text
                if new_answer is not None and any(m in answer_text for m in args.match):
                    new_text = new_answer
                for old, new in replace_pairs:
                    if old in new_text:
                        new_text = new_text.replace(old, new)
                if new_text != answer_text:
                    preview_plan += 1
                    if apply:
                        item["answer"] = new_text
                        if isinstance(raw, dict) and "答案" in raw:
                            raw["答案"] = new_text
                        flag_modified(doc, "parsed_preview_json")

        print(f"变更计划: chunks/faq_items {len(plan)} 条, preview 行 {preview_plan} 条")

        if apply:
            for p in plan:
                for field, value in p["field_updates"].items():
                    setattr(p["chunk"], field, value)
                if p["faq_item"] is not None and "answer" in p["field_updates"]:
                    p["faq_item"].answer = p["field_updates"]["answer"]
            if plan:
                dims = {c.embedding_dim for c in chunks if c.embedding_dim}
                target_dim = max(dims) if dims else 1536
                texts = []
                for c in chunks:
                    if c.chunk_type in ("qa", "faq") and c.question:
                        texts.append(c.question)
                    else:
                        texts.append(c.search_text or c.content or c.title or "")
                vectors = embed_persistent_texts(texts, target_dim=target_dim)
                for c, vector in zip(chunks, vectors):
                    c.embedding = vector
                    c.embedding_json = vector
                    c.embedding_dim = len(vector)
                    c.embedding_model = settings.embedding_model
                print(f"  embeddings regenerated: {len(chunks)} 条 (dim={target_dim}, model={settings.embedding_model})")

    print("=== 源 Excel 同步 ===")
    target_questions = set()
    with session_scope() as db:
        if faq_ids:
            target_questions = set(db.scalars(select(FAQItemRecord.question).where(FAQItemRecord.id.in_(faq_ids))))
    for excel_path in args.excel:
        path = Path(excel_path)
        if not path.exists():
            print(f"  [SKIP] Excel 不存在: {path}")
            continue
        wb = openpyxl.load_workbook(path)
        total = 0
        for ws in wb.worksheets:
            cols = locate_columns(ws)
            if cols is None or cols[1] is None:
                print(f"  [SKIP] sheet {ws.title} 未找到问题/答案列")
                continue
            changes = plan_excel_changes(ws, cols[0], cols[1], args, target_questions, replace_pairs, new_answer)
            for row_no, col, new_val in changes:
                ws.cell(row=row_no, column=col + 1).value = new_val
            total += len(changes)
        if total and apply:
            backup = path.with_suffix(path.suffix + f".bak.{datetime.now().strftime('%Y%m%d')}")
            if not backup.exists():
                shutil.copy2(path, backup)
                print(f"  [BACKUP] {backup.name}")
            wb.save(path)
            print(f"  [SAVED] {path.name}: {total} 行")
        else:
            print(f"  [{'DRY' if not apply else 'NOCHANGE'}] {path.name}: 待更新 {total} 行")

    print("=== 重建 FAQ BM25 ===")
    with session_scope() as db:
        records = faq_items_repo.list_retrieval_faq_items(db)
        if apply:
            n = bm25_store.rebuild_index(records)
            print(f"  rebuilt {n} 条")
        else:
            print(f"  将重建 {len(records)} 条 (dry)")

    print("=== 重建 chunk BM25 ===")
    with session_scope() as db:
        if apply:
            n = chunking_service.rebuild_chunk_keyword_index(db)
            print(f"  rebuilt {n} 条")
        else:
            n = len(chunking_service.list_current_chunk_index_records(db))
            print(f"  将重建 {n} 条 (dry)")

    print("=== 验证 ===")
    with session_scope() as db:
        if args.verify_query:
            for hit in retrieve_qa_chunks_by_vector(db, args.verify_query, limit=5):
                ans = (str(hit.get("answer") or "").splitlines() or [""])[0][:80]
                print(f"  vector: {hit.get('score')} [{hit.get('question')}] chunk={hit.get('chunk_id')} | {ans}")
        print("  --- FAQ BM25 ---")
        for hit in bm25_store.search(args.verify_query or args.match[0], limit=3):
            ans = (str(hit.get("answer") or "").splitlines() or [""])[0][:80]
            print(f"  bm25: {hit.get('score')} [faq {hit.get('faq_id')}] {hit.get('question')} | {ans}")
        print("  --- chunk BM25 ---")
        for hit in chunk_bm25_store.search(args.match[0], limit=3):
            ans = (str(hit.get("answer") or "").splitlines() or [""])[0][:80]
            print(f"  chunk_bm25: {hit.get('score')} chunk={hit.get('chunk_id')} {hit.get('question')} | {ans}")
        stale = list(db.scalars(
            select(KnowledgeChunkRecord).where(
                KnowledgeChunkRecord.is_current.is_(True),
                *[KnowledgeChunkRecord.content.like(f"%{m}%") for m in args.match],
            )
        ))
        print(f"  仍命中 --match 的 current chunks: {len(stale)}")
        for s in stale:
            print(f"    chunk {s.id} [{s.title or s.question}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())