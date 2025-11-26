import json
import csv
import argparse
from pathlib import Path

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read().strip()
        if not text:
            return []
        # [ {...}, {...} ] 형태
        if text[0] == "[":
            return json.loads(text)
        # JSONL {..}\n{..}\n 형태도 지원
        return [json.loads(line) for line in text.splitlines() if line.strip()]

def format_llm_labels(item, min_confidence=0.0):
    """
    한 리뷰 안의 LLM 라벨들을 사람이 보기 좋은 문자열로 변환.
    규칙:
      - term이 문장에 없으면 버림
      - evidence가 없거나 빈 문자열이면 버림
      - confidence < min_confidence 이면 버림
    출력 형식:
      term|category|polarity|evidence
      여러 개일 경우 ; 로 연결
    """
    sentence = item.get("sentence") or item.get("text") or ""
    labels = item.get("labels") or []

    parts = []
    for lab in labels:
        term = (lab.get("term") or "").strip()
        category = (lab.get("category") or "").strip()
        polarity = lab.get("polarity")
        evidence = (lab.get("evidence") or "").strip()
        confidence = lab.get("confidence", 1)

        # 1) term이 문장에 없으면 삭제 (추론 term 제거)
        if term and term not in sentence:
            continue

        # 2) evidence가 없으면 삭제 (가이드라인: evidence_span null → 삭제 대상)
        if not evidence:
            continue

        # 3) confidence 필터
        if confidence is not None and confidence < min_confidence:
            continue

        # polarity를 문자열로
        polarity_str = str(polarity) if polarity is not None else ""

        # 사람이 보기 좋은 하나의 토큰으로 묶기
        # 예: "길이|사이즈/핏|-1|바지 길이가 좀 짧은거 같아요"
        part = "|".join([term, category, polarity_str, evidence])
        parts.append(part)

    # 여러 개면 ; 로 연결
    return " ; ".join(parts)

def json_to_csv_with_llm(input_path, output_path, min_confidence=0.0):
    data = load_json(input_path)

    fieldnames = ["rid", "sentence", "llm_labels"]

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for item in data:
            rid = item.get("rid") or item.get("id")
            sentence = item.get("sentence") or item.get("text")
            if sentence is None:
                continue

            llm_labels = format_llm_labels(item, min_confidence=min_confidence)

            writer.writerow({
                "rid": rid,
                "sentence": sentence.replace("\n", " ").strip(),
                "llm_labels": llm_labels
            })

    print(f"✅ Done! CSV saved to: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert ABSA JSON(with LLM labels) to CSV for Label Studio")
    parser.add_argument("input", help="Input JSON or JSONL file path")
    parser.add_argument("output", help="Output CSV file path")
    parser.add_argument("--min_conf", type=float, default=0.0,
                        help="Minimum confidence threshold for keeping LLM labels (default: 0.0)")

    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    json_to_csv_with_llm(input_path, output_path, min_confidence=args.min_conf)
