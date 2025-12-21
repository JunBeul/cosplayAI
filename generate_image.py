import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import APIError
from datetime import datetime, timezone

load_dotenv() # .env 파일에서 API 키 로드
API_KEY = os.getenv("GEMINI_API_KEY")

def generate_and_save_img(reference_image:str, prompt:str, output_filename:str):
    """
    이미지를 생성하고 저장하는 함수
    > param prompt: 이미지 생성을 위한 프롬프트
    > param reference_image: 레퍼런스 이미지 (일러스트 파일)
    > param output_filename: 저장할 이미지 파일 이름
    """
    # TODO: API 키 유저가 직접 입력 (할지 안할지 모르겠음)
    if not API_KEY:
        print("에러: 키 확인 메시지 UI 계획 중")
        return
    try: # 클라이언트 초기화
        client = genai.Client()
        print(f"이미지 생성 시작")
        if reference_image:
            raw_ref_image = types.RawReferenceImage(
                reference_id=1,
                reference_image=types.Image.from_file(reference_image),
            )
            result = client.models.edit_image(
                model='imagen-3.0-capability-001',
                prompt=prompt,
                reference_images=[raw_ref_image],
                config=types.EditImageConfig(
                    number_of_images=1,
                    output_mime_type="image/png",
                ),
            )
        else:
            result = client.models.generate_images(
                model='imagen-3.0-generate-002', # 이메진4 모델로 바꿀 예정.
                prompt=prompt,
                config=dict(
                    number_of_images=1, # 토큰 감당 못함 -> 이미지 생성 1장
                    output_mime_type="image/png"  # png, jpg 고민좀 해봐야할듯
                )
            )
        if result.generated_images:
            # 첫 번째 이미지 데이터 가져오기
            generated_image = result.generated_images[0]
            # 생성된 이미지 바이트 데이터 저장
            with open(output_filename, 'wb') as f:
                f.write(generated_image.image.image_bytes)
            print(f"이미지 저장 성공: {output_filename}")
        else:
            print("이미지 생성 실패: API가 이미지를 반환하지 않았습니다.")

    except APIError as e:
        print(f"API 오류: {e}")
    except Exception as e:
        print(f"예기치 않은 오류: {e}")

def upload_img():
    """
    이미지 불러오는 함수
    > argum file_img: 이미지 파일 경로
    > argum file_name: 이미지 파일 명
    """
    file_img = os.getenv("REFERENCE_IMAGE_PATH")
    file_name = os.path.splitext(os.path.basename(file_img))[0]
    return file_img, file_name

if __name__ == "__main__":
    ref_img, ref_name = upload_img()
    # TODO: 프롬프트를 객체나 딕셔너리로 만든다음 json으로 변환해서 사용해야함.
    # HACK: 일단은 문자열.
    test_prompt = f"Take a very realistic cosplay photo of a girl dressed as a character in a [{ref_name}]. A cute Korean cosplayer who looks like a K-pop girl idol."
    
    # TODO: uuid로 파일명 관리해야함. 근데 타임스탬프로 냅두는것도 나쁘지 않을듯?
    # TODO: 캐릭터 이름을 파일명을 통해 구분을 해야함 -> 나중에 캐릭터별로 모아두기 이런 기능 가능 (가능성은 ㅁ?ㄹ)
    # HACK: 일단은 간편하게 utc
    timestamp = datetime.now(timezone.utc).timestamp()
    output_file = f"image_{timestamp:.0f}.png"
    
    generate_and_save_img(ref_img, test_prompt, output_file)
