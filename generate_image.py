import os
import json
from datetime import datetime, timezone
from google import genai
from google.genai import types
from google.genai.errors import APIError
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

CONFIG_DIR = "configs"
COMMON_BASE_PATH = os.path.join(CONFIG_DIR, "common_base.json")
MODE1_PATH = os.path.join(CONFIG_DIR, "mode1_general_trans.json")
MODE2_PATH = os.path.join(CONFIG_DIR, "mode2_face_consistency.json")
VFX_PATH = os.path.join(CONFIG_DIR, "VFX_prompt.json")
NEGATIVE_PATH = os.path.join(CONFIG_DIR, "negative_prompt.json")

def load_json_config(file_path: str):
    """
    JSON 파일을 안전하게 로드하는 헬퍼 함수, 긁어온건 비밀!

    :param file_path: json 파일 경로
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: 설정 파일을 찾을 수 없습니다 - {file_path}")
        return {}
    except json.JSONDecodeError:
        print(f"Error: JSON 형식이 잘못되었습니다 - {file_path}")
        return {}

def build_prompt_from_json(mode_file_path: str, variables: dict):
    """
    JSON 파일들을 읽어 최종 프롬프트(Positive, Negative)를 '하나의 딕셔너리'로 조립하는 함수
    
    :param mode_file_path: 선택한 모드(Mode 1, Mode 2 등)의 JSON 경로
    :param variables: 치환할 변수 딕셔너리 (예: {"Reference_Image": "abc.png"})
    :return: {"positive": str, "negative": str}
    """
    # 1. JSON 파일 로드
    base_data = load_json_config(COMMON_BASE_PATH)
    mode_data = load_json_config(mode_file_path)
    neg_data = load_json_config(NEGATIVE_PATH)

    # 긍정 프롬프트 조립
    base_text = " ".join(base_data.get('positive_prompts', {}).values())
    mode_text = " ".join(mode_data.get('prompts', {}).values())
    full_positive_prompt = f"{base_text} {mode_text}"

    # 부정 프롬프트 조립 (부정은 리스트임)
    neg_content = neg_data.get('system_default', {}).get('core_avoidance', "")
    if isinstance(neg_content, list):
        full_negative_prompt = ", ".join(neg_content)
    else:
        full_negative_prompt = str(neg_content)

    # 변수 치환
    for key, value in variables.items():
        target_key = key if key.startswith("[") else f"[{key}]"
        full_positive_prompt = full_positive_prompt.replace(target_key, value)
        
    # TODO: 나중에 유저 프롬프트까지 합쳐서 로그 남겨두는거 필요할 듯.
    return {
        "positive": full_positive_prompt,
        "negative": full_negative_prompt
    }

def generate_and_save_img(reference_image_path: str, prompt_data: dict, output_filename: str):
    """
    이미지를 생성하고 저장하는 함수
    > param reference_image: 레퍼런스 이미지 (일러스트 파일)
    > param prompt_data: 긍정/부정 프롬프트가 담긴 딕셔너리
    > param output_filename: 저장할 이미지 파일 이름
    """
    # TODO: API 키 유저가 직접 입력 (할지 안할지 모르겠음)
    if not API_KEY:
        print("에러: API 키가 설정되지 않았습니다.")
        return
    
    # 자꾸 실수하는 부분: 레퍼런스 이미지가 없거나 경로가 잘못된 경우 즉시 종료 
    if not reference_image_path or not os.path.exists(reference_image_path):
        print(f"에러: 레퍼런스 이미지 파일을 찾을 수 없습니다: {reference_image_path}")
        return

    try:
        client = genai.Client(api_key=API_KEY)
        
        # 딕셔너리에서 프롬프트 추출
        final_prompt = prompt_data.get("positive", "")
        final_negative = prompt_data.get("negative", "")

        print(f"이미지 생성 시작...")
        print(f"적용된 프롬프트(테스트 용): {final_prompt[:100]}...")

        # 레퍼런스 이미지 객체 생성
        raw_ref_image = types.RawReferenceImage(
            reference_id=1,
            reference_image=types.Image.from_file(reference_image_path),
        )
        # edit_image 호출 (레퍼런스 기반 생성)
        result = client.models.edit_image(
            model='imagen-3.0-capability-001', # 이메진 4 사용법을 찾고 있습니다...
            prompt=final_prompt,               # 추출한 긍정 프롬프트
            reference_images=[raw_ref_image],
            config=types.EditImageConfig(
                number_of_images=1,
                output_mime_type="image/png", 
                negative_prompt=final_negative, # 추출한 부정 프롬프트
            ),
        )

        if result.generated_images:
            generated_image = result.generated_images[0]
            with open(output_filename, 'wb') as f:
                f.write(generated_image.image.image_bytes)
            print(f"이미지 저장 성공: {output_filename}")
        else:
            print("이미지 생성 실패")

    except APIError as e:
        print(f"API 오류: {e}")
    except Exception as e:
        print(f"예기치 않은 오류: {e}")

def get_reference_info():
    """
    환경변수에서 이미지 경로와 파일명 추출
    return ("file_path": str, "file_name_with_ext": str)
    """
    file_path = os.getenv("REFERENCE_IMAGE_PATH")
    file_name_with_ext = os.path.basename(file_path)
    return file_path, file_name_with_ext

if __name__ == "__main__":
    # 입력 정보 가져오기
    ref_path, ref_filename = get_reference_info()
    
    if ref_path:
        # 변수 맵핑 설정
        variable_map = {
            "REFERENCE_IMG": ref_filename
        }
        prompt_data = build_prompt_from_json(MODE1_PATH, variable_map)

        # 파일명 생성 (타임스탬프)
        # TODO: uuid로 파일명 관리해야함. 근데 타임스탬프로 냅두는것도 나쁘지 않을듯?
        # TODO: 캐릭터 이름을 파일명을 통해 구분을 해야함 -> 나중에 캐릭터별로 모아두기 이런 기능 가능 (가능성은 ㅁ?ㄹ)
        # HACK: 일단은 간편하게 utc
        timestamp = datetime.now(timezone.utc).timestamp()
        output_file = f"outputs/image_{timestamp:.0f}.png" # outputs 폴더에 저장 추천
        os.makedirs("outputs", exist_ok=True) # 폴더 없으면 생성

        # 실행
        generate_and_save_img(ref_path, prompt_data, output_file)
    else:
        print("에러: 레퍼런스 이미지 경로")