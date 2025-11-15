#!/usr/bin/env python3
"""
Save KB files:
- reads chunks.jsonl (id, text, meta)
- filters obvious junk
- embeds texts with SentenceTransformers (e.g., Qwen3-Embedding)
- writes row-aligned:
    embeddings.npy   (float32, normalized)
    payloads.jsonl   (cleaned rows in same order)
- writes manifest.json (stats) for convenience
"""

# import argparse, os, json, re
# from typing import Iterable, Dict
# import numpy as np
# import torch
# from tqdm import tqdm
# from sentence_transformers import SentenceTransformer

# def looks_junky(text: str) -> bool:
#     t = text.strip()
#     if len(t) < 40: return True
#     if sum(ch.isdigit() for ch in t) / max(1, len(t)) > 0.5: return True
#     if re.search(r'^\s*this page has been left intentionally blank\.?\s*$', t, re.I): return True
#     if re.search(r'^\s*page\s*\w*\s*\d+\s*(of|/)\s*\w*\s*\d+\s*$', t, re.I): return True
#     return False

# def load_jsonl(path: str) -> Iterable[Dict]:
#     with open(path, "r", encoding="utf-8") as f:
#         for line in f:
#             if not line.strip(): 
#                 continue
#             rec = json.loads(line)
#             if looks_junky(rec.get("text", "")):
#                 continue
#             # ensure payload has a page_end for citation convenience
#             meta = rec.get("meta", {})
#             if "page_end" not in meta:
#                 meta["page_end"] = meta.get("page_start")
#             rec["meta"] = meta
#             yield rec

# if __name__ == "__main__":
#     ap = argparse.ArgumentParser()
#     ap.add_argument("--jsonl", required=True)
#     ap.add_argument("--embed_model_dir", required=True)
#     ap.add_argument("--out_dir", required=True)       # e.g. /home/lesli/Data/StormAI/data/processed/cumberland
#     ap.add_argument("--batch", type=int, default=32)
#     ap.add_argument("--device", default=None, help="cuda|cpu (auto if not set)")
#     args = ap.parse_args()

#     os.makedirs(args.out_dir, exist_ok=True)

#     rows = list(load_jsonl(args.jsonl))
#     if not rows:
#         raise SystemExit("No rows after filtering; check your chunks.jsonl or filters.")

#     texts = [r["text"] for r in rows]

#     device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
#     print("Device:", device)
#     model = SentenceTransformer(args.embed_model_dir, device=device)

#     # save VRAM on GPU
#     if device.startswith("cuda"):
#         for p in model.parameters():
#             if p.dtype == torch.float32:
#                 p.data = p.data.half()

#     print(f"Embedding {len(texts)} chunks (batch={args.batch}) ...")
#     vecs = model.encode(
#         texts,
#         batch_size=args.batch,
#         normalize_embeddings=True,      # needed for cosine distance later
#         convert_to_numpy=True,
#         show_progress_bar=True
#     ).astype("float32")                  # good practice for FAISS/Qdrant

#     emb_path = os.path.join(args.out_dir, "embeddings.npy")
#     pay_path = os.path.join(args.out_dir, "payloads.jsonl")

#     np.save(emb_path, vecs)
#     with open(pay_path, "w", encoding="utf-8") as w:
#         for r in rows:
#             w.write(json.dumps(r, ensure_ascii=False) + "\n")

#     print("Saved:")
#     print(" -", emb_path)
#     print(" -", pay_path)


import argparse, os, json, re
from typing import Iterable, Dict, List
import numpy as np
import torch
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
from datetime import datetime

JUNK_INTENT_BLANK = re.compile(r'^\s*this page has been left intentionally blank\.?\s*$', re.I)
JUNK_PAGE_FOOTER  = re.compile(r'^\s*page\s*\w*\s*\d+\s*(of|/)\s*\w*\s*\d+\s*$', re.I)

def looks_junky(text: str) -> bool:
    t = (text or "").strip()
    if not t: return True
    if len(t) < 40: return True
    if JUNK_INTENT_BLANK.search(t): return True
    if JUNK_PAGE_FOOTER.search(t): return True
    # mostly digits (tables of numbers)
    digits = sum(ch.isdigit() for ch in t)
    if digits / max(1, len(t)) > 0.5: return True
    return False

