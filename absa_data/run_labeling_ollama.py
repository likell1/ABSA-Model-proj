# run_labeling_ollama.py
# -*- coding: utf-8 -*-
import json, time, argparse, requests, re
from pathlib import Path
from settings_ollama import OLLAMA_HOST, OLLAMA_MODEL, OLLAMA_TIMEOUT, LABEL_BATCH_SIZE, OLLAMA_OPTIONS

OLLAMA_CHAT_URL = f"{OLLAMA_HOST}/api/chat"

BASE_REQ = {
    "model": OLLAMA_MODEL,
    "format": "json",    
    "stream": False,     
    "options": OLLAMA_OPTIONS
}

JSON_BLOCK_RE = re.compile(r"(\{.*\}|\[.*\])\s*$", re.S)

# 패션(의류) 리뷰 카테고리
ALLOWED_CATEGORIES = [
    "사이즈/핏","재질/원단","디자인/스타일","색상","가격",
    "배송/서비스","착용감","품질/내구성","세탁/관리","교환/반품/AS"
]
ALLOWED_POL = {-1, 0, 1}

# 시스템 프롬프트: 모델의 역할/출력형식을 엄격히 고정
SYSTEM_PROMPT = (
    "너는 한국어 패션/의류 리뷰에서 속성(Aspect)과 감성(−1/0/1)을 추출하는 어시스턴트다. "
    "반드시 JSON만 출력하고, 추가 텍스트/설명/마크다운을 절대 출력하지 마."
)


def build_user_prompt(sentence: str) -> str:
    s = str(sentence).strip().replace("\n", " ")
    return (
        "아래 한국어 패션/의류 리뷰에 대해 속성 기반 감성 분석을 수행하라.\n"
        f"- category 허용값: {ALLOWED_CATEGORIES}\n"
        "- polarity 허용값: -1(부정), 0(중립), 1(긍정)\n\n"
        f'리뷰: \"{s}\"\n\n'
        "반환 형식(단일 JSON만 허용):\n"
        "{\n"
        '  \"aspects\": [\n'
        '    {\"term\": \"사이즈\", \"category\": \"사이즈/핏\", \"polarity\": 1},\n'
        '    {\"term\": \"원단\", \"category\": \"재질/원단\", \"polarity\": -1}\n'
        "  ]\n"
        "}\n"
        "JSON 이외의 어떤 텍스트도 출력하지 마."
    )


def _extract_json(text: str):
    try:
        return json.loads(text)
    except Exception:
        m = JSON_BLOCK_RE.search(text or "")
        if not m:
            raise ValueError(f"JSON parse failed (head): {str(text)[:240]}")
        return json.loads(m.group(1))

def call_ollama_json(system_prompt: str, user_prompt: str, retries=2, timeout=120):
    """
    1) /api/chat 시도
    2) 404면 /api/generate 폴백
    모두 format=json 강제, stream=False
    """
    base_host = OLLAMA_HOST.rstrip('/')
    url_chat = f"{base_host}/api/chat"
    url_gen  = f"{base_host}/api/generate"

    # 공통 옵션
    options = BASE_REQ.get("options", {})
    model   = BASE_REQ["model"]

    last_err = None
    for attempt in range(retries + 1):
        # 1) /api/chat 먼저 시도
        try:
            payload = {
                "model": model,
                "format": "json",
                "stream": False,
                "options": options,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
            }
            r = requests.post(url_chat, json=payload, timeout=timeout)
            if r.status_code == 404:
                raise FileNotFoundError("/api/chat 404")
            r.raise_for_status()
            raw = (r.json().get("message") or {}).get("content", "")
            if not raw:
                raise ValueError(f"empty content from /api/chat: {r.text[:200]}")
            return _extract_json(raw)
        except Exception as e1:
            last_err = e1
            # 2) /api/generate 폴백
            try:
                body = {
                    "model": model,
                    "prompt": f"[SYSTEM]\n{system_prompt}\n[USER]\n{user_prompt}",
                    "options": options,
                    "format": "json",     # ✅ top-level
                    "stream": False,
                }
                rg = requests.post(url_gen, json=body, timeout=timeout)
                rg.raise_for_status()
                txt = rg.json().get("response", "")
                if not txt:
                    raise ValueError(f"empty content from /api/generate: {rg.text[:200]}")
                return _extract_json(txt)
            except Exception as e2:
                last_err = e2
                if attempt < retries:
                    time.sleep(0.5 * (attempt + 1))
                else:
                    print(f"[ERR] chat/gen failed: {type(last_err).__name__} {last_err}")
                    print(f"[DBG] chat url: {url_chat}, gen url: {url_gen}")
                    return None


# ===== 카테고리 보정기 (패션 리뷰 전용) =====
_CAT_SYNONYMS = {
    "사이즈/핏":  ["사이즈","크기","핏","길이","품","정사이즈","루즈","타이트","오버핏"],
    "재질/원단": ["재질","원단","소재","두께","촉감","보풀","올풀림","냄새","퀄리티(소재)"],
    "디자인/스타일": ["디자인","스타일","디테일","로고","패턴","마감(디자인)","예쁨","세련"],
    "색상": ["색","컬러","색감","염색","물빠짐"],
    "가격": ["가격","가성비","가심비","할인","세일","비싸","저렴"],
    "배송/서비스": ["배송","포장","택배","CS","응대","판매자","문의","교환 안내"],
    "착용감": ["착용감","편해","불편","무게감","통풍","따뜻","시원","신축성","쫀쫀"],
    "품질/내구성": ["내구성","퀄리티","하자","불량","튼튼","약함","봉제","마감"],
    "세탁/관리": ["세탁","관리","수축","변형","드라이","세탁 후 변형","물빠짐"],
    "교환/반품/AS": ["교환","반품","환불","A/S","AS","교환 속도","처리"]
}

