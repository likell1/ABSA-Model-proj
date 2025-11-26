import json
from pathlib import Path
import argparse

def split_jsonl(in_file: str, out_dir: str, lines_per_file: int, prefix: str = "batch"):
    in_path = Path(in_file)
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    buf = []
    idx = 1

    with in_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            buf.append(line.rstrip("\n"))
            
            if len(buf) >= lines_per_file:
                (out_path / f"{prefix}_{idx:02d}.jsonl").write_text(
                    "\n".join(buf) + "\n", encoding="utf-8"
                )
                buf.clear()
                idx += 1

    # 마지막 남은 라인들 기록
    if buf:
        (out_path / f"{prefix}_{idx:02d}.jsonl").write_text(
            "\n".join(buf) + "\n", encoding="utf-8"
        )

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in_file", required=True)
    ap.add_argument("--out_dir", required=True)
    ap.add_argument("--lines", type=int, default=3000)
    args = ap.parse_args()
    split_jsonl(args.in_file, args.out_dir, args.lines)
