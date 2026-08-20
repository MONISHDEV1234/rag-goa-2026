#!/usr/bin/env python3
"""
ingest.py — Role 1 Dataset Ingestion & Normalization for HH MSMARCO-XI RAG System.

Loads ai4bharat/MSMARCO-XI dataset across available Indic languages and English,
normalizes text, explodes multi-passage rows into passage-level document records,
deduplicates texts globally, and creates a ground-truth evaluation set.
"""

import argparse
import json
import os
import re
import sys
import unicodedata
from collections import Counter
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd
import pyarrow.parquet as pq
from huggingface_hub import HfApi, hf_hub_download

# Mapping target_lang codes or filename prefixes to standardized 2-3 char language codes
LANG_CODE_MAP = {
    "hin_Deva": "hi",
    "ben_Beng": "bn",
    "tam_Taml": "ta",
    "tel_Telu": "te",
    "mar_Deva": "mr",
    "guj_Gujr": "gu",
    "kan_Knda": "kn",
    "mal_Mlym": "ml",
    "nep_Deva": "ne",
    "ori_Orya": "or",
    "pan_Guru": "pa",
    "san_Deva": "sa",
    "urd_Arab": "ur",
    "asm_Beng": "as",
}

FILE_PREFIX_MAP = {
    "asm": "as",
    "ben": "bn",
    "guj": "gu",
    "hin": "hi",
    "kan": "kn",
    "mal": "ml",
    "mar": "mr",
    "nep": "ne",
    "ori": "or",
    "pan": "pa",
    "san": "sa",
    "tam": "ta",
    "tel": "te",
    "urd": "ur",
}


