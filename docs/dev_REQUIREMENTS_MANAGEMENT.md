# requirements.txt 관리 가이드 (MVP)

이 문서는 이 프로젝트에서 `requirements.txt`를 관리하는 방법을 설명합니다.

---

## 관리 원칙

- 현재 사용 중인 가상환경(`.venv`)에 설치된 패키지 목록을 그대로 `requirements.txt`에 저장합니다.
- 새로운 패키지를 설치했거나 버전을 변경했으면, 작업 후 `requirements.txt`를 다시 생성합니다.
- 문서/설정만 수정한 경우에는 `requirements.txt`를 갱신하지 않아도 됩니다.

---

## 설치 방법 (처음 실행하는 사용자)

가상환경 생성:

```powershell
python -m venv .venv
```

가상환경 활성화 (Windows PowerShell):

```powershell
.venv\Scripts\Activate.ps1
```

의존성 설치:

```powershell
python -m pip install -r requirements.txt
```

---

## requirements.txt 최신화 방법

가상환경이 활성화된 상태에서 아래 명령으로 덮어씁니다.

```powershell
python -m pip freeze > requirements.txt
```

이 명령은 현재 환경에 설치된 패키지와 버전을 모두 기록합니다.

---

## 언제 최신화해야 하나?

아래 경우에는 `requirements.txt`를 다시 생성하세요.

- 새로운 패키지를 설치한 경우
- 패키지 버전을 업그레이드/다운그레이드한 경우
- 가상환경을 새로 만들고 필요한 패키지를 다시 설치한 경우

---

## 권장 작업 순서

1. 가상환경 활성화
2. 필요한 패키지 설치/업데이트
3. 코드 실행 확인
4. `python -m pip freeze > requirements.txt` 실행
5. 변경된 `requirements.txt` 커밋

---

## 확인용 명령어

현재 어떤 Python / pip를 쓰는지 확인:

```powershell
where python
where pip
```

설치된 패키지 확인:

```powershell
python -m pip list
```

---

## 주의 사항

- 반드시 프로젝트 가상환경(`.venv`)을 활성화한 뒤 `freeze`를 실행하세요.
- 가상환경이 아닌 전역 Python에서 실행하면 불필요한 패키지가 `requirements.txt`에 섞일 수 있습니다.
- `requirements.txt`는 수동 편집보다 `freeze`로 다시 생성하는 방식을 우선으로 사용합니다.

---
