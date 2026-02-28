# GitHub Flow 브랜치 운영 가이드

이 문서는 소규모 팀/개인 개발 환경에서 GitHub Flow 방식으로 브랜치를 운영하는 기준을 정의한다. 이 문서의 규칙은 커밋 메시지 작성 규칙과 별개로 관리한다.

---

## 1. GitHub Flow 기준

- 기본 브랜치는 단일 브랜치(`main`)로 운영한다.
- 배포는 기본 브랜치에서 수행한다.
- 모든 작업은 기본 브랜치에서 분기한 짧은 `feature` 브랜치에서 진행한다.
- 작업 완료 후 PR로 기본 브랜치에 머지하고 브랜치를 삭제한다.

---

## 2. 브랜치 네이밍 규칙

형식:

```text
feature/<short-description>
```

- `short-description`은 소문자 + 하이픈(`-`) 사용
- 3~6 단어 이내 권장
- 버그 수정/리팩터링/문서 작업도 동일하게 `feature/` 접두어 사용

예시:

```text
feature/add-mode3-master-image
feature/fix-prompt-empty-response
feature/refactor-pipeline-split
feature/update-api-docs
```

금지/비권장:

- 의미 없는 이름: `feature/test`, `feature/temp`
- 대문자/공백/언더스코어 혼용: `Feature/New_Feature`
- 여러 목적 혼합: `feature/feat-fix-refactor-all`

---

## 3. 커밋 메시지 규칙과 분리 원칙

- 브랜치명은 작업 단위를 식별하기 위한 이름이다.
- 커밋 메시지 형식은 브랜치명과 1:1로 맞출 필요가 없다.
- 즉, 브랜치는 `feature/...`로 고정하고, 커밋 메시지는 별도 규칙에 따라 작성한다.

---

## 4. 표준 작업 절차

1. 기본 브랜치 최신화
2. `feature` 브랜치 생성
3. 작업/커밋 후 원격 푸시
4. 기본 브랜치 대상으로 PR 생성
5. 리뷰/체크 통과 후 머지
6. 머지 후 브랜치 삭제

예시 (`main` 기준):

```bash
git switch main
git pull origin main

git switch -c feature/your-brunch-name
# 작업 + 커밋

git push -u origin feature/your-brunch-name
# GitHub에서 PR 생성 (base: main)

git switch main
git pull origin main
git branch -d feature/your-brunch-name
git push origin --delete feature/your-brunch-name
```

---

## 5. 운영 규칙

- 기본 브랜치 직접 푸시는 금지한다.
- PR은 한 가지 목적만 포함하도록 작게 유지한다.
- CI/테스트 실패 상태에서는 머지하지 않는다.
- 브랜치 수명은 가능하면 1~3일 이내로 유지한다.
- 머지 완료된 브랜치는 로컬/원격에서 즉시 정리한다.

---

## 6. 요약

- GitHub Flow는 기본 브랜치 + 짧은 `feature` 브랜치로 운영한다.
- `release/hotfix/develop` 브랜치 없이 PR 기반으로 머지한다.
- 브랜치명은 `feature/<short-description>`로 통일한다.
- 브랜치 규칙과 커밋 메시지 규칙은 별개로 관리한다.

---
