# API 명세서 (MVP, JSON 요청/응답)

이 문서는 현재 Python 백엔드 프로토타입의 API 명세입니다.

현재 MVP는 빠른 검증을 위해 `JSON + 서버 로컬 파일 경로` 방식으로 입력을 받습니다.

- 장점: 구현이 빠름
- 단점: 안드로이드 실서비스 방식과는 다름

실서비스 단계에서는 `multipart/form-data` 업로드 또는 `asset_id` 방식으로 확장하는 것을 권장합니다.

## 기본 정보

- 로컬 서버 주소: `http://localhost:8000`
- API prefix: `/api/v1`

## 공통 응답 형식

모든 생성 API는 아래 형태를 공통으로 사용합니다.

### 성공 응답 예시

```json
{
  "success": true,
  "task": "cosplay_basic",
  "image_path": "outputs/cosplay_basic_20260226_120001.png",
  "metadata_path": "outputs/cosplay_basic_20260226_120001.json",
  "prompt": "High-end raw photograph ...",
  "negative_prompt": "Oversized head, big head, ...",
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
  "vfx_options": ["animal_features", "halo_vfx", "color_palette"],
  "vfx_params": {
    "HAIR_COLOR": "blue",
    "EYE_COLOR": "gold"
  },
  "output_filename": null,
  "dry_run": false
}
```

### 필드 설명

- `illustration_path` (필수): 서버에서 접근 가능한 일러스트 이미지 경로
  - 권장 형식: 프로젝트 루트 기준 상대경로 (`inputs/references/...`)
- `prompt_variables` (선택): JSON 프롬프트 템플릿 치환값
- `vfx_options` (선택): VFX 선택 목록
  - 지원값: `animal_features`, `halo_vfx`, `color_palette`
- `vfx_params` (선택): VFX 옵션용 치환값
  - `color_palette` 선택 시 `HAIR_COLOR`, `EYE_COLOR` 필요
- `output_filename` (선택): 저장할 파일명 (예: `my_result.png`)
- `dry_run` (선택): `true`면 실제 모델 호출 없이 메타데이터만 저장

## 2. 일러스트 + 마스터 이미지 -> 코스프레 생성 (기능 2)

### Endpoint

- `POST /api/v1/generation/cosplay/with-master`

### Request JSON

```json
{
  "illustration_path": "inputs/references/ref_iroha.jpg",
  "master_image_path": "inputs/master_faces/master_iroha.jpg",
  "prompt_variables": {},
  "vfx_options": ["halo_vfx"],
  "vfx_params": {},
  "output_filename": null,
  "dry_run": false
}
```

### 권장 입력 품질 (마스터 이미지)

- 정면 얼굴
- 얼굴이 충분히 크게 보임
- 밝고 균일한 조명
- 눈/코/입 가림 최소화

경로 형식은 기능 1과 동일하게 프로젝트 루트 기준 상대경로를 사용합니다.

## 3. 인물 사진 -> 마스터 이미지 생성 (기능 3)

### Endpoint

- `POST /api/v1/generation/master-image`

### Request JSON

```json
{
  "person_image_path": "inputs/references/ref_iroha.jpg",
  "prompt_variables": {},
  "output_filename": null,
  "dry_run": false
}
```

### 목적

기능 2에서 얼굴 일관성을 높이기 위해 사용할 "기준 얼굴 이미지(마스터 이미지)"를 만드는 용도입니다.

경로 형식은 프로젝트 루트 기준 상대경로(`inputs/...`) 또는 절대경로를 사용합니다.

## 상태 확인 (Health Check)

### Endpoint

- `GET /api/v1/health`

### Response JSON

```json
{
  "status": "ok"
}
```

## 호출 흐름 (앱 연동 관점)

1. 앱에서 이미지 선택
2. 앱이 백엔드 API 호출
3. 백엔드가 프롬프트 JSON 조합
4. 백엔드가 Gemini 2.5 Flash Image 모델 호출
5. 백엔드가 결과 이미지/메타데이터 저장
6. 백엔드가 결과 경로/상태 반환

## 향후 확장 (실서비스)

1. `POST /api/v1/assets/upload` 추가 (멀티파트 업로드)
2. 서버가 업로드 파일 저장 후 `asset_id` 발급
3. 생성 API는 `*_path` 대신 `*_asset_id` 입력 받기
4. 작업 시간이 길어지면 비동기 Job API (`/jobs/{id}`) 추가
