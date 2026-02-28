# 개발/운영/재현 가이드 (README_DEV)

이 문서는 로컬 개발자가 현재 백엔드(2026-02-28 기준)를 실행, 검증, 재현하는 절차를 정리합니다.

서비스 개요/소개는 [README.md](README.md)를 참고하세요.

---

## 1. 요구사항

- Python 3.10+
- `GEMINI_API_KEY`
- 테스트용 입력 이미지 파일 (`inputs/`)

---

## 2. 로컬 환경 설정

### 2.1 가상환경 생성/활성화 (Windows PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2.2 의존성 설치

```powershell
python -m pip install -r requirements.txt
```

### 2.3 환경변수

프로젝트 루트에 `.env` 파일 생성:

```env
GEMINI_API_KEY=YOUR_API_KEY
```

- 템플릿 파일: `.env.example`
- 입력 이미지 경로는 환경변수가 아니라 CLI 인자/API JSON으로 전달

---

## 3. CLI 실행

### 3.1 기능 1: 일러스트 -> 코스프레

```powershell
python -m backend.cli cosplay-basic --illustration-path inputs/references/ref_iroha.jpg
```

생성 파일:

- `outputs/cosplay_basic_*_*.json`
- `outputs/cosplay_basic_*_*.png`

### 3.2 기능 2: 일러스트 + 마스터 -> 코스프레

```powershell
python -m backend.cli cosplay-with-master --illustration-path inputs/references/ref_iroha.jpg --master-image-path inputs/master_faces/master_iroha.jpg
```

생성 파일:

- `outputs/cosplay_with_master_*_*.json`
- `outputs/cosplay_with_master_*_*.png`

### 3.3 기능 3: 인물 사진 -> 마스터 이미지

```powershell
python -m backend.cli master-image --person-image-path inputs/your/img.jpg
```

생성 파일:

- `outputs/master_image_*_*.json`
- `outputs/master_image_*_*.png`

### 3.4 dry-run (모델 호출 없이 프롬프트/메타데이터만 저장)

```powershell
python -m backend.cli cosplay-basic --illustration-path inputs/references/ref_iroha.jpg --dry-run
```

생성 파일:

- `outputs/dry_run_*.json`

### 3.5 선택 옵션

> 주의:
>
> - `--hair-color`와 `--eye-color`는 반드시 함께 입력

| 선택 옵션          | 사용 가능 모드      | 예시                                                                      |
| ------------------ | ------------------- | ------------------------------------------------------------------------- |
| 커스텀 프롬프트    | mode1, mode2, mode3 | `... --user-custom-text "Use soft rim light and slightly wider framing."` |
| 동물 귀, 꼬리 추가 | mode1, mode2        | `... --animal-features`                                                   |
| 헤일로 추가        | mode1, mode2        | `... --halo-vfx`                                                          |
| 눈, 머리 색 추가   | mode1, mode2        | `... --hair-color blue --eye-color gold`                                  |

---

## 4. API 서버 실행

```powershell
uvicorn backend.api.main:app --reload
```

기본 주소:

- `http://localhost:8000`

헬스체크:

- `GET /api/v1/health`

생성 엔드포인트:

- `POST /api/v1/generation/cosplay/basic`
- `POST /api/v1/generation/cosplay/with-master`
- `POST /api/v1/generation/master-image`

---

## 5. 경로/출력 규칙

- 상대 경로 입력은 프로젝트 루트 기준으로 해석
- 허용 이미지 확장자: `.png`, `.jpg`, `.jpeg`, `.webp`
- 결과 이미지: `outputs/<task>_<UTC timestamp>.png`
- 메타데이터: 이미지와 같은 이름의 `.json`

---

## 6. 참고 문서

- API 스펙: [`docs/dev_API_SPEC.md`](docs/dev_API_SPEC.md)

---

## 7. 프로젝트 구조

- 상세 구조 문서: [`docs/dev_PROJECT_STRUCTURE.md`](docs/dev_PROJECT_STRUCTURE.md)

---
