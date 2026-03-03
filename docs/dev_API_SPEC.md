# API 스펙

이 문서는 현재 Python 백엔드 프로토타입의 API 명세입니다.

**작성일 : 2026-03-01**

---

- 루트
  - 서비스 안내: [README.md](../README.md)
  - 개발/운영/재현 가이드: [README_DEV.md](../README_DEV.md)

---

현재 MVP는 빠른 검증을 위해 `JSON + 서버 로컬 파일 경로` 방식으로 입력을 받습니다.

- 장점: 구현/재현이 빠름
- 한계: 모바일 실서비스 업로드 방식(`multipart`, `asset_id`)과는 다름

---

## 기본 정보

- 로컬 서버 주소: `http://localhost:8000`
- API prefix: `/api/v1`
- 기본 응답 타입: `application/json`
- 이미지 생성 모델(기본): `gemini-2.5-flash-image`

입력 경로 규칙:

- 상대 경로는 프로젝트 루트 기준으로 해석
- 절대 경로도 허용
- 허용 확장자: `.png`, `.jpg`, `.jpeg`, `.webp`

출력 규칙:

- 이미지: `outputs/<task>_<UTC timestamp>.png`
- 메타데이터: 이미지와 동일 이름의 `.json`
- `dry_run=true`면 `outputs/dry_run_<UTC timestamp>.json`만 저장

---

## 공통 응답 형식

생성 API 3종은 모두 아래 응답 모델(`GenerationResult`)을 사용합니다.

| 필드              | 타입             | 설명                                                     |
| ----------------- | ---------------- | -------------------------------------------------------- |
| `success`         | `bool`           | 생성 성공 여부                                           |
| `task`            | `string`         | `cosplay_basic` / `cosplay_with_master` / `master_image` |
| `image_path`      | `string \| null` | 저장된 이미지 경로 (`dry_run`이면 `null`)                |
| `metadata_path`   | `string \| null` | 저장된 메타데이터 경로                                   |
| `prompt`          | `string \| null` | 최종 조립 프롬프트                                       |
| `negative_prompt` | `string \| null` | 호환용 필드(현재 구현은 `null`)                          |
| `error`           | `string \| null` | 실패 시 에러 메시지                                      |

### 성공 응답 예시

```json
{
  "success": true,
  "task": "cosplay_basic",
  "image_path": "D:\\workSpace\\CosplayAI\\outputs\\cosplay_basic_20260228_130001.png",
  "metadata_path": "D:\\workSpace\\CosplayAI\\outputs\\cosplay_basic_20260228_130001.json",
  "prompt": "Command: ...",
  "negative_prompt": null,
  "error": null
}
```

### 실패 응답 예시

```json
{
  "success": false,
  "task": "cosplay_with_master",
  "image_path": null,
  "metadata_path": null,
  "prompt": null,
  "negative_prompt": null,
  "error": "Input image not found: inputs/references/missing.png"
}
```

### Dry-run 응답 예시

```json
{
  "success": true,
  "task": "cosplay_basic",
  "image_path": null,
  "metadata_path": "D:\\workSpace\\CosplayAI\\outputs\\dry_run_20260228_130101.json",
  "prompt": "Command: ...",
  "negative_prompt": null,
  "error": null
}
```

---


## 인증 (사용자 Gemini API 키)

서비스 확장 시 운영자 키를 공유하지 않기 위해, 생성 API 호출 시 사용자 개인 키를 헤더로 전달해야 합니다.

- 필수 헤더: `X-Gemini-Api-Key: <USER_GEMINI_API_KEY>`
- 키 검증 실패 시: `403 Forbidden`
- 헤더 누락 시: `401 Unauthorized`

### API 키 사전 검증 Endpoint

- `GET /api/v1/auth/verify-key`
- 용도: 앱에서 로그인처럼 "키 입력/검증" 단계 구현

응답 예시:

```json
{
  "valid": true,
  "provider": "gemini"
}
```

---

## 1. 일러스트 -> 코스프레 이미지 생성 (기능 1)

### Endpoint

- `POST /api/v1/generation/cosplay/basic`

### Request JSON

```json
{
  "illustration_path": "inputs/references/ref_iroha.jpg",
  "prompt_variables": {
    "CHARACTER_NAME": "Iroha"
  },
  "user_custom_text": "Use soft rim light and slightly wider framing.",
  "vfx_options": ["animal_features", "halo_vfx", "color_palette", "combat_props", "wig_props"],
  "vfx_params": {
    "HAIR_COLOR": "blue",
    "EYE_COLOR": "gold",
    "COMBAT_PROP_ITEMS": "Pistol, Shield",
    "WIG_PROP_ITEMS": "천사 날개"
  },
  "output_filename": null,
  "dry_run": false
}
```

