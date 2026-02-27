# 프로젝트 구조

이 문서는 저장소의 디렉터리 구조, 계층별 책임, 실행 흐름, 생성물 위치를 개발자 관점에서 정리한 문서입니다.

---

- 루트
  - 서비스 안내: [README.md](../README.md)
  - 개발/운영/재현 가이드: [README_DEV.md](../README_DEV.md)

---

현재 MVP는 다음 방향으로 정리되어 있습니다.

- `backend` 중심 구조 (CLI + FastAPI)
- Gemini 이미지 생성은 `google-genai` + `GEMINI_API_KEY` 방식
- 프롬프트는 `configs/*.json` 병합 후 텍스트로 변환
- 기능 3(`master-image`)는 엔드포인트/함수 틀은 있지만 프롬프트 빌더는 아직 미구현

---

## 전체 구조

```text
CosplayAI/
├─ backend/
│  ├─ api/                      # FastAPI 앱/라우터/DI/스키마
│  │  ├─ main.py
│  │  ├─ routes_generation.py
│  │  ├─ deps.py
│  │  └─ schemas.py
│  ├─ core/                     # 환경설정(.env), 공통 경로 설정
│  │  └─ settings.py
│  ├─ domain/                   # 공용 요청/응답 모델, enum
│  │  ├─ enums.py
│  │  └─ models.py
│  ├─ services/                 # 검증/프롬프트/모델호출/저장/파이프라인
│  │  ├─ config_loader.py
│  │  ├─ prompt_builder.py
│  │  ├─ gemini_image_service.py
│  │  ├─ validators.py
│  │  ├─ storage.py
│  │  └─ pipelines.py
│  └─ cli.py                    # 로컬 테스트용 CLI 실행 진입점
├─ configs/                     # 프롬프트 템플릿(JSON)
│  ├─ common_base.json
│  ├─ mode1_general_trans.json
│  ├─ mode2_face_consistency.json
│  ├─ mode3_master_image.json   # 구조 개편 예정 (현재 프롬프트 빌드 미구현)
│  ├─ user_custom_prompts.json
│  ├─ VFX_prompt.json
│  └─ _variables_manage.txt
├─ docs/                        # 문서
│  ├─ API_SPEC.md
│  ├─ PROJECT_STRUCTURE.md
│  ├─ REQUIREMENTS_MANAGEMENT.md
│  └─ COMMIT_MESSAGE_GUIDE.md
├─ inputs/                      # 로컬 테스트 입력 이미지
│  ├─ references/
│  └─ master_faces/
├─ outputs/                     # 결과 이미지 및 메타데이터(JSON)
├─ requirements.txt
├─ .env.example                 # 환경변수 템플릿
└─ README.md
```

---

## 아키텍처 흐름

기본 흐름은 아래와 같습니다.

- `CLI 또는 API`가 요청을 받음
- `ImageGenerationPipeline`이 전체 흐름을 오케스트레이션
- 내부 서비스들이 역할 분리해서 처리
  - `validators`: 입력 경로 검증
  - `prompt_builder`: 프롬프트 텍스트 생성
  - `gemini_image_service`: Gemini 모델 호출
  - `storage`: 이미지/메타데이터 저장

즉, 구조는 다음 한 줄로 이해하면 됩니다.

- `CLI/API -> Pipeline -> (Validator + PromptBuilder + GeminiImageService + Storage)`

---

## backend 모듈 역할

### `backend/core`

- `backend/core/settings.py`
  - `.env` 파일을 읽어 설정 객체(`Settings`)를 생성합니다.
  - 프로젝트 루트 기준으로 `configs`, `inputs`, `outputs` 경로를 계산합니다.
  - 현재는 `GEMINI_API_KEY` 기반 실행만 사용합니다.
  - `.env.example`는 템플릿 문서용이며 실행 시 자동 fallback 로드하지 않습니다.

### `backend/domain`

