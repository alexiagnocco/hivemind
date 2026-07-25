#!/usr/bin/env python3
"""Provision a local ONNX sentence-transformer for hivemind dense retrieval.

Downloads an ONNX-exported sentence-transformer (default
``sentence-transformers/all-MiniLM-L6-v2``, 384-dim) and its tokenizer into a
local directory. Model weights are NOT committed to the vault — this script
fetches them on demand. Point the server at the result via:

    HIVEMIND_EMBEDDINGS_BACKEND=onnx
    HIVEMIND_EMBEDDINGS_MODEL_DIR=/abs/path/to/models/all-MiniLM-L6-v2

Usage:
    uv run --extra embeddings python scripts/fetch-embedding-model.py \
        [--model REPO_ID] [--out DIR]

Requires the optional ``embeddings`` extra plus ``huggingface_hub``:
    uv pip install huggingface_hub
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
# Candidate locations of the ONNX file within HF repos (varies by exporter).
ONNX_CANDIDATES = ("onnx/model.onnx", "model.onnx", "onnx/model_quantized.onnx")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL, help="HF repo id")
    parser.add_argument(
        "--out",
        default=str(Path(__file__).resolve().parent.parent / "models"),
        help="Output base directory (a subdir named after the model is created)",
    )
    args = parser.parse_args()

    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        print(
            "huggingface_hub is required: uv pip install huggingface_hub",
            file=sys.stderr,
        )
        return 1

    out_dir = Path(args.out) / args.model.split("/")[-1]
    out_dir.mkdir(parents=True, exist_ok=True)

    # tokenizer.json
    tok = hf_hub_download(repo_id=args.model, filename="tokenizer.json")
    (out_dir / "tokenizer.json").write_bytes(Path(tok).read_bytes())
    print(f"tokenizer.json -> {out_dir / 'tokenizer.json'}")

    # model.onnx (try known locations)
    for candidate in ONNX_CANDIDATES:
        try:
            onnx = hf_hub_download(repo_id=args.model, filename=candidate)
        except Exception:  # try next candidate
            continue
        (out_dir / "model.onnx").write_bytes(Path(onnx).read_bytes())
        print(f"{candidate} -> {out_dir / 'model.onnx'}")
        break
    else:
        print(
            f"No ONNX file found in {args.model}. Tried: {', '.join(ONNX_CANDIDATES)}.\n"
            "Pick a repo that ships an ONNX export (e.g. a *-onnx variant).",
            file=sys.stderr,
        )
        return 2

    print(f"\nDone. Set HIVEMIND_EMBEDDINGS_MODEL_DIR={out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
