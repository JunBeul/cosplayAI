# requirements.txt 관리 가이드 (MVP)

이 문서는 이 프로젝트에서 `requirements.txt`를 어떻게 관리할지 정리한 기준입니다.

목표는 단순합니다.

- 누구나 같은 의존성을 쉽게 설치할 수 있게 만들기
- 기능 추가 시 어떤 패키지를 넣어야 하는지 기준 만들기
- 버전 충돌을 줄이기

## 현재 파일 역할

- `requirements.txt`
  - 실행에 필요한 런타임 의존성 목록
  - FastAPI 서버 실행, CLI 실행, Gemini 이미지 호출에 필요한 패키지만 포함

## 설치 방법

가상환경 생성(권장):

```bash
python -m venv .venv
```

가상환경 활성화 (Windows PowerShell):

```powershell
.venv\Scripts\Activate.ps1
```

의존성 설치:

```bash
pip install -r requirements.txt
```

## 패키지 추가 규칙 (중요)

새 패키지를 추가할 때는 아래 순서로 진행합니다.

1. 먼저 실제 코드에서 필요 여부를 확인
2. `pip install <package>`로 로컬 테스트
3. 코드 반영 후 정상 동작 확인
4. `requirements.txt`에 직접 추가 (정렬 유지)
5. `README.md` 또는 관련 문서 업데이트

## 버전 관리 기준 (MVP)

현재는 MVP 단계이므로 "너무 빡빡한 pinning" 대신 범위 지정 방식을 사용합니다.

예시:

- `fastapi>=0.115,<1.0`
- `pydantic>=2.7,<3.0`

이유:

- 패치/마이너 업데이트는 비교적 유연하게 허용
- 메이저 버전 변경으로 인한 큰 깨짐은 방지

## 업데이트할 때 주의할 점

### 1) FastAPI / Pydantic

- FastAPI는 Pydantic 버전에 영향을 받습니다.
- 두 패키지를 같이 확인하는 습관이 좋습니다.

### 2) google-genai

- API 메서드/파라미터가 바뀔 수 있으므로 버전 업데이트 후 실제 생성 테스트 필요
- 특히 `generate_content()` 호출부(`backend/services/gemini_image_service.py`) 확인
- 현재 프로젝트는 API 키 기반 호출을 사용합니다.

### 3) uvicorn

- 개발 서버 실행용이므로 운영 배포 방식과 다를 수 있음
- MVP 단계에서는 `requirements.txt`에 포함 유지

## 권장 작업 흐름 (예시)

기존 환경 업데이트:

```bash
pip install -r requirements.txt --upgrade
```

새 패키지 추가 후 반영:

```bash
pip install some-package
```

그리고 `requirements.txt`에 직접 추가:

```txt
some-package>=1.0,<2.0
```

## 무엇을 `requirements.txt`에 넣지 않을까?

- 표준 라이브러리 (`json`, `os`, `pathlib` 등)
- 아직 쓰지 않는 패키지
- IDE 전용 도구

## 향후 확장 (선택)

프로젝트가 커지면 아래처럼 분리할 수 있습니다.

1. `requirements.txt` (런타임)
2. `requirements-dev.txt` (테스트/린트/포맷터)
3. `requirements-lock.txt` 또는 다른 lock 방식 (배포 재현성 강화)