- `backend/domain/enums.py`
  - 작업 유형(`TaskType`)을 정의합니다.
  - 예: `cosplay_basic`, `cosplay_with_master`, `master_image`

- `backend/domain/models.py`
  - CLI/API/파이프라인이 공용으로 쓰는 요청/응답 모델(Pydantic)을 정의합니다.
  - `PromptBundle`은 최종 텍스트 프롬프트와 사용한 모드 설정 파일명을 담습니다.
  - `BaseGenerationRequest`에는 공통 옵션이 포함됩니다.
    - `prompt_variables`
    - `user_custom_text`
    - `vfx_options`
    - `vfx_params`
    - `output_filename`
    - `dry_run`

### `backend/services`

- `backend/services/config_loader.py`
  - `configs/*.json` 파일을 읽어 `dict`로 반환하는 유틸 함수입니다.

- `backend/services/validators.py`
  - 입력 이미지 경로를 검증하고 `Path`로 변환합니다.
  - 상대경로는 프로젝트 루트 기준으로 해석합니다. (`inputs/...` 권장)

- `backend/services/storage.py`
  - 결과 이미지 파일 경로를 생성하고 저장합니다.
  - 메타데이터 JSON도 함께 저장합니다.
  - `dry-run`일 때는 메타데이터만 저장합니다.

- `backend/services/prompt_builder.py`
  - 모드 1/2 프롬프트를 JSON 병합 규칙에 따라 조합한 뒤 최종 텍스트 프롬프트를 만듭니다.
  - 현재 모드 1/2에서 사용하는 입력 소스:
    - `common_base.json`
    - `mode1_general_trans.json` 또는 `mode2_face_consistency.json`
    - `user_custom_prompts.json`
    - `VFX_prompt.json` (선택된 VFX만)
  - 주요 규칙:
    - 같은 키가 있으면 값 병합(예: 리스트 추가)
    - 없는 키는 마지막 `Crucial Constraints - ...` 뒤에 삽입
    - 플레이스홀더(`[REFERENCE_IMG]`, `[MASTER_IMG]`, `[HAIR_COLOR]`, `[EYE_COLOR]`) 치환
    - 최종 텍스트는 `Command`, `Crucial Constraints`, `negative_prompts(Strictly Avoid)` 블록 형식으로 생성
  - `mode3_master_image.json`은 구조 개편 예정이라 현재 `NotImplementedError`를 발생시킵니다.

- `backend/services/gemini_image_service.py`
  - `google-genai` 클라이언트로 Gemini 이미지 생성 모델을 호출합니다.
  - 참조 이미지(일러스트/마스터) + 텍스트 프롬프트를 멀티모달 `contents`로 구성합니다.
  - `generate_content(..., response_modalities=["IMAGE"])` 응답에서 이미지 바이트를 추출합니다.

- `backend/services/pipelines.py`
  - 기능 1/2/3 전체 흐름을 조립하는 메인 파이프라인입니다.
  - 처리 순서:
    - 입력 검증
    - 프롬프트 생성
    - Gemini 이미지 생성 호출
    - 결과 이미지/메타데이터 저장
    - 통합 결과(`GenerationResult`) 반환
  - 현재 기능 3은 파이프라인 함수는 존재하지만 프롬프트 빌더가 미구현이므로 실패 응답을 반환합니다.

### `backend/api`

- `backend/api/main.py`
  - FastAPI 앱 생성 및 라우터 등록

- `backend/api/deps.py`
  - FastAPI 의존성 주입용 `ImageGenerationPipeline` 생성 함수 제공

- `backend/api/routes_generation.py`
  - API 엔드포인트 정의
  - 현재 엔드포인트:
    - `GET /api/v1/health`
    - `POST /api/v1/generation/cosplay/basic`
    - `POST /api/v1/generation/cosplay/with-master`
    - `POST /api/v1/generation/master-image` (현재 프롬프트 빌더 미구현 상태)

