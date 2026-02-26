# CosplayAI

애니메이션 일러스트를 입력하면 코스프레 실사 이미지를 생성하는 서비스를 목표로 하는 프로젝트입니다.

## 1. 프로젝트 개요

CosplayAI는 다음 문제를 해결하기 위한 프로젝트입니다.

- 사용자가 업로드한 애니메이션 일러스트를 기반으로 실사 코스프레 이미지 생성
- 얼굴 일관성을 유지하기 위한 마스터 이미지 기반 생성
- 사용자 인물 사진으로 마스터 이미지 생성

## 2. 핵심 기능

1. 일러스트 -> 코스프레 실사 이미지 생성
2. 일러스트 + 마스터 이미지 -> 얼굴 일관성 강화 코스프레 이미지 생성
3. 인물 사진 -> 마스터 이미지 생성

추가로 제공되는 개발 편의 기능:

- CLI 실행 (`backend/cli.py`)
- FastAPI 기반 API 서버 (`backend/api`)
- 프롬프트 템플릿 JSON 분리 (`configs/`)
- 생성 메타데이터(JSON) 저장 (`outputs/`)

## 3. 프로젝트 진행도

### 현재 상태 (MVP 백엔드 기준)

- [x] 프롬프트 템플릿(JSON) 구조 분리
- [x] 기능 1/2/3 파이프라인 분리
- [x] FastAPI API 엔드포인트 구성
- [x] CLI 테스트 실행기 구성
- [x] 결과 이미지 + 메타데이터 저장 구조
- [ ] 입력 품질 검사 고도화
- [ ] 안드로이드 앱 업로드/결과 UI 연동
- [ ] 업로드 API(`multipart`) 및 비동기 Job 처리

## 4. 기술 스택

### Backend / API

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Uvicorn](https://img.shields.io/badge/Uvicorn-2C3E50?style=for-the-badge&logo=uvicorn&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-E92063?style=for-the-badge&logo=pydantic&logoColor=white)

### AI / Config / Runtime

![Google GenAI](https://img.shields.io/badge/Google%20GenAI-4285F4?style=for-the-badge&logo=google&logoColor=white)
![Imagen](https://img.shields.io/badge/Imagen-34A853?style=for-the-badge&logo=googlephotos&logoColor=white)
![python-dotenv](https://img.shields.io/badge/python--dotenv-222222?style=for-the-badge&logo=dotenv&logoColor=white)
![JSON](https://img.shields.io/badge/JSON-000000?style=for-the-badge&logo=json&logoColor=white)

## 5. 프로젝트 구조

```text
CosplayAI/
├─ backend/
│  ├─ api/                 # FastAPI 엔드포인트
│  ├─ core/                # 환경변수/경로 등 공통 설정
│  ├─ domain/              # 공용 요청/응답 모델, enum
│  ├─ services/            # 프롬프트/검증/저장/Imagen 호출
│  ├─ cli.py               # 로컬 테스트용 실행기
│  └─ __init__.py
├─ configs/                # 프롬프트 템플릿 JSON
├─ docs/                   # 문서 (API 명세, 구조, requirements 관리)
├─ inputs/                 # 테스트 입력 이미지
│  ├─ references/
│  └─ master_faces/
├─ outputs/                # 생성 결과 이미지 / 메타데이터
├─ requirements.txt        # 런타임 의존성
└─ README.md
```

자세한 구조 설명:

- `docs/PROJECT_STRUCTURE.md`
- `docs/API_SPEC.md`
- `docs/REQUIREMENTS_MANAGEMENT.md`

## 6. 요구 사항

- Python 3.10+ 권장
- Google GenAI(Imagen) API 사용 가능한 키 (`GEMINI_API_KEY`)
- 로컬 테스트용 이미지 파일 (`inputs/` 폴더)

필수 Python 모듈은 `requirements.txt`에 정리되어 있습니다.

## 7. 프로젝트 실행

### 2) 가상환경 생성 및 활성화 (권장)

가상환경 생성:

```bash
python -m venv .venv
```

### 3) 의존성 설치

```bash
pip install -r requirements.txt
```

의존성 관리 기준은 `docs/REQUIREMENTS_MANAGEMENT.md` 참고

### 4) 환경 변수 설정

`.env.example`를 참고해서 `.env` 파일을 생성하고 API 키를 입력합니다.

예시:

```env
GEMINI_API_KEY=YOUR_API_KEY
```

참고:

- 이미지 경로는 `.env`가 아니라 CLI 인자 또는 API 요청 JSON에서 전달합니다.
- 상대경로는 프로젝트 루트 기준으로 해석됩니다. 예: `inputs/references/ref_iroha.jpg`

### 5) CLI로 빠르게 테스트 (권장)

기능 1: 일러스트 -> 코스프레

```bash
python -m backend.cli cosplay-basic --illustration-path inputs/references/ref_iroha.jpg
```

기능 2: 일러스트 + 마스터 이미지 -> 코스프레

```bash
python -m backend.cli cosplay-with-master --illustration-path inputs/references/ref_iroha.jpg --master-image-path inputs/master_faces/master_iroha.jpg
```

기능 3: 인물 사진 -> 마스터 이미지

```bash
python -m backend.cli master-image --person-image-path inputs/references/ref_iroha.jpg
```

디버깅용으로 실제 API 호출 없이 흐름만 확인하려면:

```bash
python -m backend.cli cosplay-basic --illustration-path inputs/references/ref_iroha.jpg --dry-run
```

### 6) API 서버 실행 (안드로이드 연동용)

```bash
uvicorn backend.api.main:app --reload
```

- 기본 주소: `http://localhost:8000`
- API 명세: `docs/API_SPEC.md`
- Health check: `GET /api/v1/health`
