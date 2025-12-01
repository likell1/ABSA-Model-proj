import json

def jsonl_to_json(input_file, output_file):
    """
    JSONL 파일을 JSON 파일로 변환합니다.
    
    Args:
        input_file: 입력 JSONL 파일 경로
        output_file: 출력 JSON 파일 경로
    """
    data = []
    
    # JSONL 파일 읽기
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:  # 빈 줄 건너뛰기
                data.append(json.loads(line))
    
    # JSON 파일로 저장
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"변환 완료: {len(data)}개의 레코드를 {output_file}에 저장했습니다.")

# 사용 예시
if __name__ == "__main__":
    input_file = "500_(1).jsonl"
    output_file = "train_500(1).json"
    
    try:
        jsonl_to_json(input_file, output_file)
    except FileNotFoundError:
        print(f"에러: {input_file} 파일을 찾을 수 없습니다.")
    except json.JSONDecodeError as e:
        print(f"에러: JSON 파싱 실패 - {e}")
    except Exception as e:
        print(f"에러 발생: {e}")