def _guess_category(term: str, cat_text: str) -> str:
    """모델이 애매하거나 오타가 있는 category를 보정"""
    c = (cat_text or "").strip()
    if c in ALLOWED_CATEGORIES:
        return c
    text = f"{term} {c}"
    for k, kws in _CAT_SYNONYMS.items():
        if any(kw in text for kw in kws):
            return k
    if any(x in text for x in ["사이즈","핏","정사이즈","타이트","루즈"]): return "사이즈/핏"
    if any(x in text for x in ["배송","포장","판매자","응대","CS","택배"]): return "배송/서비스"
    if any(x in text for x in ["교환","반품","환불","A/S","AS"]): return "교환/반품/AS"
    return "품질/내구성"


def _find_span(sentence: str, term: str):
    """term이 문장 안에 어디에 있는지 대략적인 문자 오프셋 리턴"""
    s = str(sentence)
    t = str(term).strip()
    if not t:
        return None
    idx = s.find(t)
    if idx >= 0:
        return [idx, idx + len(t)]
    # 공백 제거해서 한 번 더 시도 (조금 러프하게)
    import re
    s2 = re.sub(r"\s+", "", s)
    t2 = re.sub(r"\s+", "", t)
    idx2 = s2.find(t2)
    if idx2 >= 0:
        return [idx2, idx2 + len(t2)]
    return None

ANNOTATOR = f"ollama:{OLLAMA_MODEL}"
DEFAULT_CONFIDENCE = 1.0



def process_batch(batch_file: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"seeds_{batch_file.stem}.jsonl"
    log_file = out_dir / f"errors_{batch_file.stem}.log"

    done = set()
    if out_file.exists():
        with out_file.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    done.add(json.loads(line)["rid"])
                except:
                    pass

    cnt = 0
    with batch_file.open("r", encoding="utf-8") as fin, \
         out_file.open("a", encoding="utf-8") as fout, \
         log_file.open("a", encoding="utf-8") as flog:

        for line in fin:
            if not line.strip():
                continue
            rec = json.loads(line)

            # 입력 키 이름 호환: rid / sentence / text
            rid = rec.get("rid")
            try:
                # rid가 문자열일 수도 있으니 안전하게 int 시도
                rid = int(rid)
            except Exception:
                # rid가 없으면 스킵(필요하면 여기서 생성 규칙 추가)
                flog.write(json.dumps({"rid": rid, "error": "missing_or_invalid_rid", "raw": rec}, ensure_ascii=False) + "\n")
                continue

            sent = rec.get("sentence") or rec.get("text") or ""
            if not sent:
                flog.write(json.dumps({"rid": rid, "error": "empty_sentence"}) + "\n")
                continue
            if rid in done:
                continue

            prompt = build_user_prompt(sent)
            data = call_ollama_json(SYSTEM_PROMPT, prompt, timeout=OLLAMA_TIMEOUT)

            if not data or "aspects" not in data or not isinstance(data["aspects"], list):
                flog.write(json.dumps({"rid": rid, "error": "invalid_response", "raw": data}, ensure_ascii=False) + "\n")
                continue

            aspects = []
            for a in data["aspects"]:
                term = str(a.get("term", "")).strip()
                if not term:
                    continue
                
                category_raw = str(a.get("category", "")).strip()
                category = category_raw if category_raw in ALLOWED_CATEGORIES else _guess_category(term, category_raw)
            
                pol_raw = a.get("polarity")
                try:
                    polarity = int(pol_raw)
                except Exception:
                    try:
                        polarity = int(str(pol_raw).strip())
                    except Exception:
                        polarity = 0
                if polarity not in ALLOWED_POL:
                    polarity = 0
            
                span = _find_span(sent, term)
            
                aspects.append({
                    "term": term,
                    "category": category,
                    "polarity": polarity,
                    "evidence": term,              # 근거 텍스트
                    "evidence_span": span,         # [start, end]
                    "annotator": ANNOTATOR,        # 어떤 모델이            라벨링했는지
                    "confidence": DEFAULT_CONFIDENCE
                })



            if not aspects:
                flog.write(json.dumps({"rid": rid, "error": "empty_aspects"}) + "\n")
                continue

            fout.write(json.dumps(
                {"rid": rid, "sentence": sent, "aspects": aspects},
                ensure_ascii=False
            ) + "\n")

            cnt += 1
            if cnt % 50 == 0:
                fout.flush()
                print(f"{batch_file.name}: {cnt} done")

            time.sleep(0.005)  # CPU/발열 완충(필요 시 조정)

    print(f"✅ {batch_file.name} → 완료: {out_file}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--batches_dir", required=True)
    ap.add_argument("--out_dir", required=True)
    args = ap.parse_args()

    batches = sorted(Path(args.batches_dir).glob("batch_*.jsonl"))
    if not batches:
        raise SystemExit("No batch_*.jsonl found.")
    for bf in batches:
        process_batch(bf, Path(args.out_dir))
