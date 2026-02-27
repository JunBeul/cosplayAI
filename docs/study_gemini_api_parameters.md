# Gemini 2.5 Flash Image 파라미터 스터디

이 문서의 목적은 `gemini-2.5-flash-image`의 이미지 생성 파라미터를 정리하고, 바로 반영할 수 있는 적용 후보를 분리해 기록하는 것이다.  
검증 기준일은 2026-02-27이다.

---

## 1. 전체 요약

- 해상도/비율은 프롬프트 텍스트 지시보다 `image_config` 파라미터 제어가 우선이다.
- 현재 프로젝트에는 입력 이미지 비율 기반 `aspect_ratio` 자동 선택 로직이 필요하다.
- `image_size`는 품질/비용 정책으로 분리해서 결정하는 것이 안전하다.
- 인증 경로(`GEMINI_API_KEY` vs Vertex AI)에 따라 일부 이미지 출력 파라미터 지원 차이를 검증해야 한다.

---

## 2. 학습 근거 정리

### 2.1 모델 스펙 (gemini-2.5-flash-image)

- 모델 ID: `gemini-2.5-flash-image`
- 입출력 모달리티: 입력 `TEXT`,`IMAGE` / 출력 `TEXT`,`IMAGE`
- 토큰 한도: 입력 32,768 / 출력 32,768
- 프롬프트당 최대 입력 이미지 수: 3
- 프롬프트당 최대 출력 이미지 수: 10
- 지원 비율: `1:1`, `3:2`, `2:3`, `3:4`, `4:3`, `4:5`, `5:4`, `9:16`, `16:9`, `21:9`
- 기본 파라미터: `temperature=1.0`, `topP=0.95`, `topK=64`, `candidateCount=1`

### 2.2 GenerationConfig/ImageConfig (Vertex REST)

- `responseModalities`
- `imageConfig.aspectRatio`
- `imageConfig.imageSize` (`1K`, `2K`, `4K`)
- `imageConfig.personGeneration` (`ALLOW_ALL`, `ALLOW_ADULT`, `ALLOW_NONE`)
- `imageConfig.imageOutputOptions.mimeType`
- `imageConfig.imageOutputOptions.compressionQuality`

### 2.3 Python SDK 필드명 (google-genai 1.65.0)

- `types.ImageConfig.aspect_ratio`
- `types.ImageConfig.image_size`
- `types.ImageConfig.person_generation`
- `types.ImageConfig.prominent_people`
- `types.ImageConfig.output_mime_type`
- `types.ImageConfig.output_compression_quality`

### 2.4 프로젝트 관점 확인 포인트

- 현재 코드의 기본 호출 경로는 `GEMINI_API_KEY` 기반이다.
- SDK 설명상 `output_mime_type`, `output_compression_quality`는 Gemini API 미지원 표기가 있으므로, Vertex AI 경로와 분리 검증이 필요하다.
- 안전성 카테고리는 기존 이슈 문서(`docs/issues_gemini_safety_category_compat.md`)의 허용 목록을 유지해야 한다.

---

## 3. 적용 후보

### 3.1 필수 적용

1. `image_config.aspect_ratio` 자동 계산
2. `image_config.image_size` 정책 적용
3. `response_modalities`를 모드별로 명시 고정

### 3.2 선택 적용

1. `image_config.person_generation` 정책화
2. `output_mime_type`, `output_compression_quality` 경로별 실험 적용
3. `candidate_count` 확장 옵션화(기본 1 유지)

---

## 4. 작업 절차(적용 설계)

1. 기준 입력 이미지의 `width`, `height`를 읽는다.
2. `r = width / height`를 계산한다.
3. 지원 비율 집합에서 `r`과의 절대 오차가 최소인 비율을 선택한다.
4. 선택 비율을 `image_config.aspect_ratio`로 전달한다.
5. `image_size`를 정책으로 결정한다.
6. 최종 적용값을 메타데이터(`resolved_image_config`)에 기록한다.

지원 비율 집합:

```text
1:1, 3:2, 2:3, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9
```

---

## 5. 확인용 예시 코드

```python
from __future__ import annotations

from pathlib import Path
from PIL import Image

SUPPORTED_ASPECT_RATIOS = [
    "1:1",
    "3:2",
    "2:3",
    "3:4",
    "4:3",
    "4:5",
    "5:4",
    "9:16",
    "16:9",
    "21:9",
]


def _ratio_value(ratio: str) -> float:
    w, h = ratio.split(":")
    return float(w) / float(h)


def pick_nearest_aspect_ratio(width: int, height: int) -> str:
    target = width / height
    return min(SUPPORTED_ASPECT_RATIOS, key=lambda r: abs(_ratio_value(r) - target))


def resolve_image_config(reference_image: Path) -> dict[str, str]:
    with Image.open(reference_image) as img:
        width, height = img.size

    aspect_ratio = pick_nearest_aspect_ratio(width, height)

    # 품질/비용 정책 예시: 기본 1K, 큰 원본은 2K
    image_size = "1K"
    if max(width, height) >= 1536:
        image_size = "2K"

    return {
        "aspect_ratio": aspect_ratio,
        "image_size": image_size,
    }
```

---

## 6. 반영 체크리스트

1. `backend/services/gemini_image_service.py`에 `image_config` 계산/주입 로직 추가
2. `backend/services/pipelines.py`에서 모드별 기준 이미지 선택 규칙 확정
3. 메타데이터에 `resolved_image_config` 저장
4. 비율 매핑 테스트(`1:1`, `16:9`, `9:16`, 경계값 근처) 추가

---

## 7. 참고 코드(초기 실험안)

```python
from google import genai
from google.genai import types
import os


def generate():
    client = genai.Client(
        vertexai=True,
        api_key=os.environ.get("GOOGLE_CLOUD_API_KEY"),
    )

    model = "gemini-2.5-flash-image"
    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text="How does AI work")],
        )
    ]

    generate_content_config = types.GenerateContentConfig(
        temperature=1,
        top_p=0.95,
        max_output_tokens=32768,
        response_modalities=["TEXT", "IMAGE"],
        safety_settings=[
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
        ],
        image_config=types.ImageConfig(
            aspect_ratio="1:1",
            image_size="1K",
            output_mime_type="image/png",
        ),
    )

    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        print(chunk.text, end="")


generate()
```

---

## 8. 출처

- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/2-5-flash-image?hl=ko
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/reference/rest/v1beta1/GenerationConfig
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/multimodal/image-generation
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/multimodal/gemini-image-generation-limitations
