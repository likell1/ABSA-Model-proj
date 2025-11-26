import pandas as pd
import re
import json

paths = [
    "/Users/hyeokjun/Desktop/Code/ABSA_Model/absa_data/fashion_data/TS_1-1.여성의류.xlsx",
    "/Users/hyeokjun/Desktop/Code/ABSA_Model/absa_data/fashion_data/TS_1-2.남성의류.xlsx",
    "/Users/hyeokjun/Desktop/Code/ABSA_Model/absa_data/fashion_data/TS_1-3.패션슈즈.xlsx",
    "/Users/hyeokjun/Desktop/Code/ABSA_Model/absa_data/fashion_data/TS_1-4.잡화.xlsx"
]

# 시트별로 합치기
frames = []
for path in paths:
    xls = pd.read_excel(path, sheet_name=None)
    for sheet, df in xls.items():
        df["source_file"] = path.split("/")[-1]
        df["source_sheet"] = sheet
    frames.append(df)

data = pd.concat(frames, ignore_index=True)

def clean_text(text):
    text = str(text)
    text = re.sub(r"\s+", " ", text)  # 공백 통합
    return text.strip()

# 상품평 컬럼만 사용
df = data[["상품평"]].rename(columns={"상품평": "sentence"}).dropna()

# 텍스트 정제
df["sentence"] = df["sentence"].apply(clean_text)

# 중복 제거
df = df.drop_duplicates(subset=["sentence"]).reset_index(drop=True)

# 고유 id 부여
df.insert(0, "rid", df.index + 1)

#LLM 프롬프트로 넣을 형태로 jsonl에 저장
df[["rid", "sentence"]].to_json("fashion_raw.jsonl", orient="records", force_ascii=False, lines=True)

#print("총 데이터 개수: ", len(df))
#print(df.head())