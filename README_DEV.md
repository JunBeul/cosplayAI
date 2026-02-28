# 개발/운영/재현 가이드 (README_DEV)

프로젝트를 로컬에서 실행하고, 재현하고, 점검하기 위한 문서입니다. 프로젝트 배경/성과 중심 설명은 루트 README를 참고하고, 이 문서는 실행/환경/API/배포 재현에 집중합니다.

- 서비스 URL: 추가 예정
- 서비스 안내: [README.md](README.md)

---

## INDEX

1. 실행 환경 준비
2. 환경변수 설정
3. CLI 실행 방법
4. API 서버 실행 방법
5. API SPEC
6. 프로젝트 구조

---

## 1. 실행 환경 준비

### 요구 사항

- Python 3.10+ 권장
- `GEMINI_API_KEY` (Gemini API Key)
- 로컬 테스트용 입력 이미지 (`inputs/`)

### 가상환경 생성/활성화 (Windows PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 패키지 설치

```powershell
python -m pip install -r requirements.txt
```

---

## 2. 환경변수 설정

프로젝트 루트에 `.env` 파일을 만들고 아래 값을 설정합니다.

```env
GEMINI_API_KEY=YOUR_API_KEY
```

참고:

- `.env.example`는 템플릿용 파일입니다.
- 입력 이미지 경로는 `.env`가 아니라 CLI 인자 또는 API 요청 JSON으로 전달합니다.

---

## 3. CLI 실행 방법

### 기능 1: 일러스트 -> 코스프레 이미지

```powershell
python -m backend.cli cosplay-basic --illustration-path inputs/references/ref_iroha.jpg
```

### 기능 2: 일러스트 + 마스터 이미지 -> 코스프레 이미지

```powershell
python -m backend.cli cosplay-with-master --illustration-path inputs/references/ref_iroha.jpg --master-image-path inputs/master_faces/master_iroha.jpg
```

### 기능 3: 인물 사진 -> 마스터 이미지

```powershell
python -m backend.cli master-image --person-image-path upload/your/image.png
```

### 기능 4: 프롬프트 확인용 `dry-run` 사용

실제 이미지 생성 API 호출 없이 프롬프트/메타데이터만 저장하려면 `--dry-run`을 사용합니다.

```powershell
python -m backend.cli cosplay-basic --illustration-path inputs/references/ref_iroha.jpg --dry-run
```

생성 결과:

- `outputs/dry_run_*.json`

이 파일에서 최종 프롬프트 텍스트와 메타데이터를 확인할 수 있습니다.

### 기능 5: VFX / 사용자 커스텀 옵션 (CLI)

> 주의
>
> - `--hair-color`와 `--eye-color`는 함께 입력해야 합니다.
> - 하나만 입력하면 CLI에서 에러를 반환합니다.

기능 1, 2에서 선택적으로 사용할 수 있습니다.

- `--user-custom-text`
- `--animal-features`
- `--halo-vfx`
- `--hair-color`
- `--eye-color`

예시:

```powershell
python -m backend.cli cosplay-basic --illustration-path inputs/references/ref_iroha.jpg --animal-features --halo-vfx --hair-color blue --eye-color gold --user-custom-text "Use soft rim light and slightly wider framing."
```

---

## 4. API 서버 실행 방법

```powershell
uvicorn backend.api.main:app --reload
```

기본 주소:

- `http://localhost:8000`

헬스체크:

- `GET /api/v1/health`

API 상세 스펙은 `docs/API_SPEC.md`를 참고하세요.

---

## 5. API SPEC

- 상세 API 문서: [`docs/dev_API_SPEC.md`](docs/dev_API_SPEC.md)

---

## 6. 프로젝트 구조

- 상세 구조 문서: [`docs/dev_PROJECT_STRUCTURE.md`](docs/dev_PROJECT_STRUCTURE.md)

---
