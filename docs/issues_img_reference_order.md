# 이미지 입력 순서 이슈

이 문서는 `cosplay-with-master` 경로에서 이미지 참조 순서 문제를 분석하고, 원인, 해결 방안, 결과를 재현 가능하게 기록하기 위한 문서다.
동일한 증상이 발생했을 때 빠르게 원인을 파악하고 동일한 수정 방향을 적용할 수 있도록 기준 정보를 제공한다.

---

## 전체 요약

- `cosplay-with-master`에서 입력 이미지는 원래 `illustration -> master` 순서로 파이프라인에 전달되었다.
- 생성 품질 이슈(레퍼런스 복제/크롭처럼 보이는 결과)가 반복되어, 모델에 전달되는 `contents`의 순서와 역할 지시를 재정렬했다.
- 현재는 모델 입력을 `텍스트 -> (Image 1=master, Image 2=illustration 힌트) -> master 관련 지시 + master 이미지 -> illustration 관련 지시 + illustration 이미지` 구조로 구성한다.

---

## 문제 정의

- 동일 프롬프트/동일 모델 조건에서도 API 경로에서 결과가 레퍼런스 이미지에 과도하게 끌리는 현상이 있었다.
- 일부 결과는 실패가 아니라 성공(`finish_reason=STOP`, `has_inline_image=true`)이지만 시각적으로 레퍼런스 재현에 가까웠다.
- 실패 케이스에서는 `Gemini image response returned no inline image data`와 함께 `finish_reason=IMAGE_SAFETY`가 확인되기도 했다.

---

## 원인 파악

- 핵심 원인은 "모델이 어떤 이미지를 어떤 역할로 해석하는지"를 충분히 강하게 고정하지 못한 점이었다.
- 파이프라인 내부 기준 순서와 실제 모델 입력에서의 역할 지시가 어긋나거나 약하면, 모델이 illustration을 주된 기준으로 과하게 보존할 수 있다.
- 추가로 safety 설정 실험 중 `generate_content`에서 지원하지 않는 카테고리(`HARM_CATEGORY_IMAGE_*`, `HARM_CATEGORY_JAILBREAK`)를 넣어 `400 INVALID_ARGUMENT`가 발생한 이슈가 있었다.

---

## 해결 방안

- 입력 순서를 모델 관점에서 명시적으로 재구성:
  - `prompt.text` 먼저 전달
  - `Image 1 = master`, `Image 2 = illustration` 역할 힌트 추가
  - master 이미지 앞에 identity 우선 지시 문구 추가
  - illustration 이미지 앞에 pose/costume/scene 용도 및 `Do not copy/crop/trace` 문구 추가
- 역할 힌트 로직을 분리 함수 대신 `_build_reference_contents()` 내부로 통합해 흐름을 단순화했다.
- safety 설정은 `generate_content`에서 유효한 카테고리만 사용하도록 정리했다.

---

## 결과

- 모델이 master 이미지를 identity 기준으로 해석하도록 유도 강도가 올라갔다.
- 순서/역할 지시를 한 곳에서 관리하게 되어 유지보수성이 좋아졌다.
- 실패 시 원인 분석을 위해 `gemini_response_summary`에 `finish_reason`, `safety_ratings` 요약이 기록되도록 개선되어 디버깅 속도가 향상됐다.

---

## 관련 파일

- `backend/services/gemini_image_service.py`
- `backend/services/pipelines.py`
- `configs/mode2_face_consistency.json`
- `outputs/cosplay_with_master_*.json`

---
