# 프로젝트 구조

이 문서는 저장소의 디렉터리 구조, 계층별 책임, 실행 흐름, 생성물 위치를 개발자 관점에서 정리한 문서입니다.

**작성일 : 2026-03-01**

---

- 루트
  - 서비스 안내: [README.md](../README.md)
  - 개발/운영/재현 가이드: [README_DEV.md](../README_DEV.md)

---

현재 MVP는 다음 방향으로 정리되어 있습니다.

- `backend` 중심 구조 (CLI + FastAPI)
- Gemini 이미지 생성은 `google-genai` + `GEMINI_API_KEY` 방식
- 프롬프트는 `configs/*.json` 병합 후 텍스트로 변환
- 기능 1/2/3(`master-image` 포함) 모두 동일 파이프라인으로 동작

---

## 전체 구조

```text
CosplayAI/
├─ backend/
│  ├─ api/                             # FastAPI 앱/라우터/DI/스키마
│  │  ├─ main.py
│  │  ├─ routes_generation.py
│  │  ├─ deps.py
│  │  └─ schemas.py
│  ├─ core/                            # 환경설정(.env), 공통 경로
│  │  └─ settings.py
│  ├─ domain/                          # 공용 요청/응답 모델, enum
│  │  ├─ enums.py
│  │  └─ models.py
│  ├─ services/                        # 검증/프롬프트/파라미터/모델호출/저장/파이프라인
│  │  ├─ config_loader.py
│  │  ├─ prompt_builder.py
│  │  ├─ gemini_parameter_resolver.py
│  │  ├─ gemini_response_observer.py
│  │  ├─ gemini_image_service.py
│  │  ├─ validators.py
│  │  ├─ storage.py
│  │  └─ pipelines.py
│  └─ cli.py                           # 로컬 테스트용 CLI 진입점
├─ configs/                            # 프롬프트 템플릿(JSON)
│  ├─ common_base.json
│  ├─ mode1_general_trans.json
│  ├─ mode2_face_consistency.json
│  ├─ mode3_master_image.json
│  ├─ user_custom_prompts.json
│  ├─ VFX_prompt.json
│  ├─ props_catalog.json
│  └─ _variables_manage.txt
├─ docs/                               # 개발/이슈/학습 문서
│  ├─ dev_API_SPEC.md
│  ├─ dev_PROJECT_STRUCTURE.md
│  └─ ...
├─ inputs/                             # 로컬 테스트 입력 이미지
│  ├─ references/
│  └─ master_faces/
├─ outputs/                            # 결과 이미지 및 메타데이터(JSON)
├─ requirements.txt
├─ .env.example
├─ README.md
└─ README_DEV.md
```

---

## 아키텍처 흐름

기본 흐름은 아래와 같습니다.

- `CLI 또는 API`가 요청을 받음
- `ImageGenerationPipeline`이 전체 흐름을 오케스트레이션
- 내부 서비스가 역할 분리 처리
  - `validators`: 입력 경로/확장자 검증
  - `prompt_builder`: 모드별 프롬프트 병합/검증/치환
  - `gemini_parameter_resolver`: `GenerateContentConfig` 해석
  - `gemini_image_service`: Gemini 호출
  - `gemini_response_observer`: 응답 요약/진단 메시지 생성
  - `storage`: 이미지/메타데이터 저장

한 줄 요약:

- `CLI/API -> Pipeline -> (Validator + PromptBuilder + ParameterResolver + GeminiImageService + Storage)`

---

## backend 모듈 역할

### `backend/core`

- `backend/core/settings.py`
  - `.env`를 읽어 설정 객체(`Settings`)를 생성
  - `project_root`, `configs`, `inputs`, `outputs` 경로 계산
  - `GEMINI_API_KEY`, 모델명(`gemini-2.5-flash-image`) 관리

### `backend/domain`

- `backend/domain/enums.py`
  - 작업 유형(`TaskType`) 정의
  - `cosplay_basic`, `cosplay_with_master`, `master_image`

- `backend/domain/models.py`
  - CLI/API/파이프라인 공용 요청/응답 모델
  - 공통 요청 필드: `prompt_variables`, `user_custom_text`, `vfx_options`, `vfx_params`, `output_filename`, `dry_run`
  - 공통 응답 모델: `GenerationResult`

### `backend/services`

- `backend/services/config_loader.py`
  - JSON 설정 파일 로드 유틸

- `backend/services/validators.py`
  - 입력 이미지 경로 검증 (`.png`, `.jpg`, `.jpeg`, `.webp`)
  - 상대경로는 프로젝트 루트 기준 해석

- `backend/services/prompt_builder.py`
  - 모드별 규칙(`MODE_RULES`)에 따라 JSON 프롬프트 병합
  - 정적 검증(키/스키마/모드/VFX 옵션) 수행
  - 플레이스홀더 치환: `REFERENCE_IMG`, `MASTER_IMG`, `PERSON_IMG`, `HAIR_COLOR`, `EYE_COLOR`, `COMBAT_PROP_ITEMS`, `WIG_PROP_ITEMS`, `CHARACTER_NAME`
  - mode1/mode2는 VFX 병합 사용, mode3는 VFX 병합 미사용(`use_vfx=False`)

- `backend/services/gemini_parameter_resolver.py`
  - Gemini `GenerateContentConfig`를 중앙에서 구성
  - `image_config`/`safety_settings` 정책 적용
  - mode3는 기본 `3:4`, `1K` 정책 오버라이드 적용

