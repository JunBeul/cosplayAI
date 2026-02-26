# 프로젝트 구조 설명 (MVP 기준)

이 문서는 현재 코드가 왜 이렇게 나뉘어 있는지, 그리고 어떤 순서로 읽으면 되는지를 설명합니다.

초보자 관점에서 핵심은 아래 한 줄입니다.

- `API/CLI -> 파이프라인 -> 서비스(프롬프트/검증/모델/저장)`

즉, 겉에서 요청을 받고(`API/CLI`), 가운데에서 흐름을 조립하고(`pipeline`), 실제 세부 작업은 각각의 서비스가 담당합니다.

## 현재 폴더 구조

```text
CosplayAI/
├─ backend/
│  ├─ api/                 # FastAPI 엔드포인트 (안드로이드가 호출할 서버 API)
│  ├─ core/                # 환경변수/경로 등 공통 설정
│  ├─ domain/              # 내부 데이터 구조(dataclass, enum)
│  ├─ services/            # 실제 작업 로직 (검증, 프롬프트, 저장, Imagen 호출)
│  ├─ cli.py               # 로컬 테스트용 실행기
│  └─ __init__.py
├─ configs/                # 프롬프트 템플릿 JSON
├─ docs/                   # 문서 (API, 구조 설명)
├─ inputs/                 # 테스트 입력 이미지
│  ├─ references/
│  └─ master_faces/
├─ outputs/                # 생성 결과 이미지 / 메타데이터
└─ README.md
```

## 폴더/파일 역할 (쉽게 보기)

### `backend/core`

- `backend/core/settings.py`
  - 프로젝트 루트, `configs/inputs/outputs` 경로 계산
  - `.env` 로딩 (`.env.example`는 템플릿)
  - `GEMINI_API_KEY` 읽기

### `backend/domain`

- `backend/domain/enums.py`
  - 작업 종류(`cosplay_basic`, `cosplay_with_master`, `master_image`)

- `backend/domain/models.py`
  - 요청/응답/프롬프트 결과를 담는 공용 데이터 구조
  - API 요청/응답 모델(Pydantic)과 내부 모델을 함께 관리

### `backend/services`

- `backend/services/config_loader.py`
  - JSON 파일을 안전하게 읽는 함수

- `backend/services/prompt_builder.py`
  - `configs/*.json`을 읽어서 최종 프롬프트 문자열 생성
  - `[REFERENCE_IMG]`, `[MASTER_IMG]`, `[PERSON_IMG]` 치환

- `backend/services/validators.py`
  - 입력 이미지 경로 존재 여부, 확장자 검사
  - 상대경로를 프로젝트 루트 기준으로 해석 (`inputs/...`)

- `backend/services/imagen_service.py`
  - Google Imagen API 호출 전담

- `backend/services/storage.py`
  - 결과 이미지 저장
  - 메타데이터(JSON) 저장

- `backend/services/pipelines.py`
  - 기능 1/2/3의 전체 흐름을 조립하는 중심 파일
  - 실제 구현을 가장 먼저 읽어야 하는 파일

### `backend/api`

- `backend/api/main.py`
  - FastAPI 앱 생성

- `backend/api/routes_generation.py`
  - 실제 HTTP 엔드포인트 정의
  - 요청 스키마 -> 내부 요청 모델 변환 -> 파이프라인 호출

- `backend/api/schemas.py`
  - API 전용 스키마 (현재는 Health 응답만 유지)
  - 생성 요청/응답은 `backend/domain/models.py` 공용 모델 사용

- `backend/api/deps.py`
  - FastAPI 의존성 주입 (`ImageGenerationPipeline` 재사용)

### 실행 진입점

- `backend/cli.py`
  - 로컬 테스트할 때 사용 (기능 1/2/3 모두 가능)

## 기능별 실제 흐름

### 기능 1: 일러스트 -> 코스프레

1. `API/CLI`에서 `illustration_path` 입력 받음
2. `validators.py`에서 경로/확장자 검증
3. `prompt_builder.py`에서 `mode1_general_trans.json` 기반 프롬프트 생성
4. `imagen_service.py`에서 Imagen `edit_image` 호출
5. `storage.py`에서 이미지/메타데이터 저장
6. 결과를 API/CLI로 반환

### 기능 2: 일러스트 + 마스터 이미지 -> 코스프레

1. 일러스트 + 마스터 이미지 경로 입력
2. 두 이미지 모두 검증
3. `mode2_face_consistency.json` 기반 프롬프트 생성
4. 두 reference 이미지를 함께 Imagen에 전달
5. 저장 후 응답 반환

### 기능 3: 인물 사진 -> 마스터 이미지

1. 인물 사진 경로 입력
2. 경로/확장자 검증
3. `mode3_master_image.json` 기반 프롬프트 생성
4. Imagen 호출
5. 저장 후 응답 반환

## 초보자용 코드 읽기 추천 순서

구조가 복잡해 보여도 아래 순서로 보면 이해가 빨라집니다.

1. `backend/cli.py` (기능 1/2/3 분기)
2. `backend/api/routes_generation.py` (HTTP 요청이 어떻게 내부 로직으로 들어오는지)
3. `backend/services/pipelines.py` (전체 흐름의 중심)
4. `backend/services/prompt_builder.py`
5. `backend/services/imagen_service.py`
6. `backend/services/storage.py`
7. `backend/services/validators.py`

## 왜 이렇게 나눴는가? (MVP에서도 분리한 이유)

처음에는 파일 하나로 시작해도 되지만, 기능이 3개가 되면 아래 문제가 생깁니다.

- 프롬프트 로직과 API 호출이 섞여서 수정이 어려움
- 기능 2/3 추가 시 분기문이 계속 늘어남
- API/CLI 둘 다 지원하려면 중복 코드가 생김

지금 구조는 "조금 나뉘어 보이지만", 나중에 수정할 때는 오히려 더 단순해집니다.

## 다음 리팩터링(선택)

MVP 단순화를 더 원하면 아래 정도는 줄일 수 있습니다.

1. `backend/domain/models.py` + `backend/api/schemas.py` 일부 통합
2. `services/config_loader.py`를 `prompt_builder.py`에 흡수
3. 기능 3 품질 검증 전까지 `validators.py`를 단순화

하지만 현재 구조는 학습용/확장용 균형이 괜찮은 편입니다.
