# CosplayAI

애니메이션 일러스트를 기반으로 코스프레 실사 이미지를 생성하는 서비스를 목표로 하는 프로젝트입니다.

---

개발/운영/재현 가이드는 [`README_DEV.md`](README_DEV.md)를 참고해주세요.

---

## 1. 프로젝트 개요

CosplayAI는 다음과 같은 사용자 경험을 목표로 합니다.

- 사용자가 업로드한 애니메이션 일러스트를 실사 코스프레 이미지로 변환
- 마스터 얼굴 이미지를 활용해 얼굴 일관성을 강화한 코스프레 이미지 생성
- 인물 사진을 기반으로 마스터 이미지 생성 (예정)

현재는 안드로이드 앱과 연동될 백엔드 MVP를 중심으로 개발 중입니다.

---

## 2. 핵심 기능

1. 일러스트 -> 코스프레 실사 이미지 생성
2. 일러스트 + 마스터 이미지 -> 얼굴 일관성 강화 코스프레 이미지 생성
3. 인물 사진 -> 마스터 이미지 생성 (구조 준비, 상세 로직 구현 예정)

추가로 백엔드 MVP에는 다음 기능이 포함되어 있습니다.

- FastAPI 기반 API 서버
- 로컬 검증용 CLI 실행 도구
- JSON 기반 프롬프트 설계/병합 구조
- 생성 결과 메타데이터 저장

---

## 3. 기술 스택

### Backend / API

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Uvicorn](https://img.shields.io/badge/Uvicorn-2C3E50?style=for-the-badge&logo=uvicorn&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-E92063?style=for-the-badge&logo=pydantic&logoColor=white)

### AI / Config / Runtime

![Google GenAI](https://img.shields.io/badge/Google%20GenAI-4285F4?style=for-the-badge&logo=google&logoColor=white)
![Gemini 2.5 Flash Image](https://img.shields.io/badge/Gemini%202.5%20Flash%20Image-1A73E8?style=for-the-badge&logo=googlegemini&logoColor=white)
![python-dotenv](https://img.shields.io/badge/python--dotenv-222222?style=for-the-badge&logo=dotenv&logoColor=white)
![JSON](https://img.shields.io/badge/JSON-000000?style=for-the-badge&logo=json&logoColor=white)

---

## 4. 프로젝트 로드맵

- [x] 기획
- [x] 프롬프트 설계 기반 구축
- [x] 백엔드 코어 로직 구현
- [x] AI 모델 연동 구현
- [x] API 서버 / 로컬 실행 도구 구성
- [ ] 생성 품질 개선 및 프롬프트 튜닝
- [ ] 클라이언트(안드로이드) UI/UX 구현
- [ ] 앱-서버 연동 구현
- [ ] 테스트 / 안정화
- [ ] 배포
- [ ] 이슈 분석 / 회고 문서화(`docs/`)

### 현재 상태 요약

- 백엔드 MVP(프롬프트 조립, 모델 호출, API/CLI) 중심으로 구현 중
- 안드로이드 앱 UI 및 앱-서버 연동은 아직 미구현
- 전체 구조는 정리되었고, 품질 개선/통합 단계가 남아 있음

---

## 5. 프로젝트 프리뷰

> 추가 예정

---

## 6. 프로젝트 포인트

> 추가 예정

---

## 7. 프로젝트 한계 및 개선점

> 추가 예정

---

## 8. 문서

<details>
<summary>문서 목록 보기 / 숨기기</summary>

<br />

| 분류        | 문서                                                                                          | 설명                                           |
| ----------- | --------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| 개발 온보딩 | [`README_DEV.md`](README_DEV.md)                                                              | 개발 환경 설정, CLI/API 실행 방법, 트러블슈팅  |
| 개발        | [`dev_API_SPEC.md`](docs/dev_API_SPEC.md)                                                     | 요청/응답 형식 및 엔드포인트 설명              |
| 개발        | [`dev_PROJECT_STRUCTURE.md`](docs/dev_PROJECT_STRUCTURE.md)                                   | 현재 프로젝트 구조와 모듈 역할 설명            |
| 개발        | [`dev_REQUIREMENTS_MANAGEMENT.md`](docs/dev_REQUIREMENTS_MANAGEMENT.md)                       | `requirements.txt` 관리 기준                   |
| 개발        | [`dev_DOCUMENTATION_GUIDE.md`](docs/dev_DOCUMENTATION_GUIDE.md)                               | 문서 작성 가이드                               |
| 개발        | [`dev_BRANCH_GUIDE.md`](docs/dev_BRANCH_GUIDE.md)                                             | 브랜치 운영 기준 가이드                        |
| 개발        | [`dev_COMMIT_MESSAGE_GUIDE.md`](docs/dev_COMMIT_MESSAGE_GUIDE.md)                             | 커밋 타입 규칙 및 메시지 작성 가이드           |
| 개발        | [`dev_PYTHON_COMMENT_GUIDE.md`](docs/dev_PYTHON_COMMENT_GUIDE.md)                             | 파이썬 주석 작성 가이드                        |
| 이슈        | [`issues_img_reference_order.md`](docs/issues_img_reference_order.md)                         | 이미지 입력 순서에 따른 전달 이슈              |
| 이슈        | [`issues_gemini_safety_category_compat.md`](docs/issues_gemini_safety_category_compat.md)     | `safety_settings.category` 호환성 이슈         |
| 이슈        | [`issues_no_inline_image_data_runbook.md`](docs/issues_no_inline_image_data_runbook.md)       | `no inline image data` 대응 Runbook            |
| 이슈        | [`issues_response_observability.md`](docs/issues_response_observability.md)                   | Gemini 응답 관측성 이슈 정리                   |
| 이슈        | [`issues_gemini_service_observer_split.md`](docs/issues_gemini_service_observer_split.md)     | Gemini 호출 책임 분리 및 observer 정책 강화    |
| 이슈        | [`issues_gemini_parameter_resolver_split.md`](docs/issues_gemini_parameter_resolver_split.md) | Gemini 파라미터 resolver 분리 이유 및 기준     |
| 이슈        | [`issues_pipeline_refactor.md`](docs/issues_pipeline_refactor.md)                             | 파이프라인 재구성 및 모드별 입력 순서 고정     |
| 이슈        | [`issues_prompt_assembly_contract.md`](docs/issues_prompt_assembly_contract.md)               | 멀티이미지 프롬프트 조립 규약                  |
| 이슈        | [`issues_temp_prompt_builder_refactor.md`](docs/issues_temp_prompt_builder_refactor.md)       | prompt builder 구조 개선/검증 이슈 정리        |
| 학습        | [`study_gemini_api_parameters.md`](docs/study_gemini_api_parameters.md)                       | 이미지 생성 파라미터 정리, 있는 적용 후보 기록 |
|             |                                                                                               |                                                |
| 개발        | [`dev_*`]()                                                                                   | 개발 문서 추가 포멧                            |
| 이슈        | [`issues_*`]()                                                                                | 이슈 문서 추가 포멧                            |
| 학습        | [`study_*`]()                                                                                 | 학습 문서 추가 포멧                            |

</details>

---
