# Gemini 호출 책임 분리와 응답 관측성 강화 이슈

이 문서의 목적은 `gemini_image_service.py`의 과도한 책임을 분리하고, Gemini 응답 관측성 정책을 재현 가능하게 기록하는 것이다. 현재 코드 기준으로 어떤 책임을 어디에 두는지와 적용 결과를 정리한다.

---

## 전체 요약

- `GeminiImageService`는 호출 어댑터 책임만 유지하도록 축소했다.
- 응답 파싱/요약/진단 로직은 `GeminiResponseObserver`로 분리했다.
- observer에 스키마 고정, 실패 분류 코드, 마스킹, 길이 제한, 방어 파싱 정책을 추가했다.
- 서비스 예외 메시지는 `[GEMINI_IMAGE_SERVICE:<code>] <detail>` 형식으로 통일했다.

---

## 문제 정의

- 기존 구조는 Gemini 호출, 응답 파싱, 진단 문자열 생성이 한 파일에 혼합되어 변경 영향 범위가 컸다.
- `no inline image data` 같은 실패 케이스에서 원인 분류 기준이 코드화되어 있지 않아 대응 일관성이 떨어졌다.
- 응답 요약의 형식이 암묵적이라, 메타데이터 소비 측에서 안정적인 파싱 계약을 기대하기 어려웠다.

---

## 원인 파악

- 호출 계층과 관측성 계층의 경계가 모듈 수준에서 분리되지 않았다.
- 관측성 데이터의 스키마/길이/민감정보 처리 규칙이 코드 상수로 고정되어 있지 않았다.
- 실패 케이스 분류(`BLOCKED`, `NO_CANDIDATE`, `NO_IMAGE_PART`)가 문자열 해석에 의존했다.

---

## 해결 방안

1. 모듈 책임 분리

- `backend/services/gemini_image_service.py`
  - API 키 검증
  - SDK import 검증
  - `generate_content` 실행
  - observer 호출 및 최종 예외 변환
- `backend/services/gemini_response_observer.py`
  - `extract_first_image_bytes`
  - `build_response_summary`
  - `build_no_inline_image_error`
  - safety 직렬화/텍스트 마스킹/길이 제한/방어 파싱

2. 응답 요약 스키마 고정

- `schema_version = "gemini-response-summary.v1"`
- 고정 키: `schema_version`, `candidate_count`, `candidates_truncated`, `prompt_feedback`, `candidates`

```json
{
  "schema_version": "gemini-response-summary.v1",
  "candidate_count": 1,
  "candidates_truncated": false,
  "prompt_feedback": {
    "block_reason": "",
    "block_reason_message": "",
    "safety_ratings": []
  },
  "candidates": [
    {
      "finish_reason": "",
      "safety_ratings": [],
      "has_inline_image": false,
      "text": ""
    }
  ]
}
```

3. 실패 원인 코드화

- `classify_no_inline_reason()`로 아래 코드 반환
  - `BLOCKED`
  - `NO_CANDIDATE`
  - `NO_IMAGE_PART`
  - `UNKNOWN`

4. 관측성 안전 정책

- 텍스트 길이 제한 상수화 (`MAX_TEXT_LENGTH`)
- 후보 요약/오류에 포함할 후보 수 제한 상수화
- 이메일 및 Google API 키 패턴 마스킹
- 후보/파트 목록은 누락/비정상 타입일 때 빈 리스트로 처리

5. 서비스 예외 포맷 통일

```text
[{ERROR_NAMESPACE}:{code}] {detail}
```

적용 namespace:

```text
GEMINI_IMAGE_SERVICE
```

---

## 결과

- Gemini 호출과 응답 관측성이 모듈 단위로 분리되어 변경 포인트가 명확해졌다.
- `no inline image data` 케이스에서 원인 코드 기반 분류가 가능해졌다.
- 요약 스키마가 고정되어 메타데이터 저장/후속 분석의 안정성이 개선되었다.
- 서비스 레이어 에러 메시지가 코드화되어 로그 검색성과 트러블슈팅 속도가 개선되었다.

---

## 관련 파일

- `backend/services/gemini_image_service.py`
- `backend/services/gemini_response_observer.py`

---
