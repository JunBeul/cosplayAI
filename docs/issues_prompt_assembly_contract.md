# 멀티이미지 프롬프트 조립 규약 이슈

이 문서는 `cosplay-with-master` 경로에서 멀티이미지 입력을 어떤 순서/역할로 조립해야 하는지 계약(Contract) 형태로 정리한다.

---

## 전체 요약

- 같은 모델/프롬프트라도 이미지 조립 순서와 역할 지시 강도에 따라 출력 품질이 크게 달라진다.
- 현재 표준은 "텍스트 우선 + 이미지 번호 명시 + 이미지별 역할 라벨 interleave"다.
- 조립 규약을 코드와 문서로 고정해 재발을 방지한다.

---

## 문제 정의

- 이전 구조에서는 illustration이 과도하게 보존되어, 결과가 레퍼런스 복제/크롭처럼 보이는 케이스가 반복됐다.
- 역할 힌트와 실제 이미지 전달 순서가 약하거나 모호하면 모델 해석이 흔들렸다.

---

## 원인 파악

- 멀티모달 입력에서 모델은 "순서 + 인접 텍스트"를 함께 해석한다.
- identity 우선(master)과 스타일/구도 우선(illustration)을 명확히 분리하지 않으면 기준 이미지가 뒤바뀔 수 있다.

---

## 해결 방안

- 2장 입력(`cosplay-with-master`) 규약:
  1. `prompt.text`
  2. `Image 1 is the master face reference... Image 2 is the illustration reference...`
  3. master 역할 라벨 텍스트
  4. master 이미지
  5. illustration 역할 라벨 텍스트 (`Do not copy/crop/trace` 포함)
  6. illustration 이미지
- 1장 입력(`cosplay-basic`) 규약:
  - 단일 레퍼런스 힌트 + 이미지 1장
- 역할 힌트 로직은 `_build_reference_contents()` 내부에서 일괄 구성한다.

---

## 결과

- identity 우선순위가 명확해져 얼굴 일관성 품질이 안정화됐다.
- 조립 흐름이 한 함수에 모여 변경 영향 범위가 줄었다.
- 향후 프롬프트 실험 시 수정 지점이 명확해졌다.

---

## 관련 파일

- `backend/services/gemini_image_service.py`
- `backend/services/pipelines.py`
- `configs/mode2_face_consistency.json`
- `docs/issues_img_reference_order.md`

---
