# `no inline image data` 대응 Runbook

이 문서는 `Gemini image response returned no inline image data` 오류 발생 시, 원인을 빠르게 분류하고 복구하는 절차를 정리한다.

---

## 전체 요약

- 이 오류는 "API 호출 실패"가 아니라 "응답 후보는 있으나 이미지 바이트가 비어 있음"을 의미한다.
- 특히 `finish_reason=IMAGE_SAFETY`면 안전 정책에 의해 이미지 파트가 차단된 상태다.
- 응답 요약(`finish_reason`, `safety_ratings`, `prompt_feedback`)을 확인하면 원인 분류가 가능하다.

---

## 문제 정의

- 증상:

```text
Gemini image response returned no inline image data.
candidates=1 | candidate1, finish_reason=FinishReason.IMAGE_SAFETY
```

- 후보(`candidates`)는 존재하지만 `inline_data.data`가 없어 이미지 저장 단계로 진행되지 못한다.

---

## 원인 파악

- `IMAGE_SAFETY`: 모델 응답은 생성됐으나 이미지 안전 필터에서 차단.
- `STOP` + no inline: 텍스트만 반환되거나 응답 파트 구조가 기대와 다른 경우.
- `candidates=0`: 상위 정책 차단 또는 일시적 서비스 이슈 가능성.

---

## 해결 방안

- 1차 확인:
  - `gemini_response_summary.candidates[].finish_reason`
  - `gemini_response_summary.candidates[].safety_ratings`
  - `gemini_response_summary.prompt_feedback`
- `IMAGE_SAFETY` 대응:
  - 프롬프트에 성인 조건 명시 강화(`adult`, `mid-20s+`, `no minor appearance`)
  - 얼굴 치환처럼 보이는 문구 완화(`with the face of` -> `identity reference`)
  - 필요한 경우 안전한 fallback 프롬프트로 1회 재시도
- no-inline 일반 대응:
  - 입력 이미지 순서/역할 힌트 재검증
  - prompt 구성 변경 후 재시도

---

## 결과

- 실패 원인이 "호출 오류"인지 "정책 차단"인지 빠르게 분리된다.
- `IMAGE_SAFETY` 패턴이 누적되면 프롬프트/정책 조정 포인트를 체계적으로 개선할 수 있다.

---

## 관련 파일

- `backend/services/gemini_image_service.py`
- `backend/services/pipelines.py`
- `outputs/cosplay_with_master_*.json`
- `docs/issues_response_observability.md`

---