- `backend/api/schemas.py`
  - API 전용 스키마(현재는 헬스체크 응답) 정의
  - 생성 요청/응답 모델은 `backend/domain/models.py` 공용 모델을 사용합니다.

### `backend/cli.py`

로컬 테스트용 실행 진입점입니다.

- 지원 명령:
  - `cosplay-basic`
  - `cosplay-with-master`
  - `master-image`
- 공통 옵션:
  - `--output-filename`
  - `--dry-run`
- 모드 1, 2 선택 옵션:
  - `--user-custom-text`
  - `--animal-features`
  - `--halo-vfx`
  - `--hair-color`
  - `--eye-color`

주의:

- `--hair-color`와 `--eye-color`는 함께 입력해야 합니다.
- 하나만 입력하면 CLI에서 에러를 반환합니다.

---

## 기능별 실제 흐름

### 기능 1: 일러스트 -> 코스프레 이미지 (`cosplay-basic`)

1. `illustration_path` 입력
2. `validators.py`에서 경로 검증
3. `prompt_builder.py`에서 모드 1 프롬프트 생성
4. `gemini_image_service.py`에서 Gemini 이미지 생성 호출
5. `storage.py`에서 이미지/메타데이터 저장
6. `GenerationResult` 반환

추가로 선택 옵션(VFX, 유저 커스텀 프롬프트)을 함께 넣을 수 있습니다.

### 기능 2: 일러스트 + 마스터 이미지 -> 코스프레 이미지 (`cosplay-with-master`)

1. `illustration_path`, `master_image_path` 입력
2. 두 이미지 경로 검증
3. `prompt_builder.py`에서 모드 2 프롬프트 생성
4. Gemini 멀티모달 입력으로 이미지 + 프롬프트 전달
5. 결과 저장 후 반환

기능 1과 동일하게 VFX 옵션/유저 커스텀 프롬프트를 사용할 수 있습니다.

### 기능 3: 인물 사진 -> 마스터 이미지 (`master-image`)

현재 상태:

- CLI/API 라우트/파이프라인 함수는 존재함
- `prompt_builder.py`의 `build_for_master_image()`는 미구현 (`NotImplementedError`)

즉, 구조만 준비되어 있고 실제 프롬프트 생성 로직은 다음 단계에서 구현 예정입니다.

---

## 프롬프트 구조

### 항상 기반이 되는 파일

- `configs/common_base.json`

### 모드별 파일

- `configs/mode1_general_trans.json`
- `configs/mode2_face_consistency.json`
- `configs/mode3_master_image.json` (예정, 현재 미구현)

### 선택/추가 프롬프트 파일

- `configs/user_custom_prompts.json`
  - 사용자 입력 텍스트를 `Crucial Constraints - Additions`에 주입

- `configs/VFX_prompt.json`
  - 선택 옵션 기반으로 일부 항목만 병합
  - 현재 지원:
    - `animal_features` (선택 사항)
    - `halo_vfx` (선택 사항)
    - `color_palette` (선택 사항 : `HAIR_COLOR` AND `EYE_COLOR`)

---

## 코드 순서

1. `backend/cli.py`
2. `backend/api/routes_generation.py`
3. `backend/services/pipelines.py`
4. `backend/services/prompt_builder.py`
5. `backend/services/gemini_image_service.py`
6. `backend/services/storage.py`
7. `backend/services/validators.py`
8. `backend/domain/models.py`
9. `backend/core/settings.py`

--

## 현재 상태에서 주의점

- `dry-run` 사용 시 실제 이미지 생성은 호출하지 않고 메타데이터(JSON)만 저장합니다.
- 실제 이미지 생성은 Gemini API 쿼터/과금 상태에 따라 `429 RESOURCE_EXHAUSTED`가 날 수 있습니다.
- `GenerationResult.negative_prompt` 필드는 현재 호환 목적 필드로 남아 있으며, 실제 negative 내용은 최종 `prompt` 텍스트 블록에 포함됩니다.

---