- `backend/services/gemini_response_observer.py`
  - Gemini 응답에서 이미지 파트 추출
  - 응답 요약(`ResponseSummary`) 생성
  - `E_NO_INLINE_IMAGE_DATA` 진단 메시지 생성

- `backend/services/gemini_image_service.py`
  - Gemini SDK 호출 전담
  - API 키/SDK/응답 유효성 검증 및 표준 에러 생성

- `backend/services/storage.py`
  - 결과 이미지/메타데이터 저장
  - `dry-run` 시 메타데이터 JSON만 저장

- `backend/services/pipelines.py`
  - 기능 1/2/3 공통 생성 파이프라인
  - 처리 순서:
    1. 입력 검증
    2. 프롬프트 생성
    3. 파라미터 해석
    4. 멀티모달 `contents` 구성 (`text`, `image_role_instruction`, `image...`)
    5. Gemini 호출
    6. 결과 저장
    7. `GenerationResult` 반환

### `backend/api`

- `backend/api/main.py`
  - FastAPI 앱 생성/라우터 등록

- `backend/api/deps.py`
  - `ImageGenerationPipeline` DI 제공 (`lru_cache`)

- `backend/api/routes_generation.py`
  - 엔드포인트
    - `GET /api/v1/health`
    - `POST /api/v1/generation/cosplay/basic`
    - `POST /api/v1/generation/cosplay/with-master`
    - `POST /api/v1/generation/master-image`

- `backend/api/schemas.py`
  - API 전용 스키마(`HealthResponseSchema`)

### `backend/cli.py`

로컬 실행 진입점.

- 지원 명령
  - `cosplay-basic`
  - `cosplay-with-master`
  - `master-image`
- 공통 옵션
  - `--output-filename`
  - `--dry-run`
- mode1/mode2 선택 옵션
  - `--user-custom-text`
  - `--animal-features`
  - `--halo-vfx`
  - `--hair-color`
  - `--eye-color`
  - `--combat-prop` (반복 입력 가능)
  - `--wig-prop` (반복 입력 가능)

주의:

- `--hair-color`와 `--eye-color`는 함께 입력해야 함
- 하나만 전달 시 CLI가 즉시 에러 반환
- `--combat-prop`, `--wig-prop`는 `configs/props_catalog.json`의 key만 허용
- `--combat-prop`, `--wig-prop`는 중복 key 입력 시 자동 제거(입력 순서 유지)

---

## 기능별 실제 흐름

### 기능 1: 일러스트 -> 코스프레 이미지 (`cosplay-basic`)

1. `illustration_path` 검증
2. mode1 프롬프트 생성
3. `contents = [text, role_instruction, reference_image]`
4. Gemini 호출 후 결과 저장
5. `GenerationResult` 반환

### 기능 2: 일러스트 + 마스터 -> 코스프레 이미지 (`cosplay-with-master`)

1. `illustration_path`, `master_image_path` 검증
2. mode2 프롬프트 생성
3. `contents = [text, role_instruction, master_image, reference_image]`
4. Gemini 호출 후 결과 저장
5. `GenerationResult` 반환

### 기능 3: 인물 사진 -> 마스터 이미지 (`master-image`)

1. `person_image_path` 검증
2. mode3 프롬프트 생성
3. `contents = [text, role_instruction, person_image]`
4. Gemini 호출 후 결과 저장
5. `GenerationResult` 반환

---

## 프롬프트 구조

### 기반/모드 파일

- 기반: `configs/common_base.json` (mode1/mode2)
- mode1: `configs/mode1_general_trans.json`
- mode2: `configs/mode2_face_consistency.json`
- mode3: `configs/mode3_master_image.json` (현재 실제 사용 중)

### 추가 파일

- `configs/user_custom_prompts.json`
  - `user_custom_text`를 `Additions`에 반영

- `configs/VFX_prompt.json`
  - mode1/mode2에서 선택된 옵션만 병합
  - 지원 옵션
    - `animal_features`
    - `halo_vfx`
    - `color_palette` (`HAIR_COLOR`, `EYE_COLOR` 필요)
    - `combat_props` (`COMBAT_PROP_ITEMS` 필요)
    - `wig_props` (`WIG_PROP_ITEMS` 필요)

- `configs/props_catalog.json`
  - 선택형 소품 key를 label로 매핑하는 카탈로그
  - 섹션
    - `combat_props`
    - `wig_props`

---

## 코드 읽기 순서

1. `backend/cli.py`
2. `backend/api/routes_generation.py`
3. `backend/services/pipelines.py`
4. `backend/services/prompt_builder.py`
5. `backend/services/gemini_parameter_resolver.py`
6. `backend/services/gemini_image_service.py`
7. `backend/services/gemini_response_observer.py`
8. `backend/services/storage.py`
9. `backend/services/validators.py`
10. `backend/domain/models.py`
11. `backend/core/settings.py`

---

## 현재 상태에서 주의점

- `dry-run=true`면 모델 호출 없이 메타데이터 JSON만 저장
- Gemini 사용량/쿼터/정책 상태에 따라 `429 RESOURCE_EXHAUSTED` 또는 차단 응답 가능
- `GenerationResult.negative_prompt`는 호환 목적 필드이며 현재 `null`
- 이미지 경로 유효성/확장자 검증 실패는 `success=false`와 에러 메시지로 반환