def clean_text(text: Optional[str]) -> str:
    """Normalize Unicode (NFC), strip redundant whitespace and control characters."""
    if not text:
        return ""
    text = unicodedata.normalize("NFC", str(text))
    text = re.sub(r"[\r\n\t]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def get_lang_code(target_lang: str, filename: str) -> str:
    """Resolve standard language code from target_lang field or filename."""
    if target_lang in LANG_CODE_MAP:
        return LANG_CODE_MAP[target_lang]
    
    base_name = os.path.basename(filename).lower()
    for prefix, code in FILE_PREFIX_MAP.items():
        if base_name.startswith(prefix):
            return code
            
    if "_" in target_lang:
        prefix = target_lang.split("_")[0].lower()
        if prefix in FILE_PREFIX_MAP:
            return FILE_PREFIX_MAP[prefix]
        return prefix[:2]
    return target_lang[:2].lower() if target_lang else "indic"


def discover_parquet_files(repo_id: str, split: str, languages: str) -> List[str]:
    """Discover matching parquet files from HuggingFace dataset repo."""
    api = HfApi()
    all_files = api.list_repo_files(repo_id=repo_id, repo_type="dataset")
    
    prefix = f"{split}/"
    split_files = [f for f in all_files if f.startswith(prefix) and f.endswith(".parquet")]
    
    if not split_files:
        split_files = [f for f in all_files if f.endswith(".parquet")]

    if languages.lower() == "all":
        return sorted(split_files)

    selected_langs = set(l.strip().lower() for l in languages.split(","))
    filtered_files = []
    for f in split_files:
        base = os.path.basename(f).lower()
        for l in selected_langs:
            if l in base or FILE_PREFIX_MAP.get(l, l) in base:
                filtered_files.append(f)
                break
    return sorted(filtered_files)


def load_dataframe_direct(repo_id: str, file_rel_path: str, sample_limit: Optional[int]) -> pd.DataFrame:
    """Download file using hf_hub_download and slice first N rows using PyArrow."""
    local_path = hf_hub_download(repo_id=repo_id, filename=file_rel_path, repo_type="dataset")
    if sample_limit:
        with open(local_path, "rb") as f:
            pf = pq.ParquetFile(f)
            batch = next(pf.iter_batches(batch_size=sample_limit))
            return batch.to_pandas()
    return pd.read_parquet(local_path)


def process_dataset(
    repo_id: str,
    split: str,
    languages: str,
    sample_limit: Optional[int] = None,
    output_dir: str = "data",
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    """Download, explode, deduplicate, and normalize passages and eval queries."""
    os.makedirs(output_dir, exist_ok=True)
    parquet_files = discover_parquet_files(repo_id, split, languages)
    
    if not parquet_files:
        raise FileNotFoundError(f"No matching parquet files found for split='{split}' in {repo_id}")

    print(f"Found {len(parquet_files)} language file(s) for split '{split}':")
    for pf in parquet_files:
        print(f"  - {pf}")

    documents: List[Dict[str, Any]] = []
    eval_queries: List[Dict[str, Any]] = []

    seen_doc_ids: Set[str] = set()
    seen_text_hashes: Set[Tuple[str, str]] = set()
    seen_eval_keys: Set[Tuple[int, str]] = set()

    total_raw_rows = 0
    total_raw_passages = 0
    lang_doc_counter: Counter = Counter()
    lang_eval_counter: Counter = Counter()

    for i, file_rel_path in enumerate(parquet_files, 1):
        print(f"\n[{i}/{len(parquet_files)}] Downloading & loading {file_rel_path}...", flush=True)
        try:
            df = load_dataframe_direct(repo_id, file_rel_path, sample_limit)
        except Exception as e:
            print(f"Error loading {file_rel_path}: {e}", flush=True)
            continue

        print(f"  Processed {len(df):,} rows from {file_rel_path}", flush=True)
        total_raw_rows += len(df)

        for idx, row in df.iterrows():
            row_dict = row.to_dict()
            query_id = int(row_dict.get("query_id", 0))
            query_type = str(row_dict.get("query_type", "UNKNOWN"))
            eng_query = clean_text(row_dict.get("Eng_Query", ""))
            indic_query = clean_text(row_dict.get("query", ""))
            target_lang_raw = str(row_dict.get("target_lang", ""))
            lang_code = get_lang_code(target_lang_raw, file_rel_path)

            passages_obj = row_dict.get("passages", {})
            if not isinstance(passages_obj, dict):
                continue

            eng_passages = passages_obj.get("English_passages", [])
            trans_passages = passages_obj.get("Translated_passages", [])
            is_selected = passages_obj.get("is_selected", [])

            num_passages = max(len(eng_passages), len(trans_passages))
            total_raw_passages += num_passages

            for p_idx in range(num_passages):
                sel_flag = bool(is_selected[p_idx]) if p_idx < len(is_selected) else False

                # 1. English Passage Document
                if p_idx < len(eng_passages):
                    eng_text = clean_text(eng_passages[p_idx])
                    if eng_text:
                        doc_id_en = f"{query_id}_{p_idx}_en"
                        text_key_en = ("en", eng_text)
                        
                        if doc_id_en not in seen_doc_ids and text_key_en not in seen_text_hashes:
                            seen_doc_ids.add(doc_id_en)
                            seen_text_hashes.add(text_key_en)
                            doc_en = {
                                "doc_id": doc_id_en,
                                "text": eng_text,
                                "lang": "en",
                                "query_id": query_id,
                                "query_type": query_type,
                                "passage_idx": p_idx,
                                "is_selected": sel_flag,
                            }
                            documents.append(doc_en)
                            lang_doc_counter["en"] += 1

                        # Build English Eval Query Pair if selected
                        if sel_flag and eng_query:
                            eval_key_en = (query_id, "en")
                            if eval_key_en not in seen_eval_keys:
                                seen_eval_keys.add(eval_key_en)
                                eval_queries.append({
                                    "query": eng_query,
                                    "expected_doc_id": doc_id_en,
                                    "query_id": query_id,
                                    "query_type": query_type,
                                    "lang": "en",
                                })
                                lang_eval_counter["en"] += 1

                # 2. Indic Passage Document
                if p_idx < len(trans_passages):
                    indic_text = clean_text(trans_passages[p_idx])
                    if indic_text:
                        doc_id_indic = f"{query_id}_{p_idx}_{lang_code}"
                        text_key_indic = (lang_code, indic_text)

                        if doc_id_indic not in seen_doc_ids and text_key_indic not in seen_text_hashes:
                            seen_doc_ids.add(doc_id_indic)
                            seen_text_hashes.add(text_key_indic)
                            doc_indic = {
                                "doc_id": doc_id_indic,
                                "text": indic_text,
                                "lang": lang_code,
                                "query_id": query_id,
                                "query_type": query_type,
                                "passage_idx": p_idx,
                                "is_selected": sel_flag,
                            }
                            documents.append(doc_indic)
                            lang_doc_counter[lang_code] += 1

                        # Build Indic Eval Query Pair if selected
                        if sel_flag and indic_query:
                            eval_key_indic = (query_id, lang_code)
                            if eval_key_indic not in seen_eval_keys:
                                seen_eval_keys.add(eval_key_indic)
                                eval_queries.append({
                                    "query": indic_query,
                                    "expected_doc_id": doc_id_indic,
                                    "query_id": query_id,
                                    "query_type": query_type,
                                    "lang": lang_code,
                                })
                                lang_eval_counter[lang_code] += 1

    stats = {
        "parquet_files_processed": len(parquet_files),
        "total_raw_rows": total_raw_rows,
        "total_raw_passages": total_raw_passages,
        "total_documents": len(documents),
        "per_language_documents": dict(lang_doc_counter),
        "total_eval_queries": len(eval_queries),
        "per_language_eval_queries": dict(lang_eval_counter),
    }

    return documents, eval_queries, stats


def main():
    parser = argparse.ArgumentParser(
        description="Explode and normalize ai4bharat/MSMARCO-XI dataset into document pool and evaluation set."
    )
    parser.add_argument(
        "--repo-id",
        type=str,
        default="ai4bharat/MSMARCO-XI",
        help="Hugging Face dataset repository ID (default: ai4bharat/MSMARCO-XI)",
    )
    parser.add_argument(
        "--split",
        type=str,
        default="validation",
        choices=["validation", "train"],
        help="Dataset split to ingest (default: validation)",
    )
    parser.add_argument(
        "--languages",
        type=str,
        default="all",
        help="Comma-separated language codes or 'all' (default: all)",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help="Optional row limit per language file for fast local testing",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data",
        help="Output directory for JSONL files (default: data)",
    )

    args = parser.parse_args()

    print("=========================================================================")
    print("         MSMARCO-XI INGESTION & NORMALIZATION (ROLE 1)                   ")
    print("=========================================================================")
    print(f"Repo ID     : {args.repo_id}")
    print(f"Split       : {args.split}")
    print(f"Languages   : {args.languages}")
    print(f"Sample Limit: {args.sample if args.sample else 'None (Full Dataset)'}")
    print(f"Output Dir  : {args.output_dir}")
    print("=========================================================================")

    documents, eval_queries, stats = process_dataset(
        repo_id=args.repo_id,
        split=args.split,
        languages=args.languages,
        sample_limit=args.sample,
        output_dir=args.output_dir,
    )

    docs_path = os.path.join(args.output_dir, "documents.jsonl")
    print(f"\nSaving {len(documents):,} documents to {docs_path}...")
    with open(docs_path, "w", encoding="utf-8") as f:
        for doc in documents:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")

    eval_path = os.path.join(args.output_dir, "eval_queries.jsonl")
    print(f"Saving {len(eval_queries):,} evaluation queries to {eval_path}...")
    with open(eval_path, "w", encoding="utf-8") as f:
        for eq in eval_queries:
            f.write(json.dumps(eq, ensure_ascii=False) + "\n")

    print("\n=========================================================================")
    print("                     INGESTION SUMMARY STATISTICS                        ")
    print("=========================================================================")
    print(f"Parquet Files Processed : {stats['parquet_files_processed']}")
    print(f"Total Raw Rows Read     : {stats['total_raw_rows']:,}")
    print(f"Total Raw Passages      : {stats['total_raw_passages']:,}")
    print(f"Total Unique Documents  : {stats['total_documents']:,}")
    print(f"Total Eval Query Pairs  : {stats['total_eval_queries']:,}")
    print("\n--- Per-Language Document Counts ---")
    for lang, count in sorted(stats["per_language_documents"].items(), key=lambda x: -x[1]):
        print(f"  - {lang:5s}: {count:8,d} docs")

    print("\n--- Per-Language Evaluation Set Size ---")
    for lang, count in sorted(stats["per_language_eval_queries"].items(), key=lambda x: -x[1]):
        print(f"  - {lang:5s}: {count:8,d} query pairs")
    print("=========================================================================")


if __name__ == "__main__":
    main()
