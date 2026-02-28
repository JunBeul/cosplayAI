# Gemini Parameter Resolver 분리 이슈

이 문서의 목적은 Gemini 호출 파라미터 해석 로직을 `gemini_image_service.py`에서 분리해 `gemini_parameter_resolver.py`로 독립시킨 이유와 기준을 재현 가능하게 정리하는 것이다.

---

## 전체 요약

- Gemini 호출 서비스에서 파라미터 정책 결정을 분리해 책임 경계를 명확히 했다.
- `gemini_parameter_resolver.py`가 호출 정책(고정 generation/safety + mode별 image_config 해석)을 단일 진입점으로 관리한다.
- `gemini_image_service.py`는 Gemini API 호출과 응답 처리만 담당하도록 축소했다.

---

## 문제 정의

- 기존 구조에서 호출 서비스가 정책 결정까지 함께 담당하면 변경 포인트가 커지고, 회귀 위험이 커진다.
- `temperature`, `top_p`, `image_config`, `safety_settings` 같은 정책값이 호출 코드에 섞이면 운영 튜닝 시 코드 영향 범위를 빠르게 파악하기 어렵다.
- 이미지 비율/사이즈 계산 규칙이 분산되면 모드별 동작 일관성을 보장하기 어렵다.

---

## 원인 파악

- 호출 계층(어댑터)과 정책 계층(결정기)의 역할 분리가 부족했다.
- generation/safety 정책 결정과 SDK 매핑(`GenerateContentConfig`)이 호출 로직과 결합되어 있었다.
- 파라미터 조정 시 서비스 코드까지 수정해야 하는 구조라 변경 비용이 높았다.

---

## 해결 방안

1. 모듈 책임 분리

- `backend/services/gemini_parameter_resolver.py`
  - 고정 generation 파라미터 관리 (`temperature`, `response_modalities`, `top_p`, `candidate_count`)
  - 고정 `safety_settings` 관리
  - `image_config` 해석 (`aspect_ratio`, `image_size`, 첫 번째 레퍼런스 이미지 기준)
  - `types.GenerateContentConfig` 생성
- `backend/services/gemini_image_service.py`
  - API 키 검증
  - SDK import/클라이언트 호출
  - 응답 이미지 추출/요약

2. 이미지 설정 해석 규칙 고정

- 비율/사이즈 계산은 **첫 번째 레퍼런스 이미지 기준**으로 수행
- 마스터 이미지 여부는 해석 로직에 반영하지 않음

3. 고정 정책 명시

- `temperature`: `1.0`
- `response_modalities`: `["IMAGE"]`
- `top_p`: `0.95`
- `candidate_count`: `1`
- `safety_settings`: 프로젝트 고정 목록 사용

4. 에러 형식 통일

- Resolver 예외는 아래 형식을 사용

```text
[{ERROR_NAMESPACE}:{code}] {detail}
```

적용 namespace:

```text
GEMINI_PARAMETER_RESOLVER
```

---

## 결과

- 호출 서비스와 정책 결정 로직이 분리되어 코드 가독성과 유지보수성이 개선되었다.
- 정책 수정 시 `gemini_parameter_resolver.py` 중심으로 변경할 수 있어 영향 범위가 명확해졌다.
- MVP 기준에서 외부 입력 경로를 줄여 동작 예측 가능성과 운영 단순성이 높아졌다.

---

## 관련 파일

- `backend/services/gemini_parameter_resolver.py`
- `backend/services/gemini_image_service.py`
- `backend/services/gemini_response_observer.py`

---
