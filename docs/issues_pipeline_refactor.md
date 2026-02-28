# Pipeline 재구성

이 문서의 목적은 `backend/services/pipelines.py`를 MVP 기준으로 재작성한 이유와 변경 기준을 재현 가능하게 정리하는 것이다.

---

## 전체 요약

- 파이프라인을 "검증 -> 프롬프트 생성 -> contents 조립 -> Gemini 호출 -> 저장"의 단일 흐름으로 단순화했다.
- 모델 입력 `contents`의 최종 순서를 파이프라인에서 명시적으로 결정하도록 변경했다.
- 모드별 이미지 역할 설명 문구를 한 곳에서 관리하고, 런타임에서 교체 가능하게 만들었다.

---

## 문제 정의

- 기존 파이프라인은 `GeminiImageService.generate_image(contents, config)` 시그니처와 호출부가 불일치했다.
- 모델에 전달되는 `contents` 순서가 코드 상에서 명확히 드러나지 않아 회귀 위험이 있었다.
- 모드별 이미지 역할 설명 문구를 변경하려면 분산된 로직을 찾아 수정해야 했다.

---

## 원인 파악

- 책임 분리 이후(`gemini_image_service.py`, `gemini_parameter_resolver.py`)에 맞게 파이프라인 오케스트레이션이 정리되지 않았다.
- "최종 입력 순서 결정" 책임이 명확히 파이프라인에 고정되지 않았다.
- 역할 문구(이미지가 무엇을 의미하는지)가 상수화/중앙화되어 있지 않았다.

---

## 해결 방안

1. 파이프라인 책임을 오케스트레이션으로 고정

- `pipelines.py`는 아래 순서만 담당:
  - 입력 경로 검증
  - `PromptBuilder`로 최종 텍스트 생성
  - `GeminiParameterResolver`로 `GenerateContentConfig` 생성
  - 최종 `contents` 조립
  - `GeminiImageService` 호출
  - 이미지/메타데이터 저장

2. 모드별 `contents` 순서 명시

```text
mode1: [text, image_role_instruction, reference_image]
mode2: [text, image_role_instruction, master_image, reference_image]
mode3: [text, image_role_instruction, person_image]
```

3. 이미지 역할 설명 문구 중앙 관리

- `DEFAULT_IMAGE_ROLE_INSTRUCTIONS`에 모드별 기본 문구를 정의
- `set_image_role_instruction(mode_config_name, instruction)`으로 런타임 교체 가능

4. resolver/service 연결 일원화

- 파이프라인에서 `resolve(...).generate_content_config`를 생성해 서비스에 전달
- 서비스는 호출/응답 처리만 수행

---

## 결과

- 파이프라인 코드가 MVP 기준으로 단순해져 흐름 파악이 쉬워졌다.
- 모드별 모델 입력 순서가 코드/메타데이터(`content_order`)로 명확해졌다.
- 역할 문구를 파이프라인 상수/메서드로 빠르게 조정할 수 있게 됐다.

---

## 관련 파일

- `backend/services/pipelines.py`
- `backend/services/gemini_parameter_resolver.py`
- `backend/services/gemini_image_service.py`
- `backend/services/prompt_builder.py`

---
