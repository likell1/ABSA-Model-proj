import json

# 파일 경로 설정 (업로드하신 파일명과 동일하게 설정했습니다)
input_file_path = 'train_500(1).json'
output_file_path = 'train_500_hj.json'

def process_json(input_path, output_path):
    try:
        # 1. JSON 파일 읽기
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 2. 데이터 수정
        for item in data:
            # aspects 키가 있는지 확인
            if 'aspects' in item:
                for aspect in item['aspects']:
                    # 삭제할 키들 (존재하지 않아도 에러가 나지 않도록 pop 사용)
                    aspect.pop('evidence', None)
                    aspect.pop('evidence_span', None)
                    aspect.pop('confidence', None)
                    
                    # annotator 값 변경
                    aspect['annotator'] = 'hyeokjun'

        # 3. 수정된 데이터를 새로운 JSON 파일로 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            # ensure_ascii=False를 해야 한글이 깨지지 않고 저장됩니다.
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        print(f"작업 완료! '{output_path}' 파일이 생성되었습니다.")

    except FileNotFoundError:
        print(f"오류: '{input_path}' 파일을 찾을 수 없습니다.")
    except Exception as e:
        print(f"오류 발생: {e}")

# 실행
if __name__ == "__main__":
    process_json(input_file_path, output_file_path)