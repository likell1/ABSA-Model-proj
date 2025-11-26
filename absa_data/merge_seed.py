import json
from pathlib import Path
import argparse

def merge_jsonl(in_dir: str, out_file: str):
    out_path = Path(out_file)
    with out_path.open("w", encoding="utf-8") as fout:
        for p in sorted(Path(in_dir).glob("seeds_batch_*.jsonl")):
            with p.open("r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        fout.write(line)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in_dir", required=True)   # ex) seeds/
    ap.add_argument("--out_file", required=True) # ex) seeds_all.jsonl
    args = ap.parse_args()
    merge_jsonl(args.in_dir, args.out_file)
    print(f"merged → {args.out_file}")