### 필드 설명

- `illustration_path` (필수): 서버에서 접근 가능한 일러스트 이미지 경로
- `prompt_variables` (선택): 템플릿 치환값
- `user_custom_text` (선택): 사용자 커스텀 문장
- `vfx_options` (선택): `animal_features`, `halo_vfx`, `color_palette`, `combat_props`, `wig_props`
- `vfx_params` (선택):
  - `color_palette` 사용 시 `HAIR_COLOR`, `EYE_COLOR` 필요
  - `combat_props` 사용 시 `COMBAT_PROP_ITEMS` 필요 (예: `Pistol, Shield`)
  - `wig_props` 사용 시 `WIG_PROP_ITEMS` 필요 (예: `천사 날개`)
- `output_filename` (선택): 출력 파일명(예: `my_result.png`)
- `dry_run` (선택): `true`면 모델 호출 없이 메타데이터만 저장

---

## 2. 일러스트 + 마스터 이미지 -> 코스프레 생성 (기능 2)

### Endpoint

- `POST /api/v1/generation/cosplay/with-master`

### Request JSON

```json
{
  "illustration_path": "inputs/references/ref_iroha.jpg",
  "master_image_path": "inputs/master_faces/master_iroha.jpg",
  "prompt_variables": {},
  "user_custom_text": "Emphasize elegant stage atmosphere and clean highlights.",
  "vfx_options": ["halo_vfx"],
  "vfx_params": {},
  "output_filename": null,
  "dry_run": false
}
```

### 필드 설명

- 기능 1 공통 필드 + 아래 필드 추가
- `master_image_path` (필수): 얼굴 일관성 기준이 되는 마스터 이미지 경로

### 권장 마스터 이미지 품질

- 정면 얼굴
- 얼굴이 충분히 크게 보이는 구도
- 밝고 균일한 조명
- 눈/코/입 가림 최소화

---

## 3. 인물 사진 -> 마스터 이미지 생성 (기능 3)

### Endpoint

- `POST /api/v1/generation/master-image`

### Request JSON

```json
{
  "person_image_path": "inputs/your/img.jpg",
  "prompt_variables": {},
  "user_custom_text": "Keep skin texture natural and use clean studio lighting.",
  "vfx_options": [],
  "vfx_params": {},
  "output_filename": null,
  "dry_run": false
}
```

### 필드 설명

- `person_image_path` (필수): 마스터 이미지를 만들 기준 인물 사진 경로
- 나머지 공통 필드는 기능 1과 동일
- `vfx_options`, `vfx_params`는 요청 모델에서 허용되지만, 현재 mode3에서는 VFX 병합을 사용하지 않음

---

## 상태 확인 (Health Check)

### Endpoint

- `GET /api/v1/health`

### Response JSON

```json
{
  "status": "ok"
}
```

---

## HTTP 상태 코드/에러 처리

- `200 OK`
  - 생성 요청 처리 완료(실패 포함)
  - 비즈니스/실행 실패는 `success=false` + `error` 메시지로 반환
- `422 Unprocessable Entity`
  - 요청 JSON 형식/타입이 Pydantic 스키마와 맞지 않을 때

대표 에러 메시지 예:

- `Input image not found: ...`
- `Unsupported image extension for ...`
- `[PROMPT_BUILDER:E_MISSING_COLOR_PALETTE_PARAMS] ...`
- `[PROMPT_BUILDER:E_MISSING_COMBAT_PROP_ITEMS] ...`
- `[PROMPT_BUILDER:E_MISSING_WIG_PROP_ITEMS] ...`
- `[GEMINI_IMAGE_SERVICE:E_API_KEY_MISSING] GEMINI_API_KEY is not set`
- `[GEMINI_IMAGE_SERVICE:E_NO_INLINE_IMAGE_DATA] ...`

---

## 호출 흐름 (앱 연동 관점)

1. 클라이언트가 이미지 경로 기준 요청 JSON 전송
2. API 라우터가 공용 요청 모델로 파싱
3. 파이프라인이 입력 검증 -> 프롬프트 조립 -> Gemini 호출/저장 수행
4. 결과 이미지/메타데이터 경로와 상태를 응답

---

## 향후 확장 (실서비스)

1. `POST /api/v1/assets/upload` 추가 (`multipart/form-data`)
2. 업로드 파일 저장 후 `asset_id` 발급
3. 생성 API 입력을 `*_path` -> `*_asset_id` 중심으로 전환
4. 장시간 작업 대비 비동기 Job API (`/jobs/{id}`) 도입

---
