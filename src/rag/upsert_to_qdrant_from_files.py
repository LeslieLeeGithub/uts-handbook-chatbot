#!/usr/bin/env python3
# import argparse, json, numpy as np
# from qdrant_client import QdrantClient
# from qdrant_client.http import models as qm

# if __name__ == "__main__":
#     ap = argparse.ArgumentParser()
#     ap.add_argument("--payloads", required=True)        # payloads.jsonl (rows aligned to embeddings)
#     ap.add_argument("--emb", required=True)             # embeddings.npy (normalized)
#     ap.add_argument("--collection", required=True)      # e.g. cumberland_kb
#     ap.add_argument("--host", default="localhost")
#     ap.add_argument("--port", type=int, default=6333)
#     ap.add_argument("--batch", type=int, default=64)
#     args = ap.parse_args()

#     # 1) load
#     M = np.load(args.emb)
#     ids, payloads = [], []
#     with open(args.payloads, "r", encoding="utf-8") as f:
#         for line in f:
#             if not line.strip(): continue
#             r = json.loads(line)
#             ids.append(r["id"])
#             payloads.append(r.get("meta", {}) | {"text": r.get("text", ""), "row_id": r["id"]})

#     dim = int(M.shape[1])
#     cli = QdrantClient(host=args.host, port=args.port)

#     # 2) create/recreate collection (COSINE for normalized embeddings)
#     cli.recreate_collection(
#         collection_name=args.collection,
#         vectors_config=qm.VectorParams(size=dim, distance=qm.Distance.COSINE),
#         hnsw_config=qm.HnswConfigDiff(m=32, ef_construct=256)
#     )

#     # 3) upsert in batches
#     B = args.batch
#     for i in range(0, len(ids), B):
#         cli.upsert(
#             collection_name=args.collection,
#             points=qm.Batch(
#                 ids=ids[i:i+B],
#                 vectors=M[i:i+B].tolist(),
#                 payloads=payloads[i:i+B],
#             )
#         )
#     print(f"Upserted {len(ids)} points → '{args.collection}' (dim={dim}).")


#!/usr/bin/env python3
import argparse, json, numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

def load_payloads(path):
    ids, payloads = [], []
    with open(path, "r", encoding="utf-8") as f:
        for i, ln in enumerate(f):
            if not ln.strip(): 
                continue
            r = json.loads(ln)
            rid = r.get("id")
            if not rid:
                raise SystemExit("Row missing 'id' in payloads.jsonl")
            
            # Convert string IDs to integers for Qdrant compatibility
            if isinstance(rid, str):
                # Use row index as ID for string IDs
                qdrant_id = i
            else:
                qdrant_id = rid
            
            ids.append(qdrant_id)
            payloads.append(r.get("meta", {}) | {"text": r.get("text", ""), "row_id": rid})
    # basic checks
    if len(set(ids)) != len(ids):
        raise SystemExit("Duplicate ids found in payloads.jsonl")
    return ids, payloads

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Upsert embeddings + payloads into Qdrant.")
    ap.add_argument("--payloads", required=True, help="payloads.jsonl (row-aligned to embeddings)")
    ap.add_argument("--emb", required=True, help="embeddings.npy (float32, normalized)")
    ap.add_argument("--collection", required=True, help="e.g. courses")
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=6333)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--no_recreate", action="store_true",
                    help="Do not drop collection; create if missing, then upsert/overwrite by ID.")
    ap.add_argument("--skip_version_check", action="store_true",
                    help="Skip qdrant-client/server compatibility check (useful if client > server).")
    args = ap.parse_args()

    # --- load files ---
    vecs = np.load(args.emb)
    ids, payloads = load_payloads(args.payloads)

    if vecs.shape[0] != len(ids):
        raise SystemExit(f"Emb rows {vecs.shape[0]} != payload rows {len(ids)}")
    vecs = vecs.astype("float32", copy=False)  # ensure JSON-serializable + consistent
    dim = int(vecs.shape[1])

    # --- client ---
    client_kwargs = dict(host=args.host, port=args.port)
    if args.skip_version_check:
        client_kwargs["check_compatibility"] = False  # qdrant-client >= 1.11
    cli = QdrantClient(**client_kwargs)

    # --- create / recreate collection (COSINE for normalized embeddings) ---
    if args.no_recreate:
        if not cli.collection_exists(args.collection):
            cli.create_collection(
                collection_name=args.collection,
                vectors_config=qm.VectorParams(size=dim, distance=qm.Distance.COSINE),
                hnsw_config=qm.HnswConfigDiff(m=32, ef_construct=256),
            )
    else:
        cli.recreate_collection(
            collection_name=args.collection,
            vectors_config=qm.VectorParams(size=dim, distance=qm.Distance.COSINE),
            hnsw_config=qm.HnswConfigDiff(m=32, ef_construct=256),
        )

    # --- upsert in batches ---
    B = args.batch
    for i in range(0, len(ids), B):
        cli.upsert(
            collection_name=args.collection,
            points=qm.Batch(
                ids=ids[i:i+B],                     # UUID strings
                vectors=vecs[i:i+B].tolist(),
                payloads=payloads[i:i+B],
            )
        )

    print(f"Upserted {len(ids)} points → '{args.collection}' (dim={dim}).")



# python /home/lesli/Data/StormAI/scripts/upsert_to_qdrant_from_files.py \
#   --payloads /home/lesli/Data/StormAI/data/embeddings/cumberland/payloads.jsonl \
#   --emb /home/lesli/Data/StormAI/data/embeddings/cumberland/embeddings.npy \
#   --collection cumberland_kb



# Fresh build (drops/creates collection):

# python /home/lesli/Data/Handbook/src/rag/upsert_to_qdrant_from_files.py \
#   --payloads /home/lesli/Data/Handbook/data/processed/courses/payloads.jsonl \
#   --emb /home/lesli/Data/Handbook/data/processed/courses/embeddings.npy \
#   --collection courses \
#   --skip_version_check


# Append/update only (keep existing, create if missing):

# python /home/lesli/Data/Handbook/src/rag/upsert_to_qdrant_from_files.py \
#   --payloads /home/lesli/Data/Handbook/data/processed/courses/payloads.jsonl \
#   --emb /home/lesli/Data/Handbook/data/processed/courses/embeddings.npy \
#   --collection courses \
#   --no_recreate --skip_version_check

