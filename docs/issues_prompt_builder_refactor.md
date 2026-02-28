# Prompt Builder 구조 개선 이슈

이 문서는 `prompt_builder.py`를 중심으로 프롬프트 병합 모듈 구조를 개선한 과정을 재현 가능하게 정리하기 위한 문서다.  
동일한 구조 문제(성능 저하, 규칙 누락, 유지보수 난이도)가 재발했을 때 같은 기준으로 점검하고 수정할 수 있도록 근거를 남긴다.

---

## 전체 요약

- `configs`를 프롬프트 빌더를 새 규칙으로 재구성하면서, 구조를 `타입 기반 정규화 -> 병합 -> 렌더링 -> 치환` 단계로 분리했다.
- 반복 호출 성능 개선을 위해 JSON 로드 캐시를 추가했고, 초기화 시 정적 파일 사전검증을 1회 수행하도록 변경했다.
- 플레이스홀더 치환을 1패스 정규식 스캔으로 교체하고, 예외 메시지를 코드 기반 포맷으로 표준화했다.
- 실행 검증 스크립트(`run_prompt_builder.py`)를 추가해 결과 프롬프트를 즉시 확인할 수 있게 했다.

---

## 문제 정의

- 기존 빌더 구조는 `dict[str, Any]` 중심이라 키/스키마 오류를 컴파일 단계에서 방지하기 어려웠다.
- 빌드 호출마다 동일 JSON 파일을 반복 로드하여 불필요한 I/O 비용이 발생했다.
- 플레이스홀더 치환이 변수 수만큼 전체 문자열을 반복 순회하는 방식이었다.
- 설정 오류가 런타임 후반에야 드러나 초기 장애 감지가 늦었다.
- 예외 메시지 형식이 일관되지 않아 원인 분류와 디버깅 속도가 떨어졌다.

---

## 원인 파악

- 프롬프트 데이터 모델이 명시적 타입 없이 동적 딕셔너리로 흩어져 있어, 함수 간 계약이 암묵적이었다.
- 파일 로드/검증/병합/렌더링 책임이 분리되어 있었지만 공통 상태(정규화 결과, 에러 코드, 파일 캐시) 레이어가 없었다.
- 플레이스홀더 키 집합이 구조적으로 관리되지 않아 치환 정책이 호출 인자에 의존했다.
- 문서/실행 검증 루틴이 분리되어 있지 않아 실제 출력 점검을 매번 수동으로 수행해야 했다.

---

## 해결 방안

- 정규화 타입 도입:
  - `ModeRule(TypedDict)`, `NormalizedPrompts(dataclass)`로 내부 계약을 명확히 정의.
- 로드 성능 개선:
  - `_load_json_cached()`로 파일별 캐시를 적용해 동일 파일 재로딩 제거.
- 초기 실패 감지:
  - `__init__`에서 `_validate_static_configs()`를 실행해 모드별 base/source/vfx 정합성을 1회 사전검증.
- 치환 성능/정책 개선:
  - `PLACEHOLDER_PATTERN` 기반 1패스 치환으로 전환.
  - 지원 플레이스홀더 키를 상수(`SUPPORTED_PLACEHOLDER_KEYS`)로 관리.
- 예외 표준화:
  - `_raise_value_error()`를 도입하고 `[TEMP_PROMPT_BUILDER:ERROR_CODE]` 포맷으로 통일.
- 재현 가능한 실행 경로 추가:
  - `temp_run_prompt_builder.py`를 생성해 모드/VFX/변수 조합 테스트를 CLI에서 반복 검증 가능하도록 구성.

---

## 결과

- 모듈 구조가 `정규화 타입 중심`으로 바뀌어 확장 시 영향 범위 추적이 쉬워졌다.
- 반복 빌드 시 JSON 재로딩이 제거되어 성능이 개선됐다.
- 시작 시점 사전검증으로 설정 불일치를 조기에 감지할 수 있게 됐다.
- 플레이스홀더 치환이 1패스로 단순화되어 긴 프롬프트에서 비용이 감소했다.
- 오류 메시지가 코드화되어 장애 분류가 빨라졌다.

검증에 사용한 대표 명령어:

```powershell
python temp_run_prompt_builder.py --mode mode1_general_trans.json --var REFERENCE_IMG=ref_iroha.jpg
python temp_run_prompt_builder.py --mode mode1_general_trans.json --var REFERENCE_IMG=ref_iroha.jpg --vfx-option color_palette --vfx-param HAIR_COLOR=silver --vfx-param EYE_COLOR=blue
python temp_run_prompt_builder.py --mode mode1_general_trans.json --var REFERENCE_IMG=ref_iroha.jpg --vfx-option color_palette
```

오류 케이스 검증 요약:

```text
오류: [TEMP_PROMPT_BUILDER:E_MISSING_COLOR_PALETTE_PARAMS] color_palette 사용 시 HAIR_COLOR, EYE_COLOR가 모두 필요합니다.
```

---

## 관련 파일

- `backend/services/temp_prompt_builder.py`
- `temp_run_prompt_builder.py`
- `temp_configs/common_base.json`
- `temp_configs/mode1_general_trans.json`
- `temp_configs/mode2_face_consistency.json`
- `temp_configs/mode3_master_image.json`
- `temp_configs/user_custom_prompts.json`
- `temp_configs/VFX_prompt.json`
- `docs/dev_DOCUMENTATION_GUIDE.md`

---
