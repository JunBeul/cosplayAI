# Gemini 응답 관측성(Observability) 이슈 정리

이 문서는 이미지 생성 실패/품질 이슈를 빠르게 진단하기 위해 응답 요약 정보를 어디에, 어떤 형태로 남기는지 기준을 정리한다.

---

## 전체 요약

- 단순 성공/실패 플래그만으로는 원인 분석이 어렵다.
- `gemini_response_summary`에 `finish_reason`, `safety_ratings`, `prompt_feedback`를 저장하면 재현성과 진단 속도가 크게 개선된다.
- 출력 메타데이터(JSON) 기반으로 이슈를 추적하도록 표준화했다.

---

## 문제 정의

- 기존에는 실패 시 고정 메시지 중심이라, 실제 Gemini 응답 맥락을 알기 어려웠다.
- 성공 케이스라도 품질 이상(레퍼런스 과보존 등) 원인을 로그에서 분리하기 어려웠다.

---

## 원인 파악

- 모델 응답은 후보 단위 정보(`finish_reason`, `safety_ratings`)를 제공하지만, 저장하지 않으면 실행 시점 이후 분석이 불가능하다.
- CLI 요약 출력만으로는 멀티모달 응답 구조를 복원할 수 없다.

---

## 해결 방안

- `generate_image()` 단계에서 응답 요약을 추출:
  - `candidate_count`
  - `candidates[].finish_reason`
  - `candidates[].safety_ratings`
  - `prompt_feedback.block_reason`
  - `prompt_feedback.safety_ratings`
- 파이프라인 메타데이터에 `gemini_response_summary`로 저장.
- `no inline image data` 오류 메시지에도 가능한 범위의 응답 요약을 포함.

---

## 결과

- 실패 케이스에서 정책 차단 여부를 즉시 판단 가능해졌다.
- 성공/실패를 넘어서 "왜 그런 결과가 나왔는지"를 실행 후에도 추적할 수 있다.
- 팀 내 이슈 문서화와 회귀 점검이 쉬워졌다.

---

## 관련 파일

- `backend/services/gemini_image_service.py`
- `backend/services/pipelines.py`
- `outputs/cosplay_with_master_*.json`

---
