# CosplayAI

## 프로젝트 개요

일러스트를 입력하면 실사 코스프레 이미지로 변환하는 안드로이드 앱을 목표로 합니다. 현재는 Python 스크립트로 이미지 생성 흐름을 검증하는 프로토타입 단계입니다.

## 계획 (초안)

- 프롬프트 템플릿 및 캐릭터 메타데이터 JSON 설계
- 이미지 업로드/미리보기 UI 설계
- Android 앱 + 서버(API 프록시) 아키텍처 정의
- 모델 호출 비용/크레딧 관리 및 에러 핸들링 개선

## 현재 구현 상태

- `generate_image.py`에서 Google GenAI(Imagen) 모델을 호출해 이미지를 생성/편집합니다.
- `generate_and_save_image(reference_image, prompt, output_filename)`
  - reference 이미지가 있으면 `edit_image`로 변환
  - 없으면 `generate_images`로 신규 생성
- `upload_img()`는 `.env`의 `REFERENCE_IMAGE_PATH`를 읽어 프롬프트에 파일명을 반영합니다.
- 출력 파일명은 `image_<UTC 타임스탬프>.png` 형식으로 저장됩니다.

## 요구 사항

- Python 3.9+ (권장)
- `google-genai`
- `python-dotenv`

## 설치

```bash
pip install google-genai python-dotenv
```

## 환경 변수

`.env` 파일에 아래 값을 설정합니다.

```
GEMINI_API_KEY=YOUR_KEY
REFERENCE_IMAGE_PATH=path/to/your/reference.png
```

## 실행 방법

```bash
python generate_image.py
```

실행되면 현재 작업 디렉터리에 결과 이미지가 저장됩니다.

## 참고

- Google Imagen 모델 사용 (`imagen-3.0-capability-001`, `imagen-3.0-generate-002`)
