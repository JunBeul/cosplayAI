# Gemini Safety Category 호환성 이슈

이 문서는 `google-genai` SDK enum과 `generate_content` 엔드포인트의 실제 허용 `safety_settings.category`가 다를 때 발생하는 호환성 이슈를 재현 가능하게 정리한다.

---

## 전체 요약

- `types.HarmCategory`에 존재하는 값이라도 `generate_content` API가 모두 허용하지는 않는다.
- `HARM_CATEGORY_IMAGE_*`, `HARM_CATEGORY_JAILBREAK`를 포함해 호출하면 `400 INVALID_ARGUMENT`가 발생할 수 있다.
- 해결은 엔드포인트에서 실제 허용되는 카테고리만 사용하도록 제한하는 것이다.

---

## 문제 정의

- `cosplay-with-master` 실행 시 아래 오류가 발생했다.

```text
400 INVALID_ARGUMENT
Invalid value at 'safety_settings[4].category' ... "HARM_CATEGORY_IMAGE_HARASSMENT"
...
Invalid value at 'safety_settings[9].category' ... "HARM_CATEGORY_JAILBREAK"
```

- 결과적으로 이미지 생성 호출 자체가 실패해 출력 파일이 생성되지 않았다.

---

## 원인 파악

- SDK 타입(`google.genai.types.HarmCategory`)은 다양한 카테고리를 노출하지만, 실제 `generate_content` 경로는 일부 카테고리만 허용한다.
- 코드에서 image 계열 및 jailbreak 카테고리를 안전설정에 포함하면서 서버 검증 단계에서 거절됐다.

---

## 해결 방안

- `generate_content`에서 유효한 카테고리만 사용:
  - `HARM_CATEGORY_HARASSMENT`
  - `HARM_CATEGORY_HATE_SPEECH`
  - `HARM_CATEGORY_SEXUALLY_EXPLICIT`
  - `HARM_CATEGORY_DANGEROUS_CONTENT`
  - `HARM_CATEGORY_CIVIC_INTEGRITY`
- 각 카테고리 threshold는 테스트 목적에 맞게 `BLOCK_NONE` 값으로 통일한다.
- 새 카테고리 추가 전에는 실제 호출로 유효성 확인을 수행한다.

---

## 결과

- `400 INVALID_ARGUMENT`가 재현되지 않고 호출이 정상 수행된다.
- 이후 실패는 파라미터 형식 오류가 아니라 모델/정책 결과(`IMAGE_SAFETY` 등)로 분리되어 분석 가능해진다.

---

## 관련 파일

- `backend/services/gemini_image_service.py`
- `outputs/cosplay_with_master_*.json`
- `docs/issues_no_inline_image_data_runbook.md`

---