def load_jsonl(path: str) -> Iterable[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            # basic guards
            if looks_junky(rec.get("text", "")):
                continue
            meta = rec.get("meta", {}) or {}
            if "page_end" not in meta:
                meta["page_end"] = meta.get("page_start")
            rec["meta"] = meta
            yield rec

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", required=True, help="Input chunks.jsonl")
    ap.add_argument("--embed_model_dir", required=True, help="HF/SBERT model dir (e.g., qwen3-embedding-0.6b)")
    ap.add_argument("--out_dir", required=True, help="Folder to write embeddings.npy + payloads.jsonl")
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--device", default=None, help="cuda|cpu (auto if omitted)")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    # 1) load & filter
    rows: List[Dict] = list(load_jsonl(args.jsonl))
    if not rows:
        raise SystemExit("No rows after filtering; check your chunks.jsonl or filters.")

    # integrity checks on IDs
    ids = [r.get("id") for r in rows]
    if any(i is None for i in ids):
        raise SystemExit("Some rows are missing 'id'. Did ingest write UUIDs?")
    if len(set(ids)) != len(ids):
        raise SystemExit("Duplicate ids detected in JSONL. UUIDv5 should be unique per chunk.")

    texts = [r["text"] for r in rows]

    # 2) device + model
    device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
    print("Device:", device)
    model = SentenceTransformer(args.embed_model_dir, device=device)

    # optional: reduce VRAM
    if device.startswith("cuda"):
        for p in model.parameters():
            if p.dtype == torch.float32:
                p.data = p.data.half()

    # 3) embed (normalized for COSINE)
    print(f"Embedding {len(texts)} chunks (batch={args.batch}) ...")
    vecs = model.encode(
        texts,
        batch_size=args.batch,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=True
    )

    # sanity: rows match
    if vecs.shape[0] != len(rows):
        raise SystemExit(f"Embeddings rows {vecs.shape[0]} != payload rows {len(rows)}")

    # enforce float32 (good for FAISS/Qdrant)
    vecs = vecs.astype("float32", copy=False)

    # 4) write outputs (row-aligned)
    emb_path = os.path.join(args.out_dir, "embeddings.npy")
    pay_path = os.path.join(args.out_dir, "payloads.jsonl")
    man_path = os.path.join(args.out_dir, "manifest.json")

    np.save(emb_path, vecs)
    with open(pay_path, "w", encoding="utf-8") as w:
        for r in rows:
            w.write(json.dumps(r, ensure_ascii=False) + "\n")

    # 5) manifest (handy for audits)
    manifest = {
        "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "n_points": int(vecs.shape[0]),
        "dim": int(vecs.shape[1]),
        "embed_model": args.embed_model_dir,
        "source_jsonl": os.path.abspath(args.jsonl)
    }
    with open(man_path, "w", encoding="utf-8") as mf:
        json.dump(manifest, mf, indent=2)

    print("Saved:")
    print(" -", emb_path)
    print(" -", pay_path)
    print(" -", man_path)

if __name__ == "__main__":
    main()





# python /home/lesli/Data/StormAI/scripts/save_kb_files.py \
#   --jsonl /home/lesli/Data/StormAI/data/processed/cumberland/chunks.jsonl \
#   --embed_model_dir /home/lesli/Data/StormAI/models/hf/qwen3-embedding-0.6b \
#   --out_dir /home/lesli/Data/StormAI/data/samples/cumberland \
#   --batch 16

# python /home/lesli/Data/StormAI/scripts/save_kb_files.py \
#   --jsonl /home/lesli/Data/StormAI/data/processed/general/general_general_terminology_chunks.jsonl \
#   --embed_model_dir /home/lesli/Data/StormAI/models/hf/qwen3-embedding-0.6b \
#   --out_dir /home/lesli/Data/StormAI/data/embeddings/general_embeddings

# python /home/lesli/Data/StormAI/scripts/save_kb_files.py \
#   --jsonl /home/lesli/Data/StormAI/data/processed/parramatta_kb/parramatta_council_specific_chunks.jsonl \
#   --embed_model_dir /home/lesli/Data/StormAI/models/hf/qwen3-embedding-0.6b \
#   --out_dir /home/lesli/Data/StormAI/data/embeddings/parramatta_embeddings