# -*- coding: utf-8 -*-

# ===== Ollama 서버 설정 =====
OLLAMA_HOST = "http://localhost:11434"

# 모델명 (실행 중인 모델로 맞추세요: 예) "qwen2.5:14b-instruct", "llama3.1:8b-instruct")
OLLAMA_MODEL = "qwen2.5:14b-instruct"

# 요청 타임아웃(초)
OLLAMA_TIMEOUT = 120

# 라벨링 시 배치 크기(파일 분할이 아니라, 재시도/큐잉 등에 쓸 때 사용)
LABEL_BATCH_SIZE = 8

# Ollama options (여기 값만 수정해서 전역 반영)
OLLAMA_OPTIONS = {
    "temperature": 0.1,
    "num_ctx": 4096,  # 길면 8192도 가능 (모델/메모리 따라 조정)
    # "top_p": 0.9,
    # "repeat_penalty": 1.05,
}
