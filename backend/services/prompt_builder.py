"""
파일명: prompt_builder.py
작성자: Codex
설명: JSON 설정을 규칙대로 병합하고 스키마/키 검증을 통해 최종 프롬프트 문자열을 생성한다.
상위 모듈: backend.services.pipelines
하위 모듈: backend.core.settings, backend.domain.models, backend.services.config_loader
"""


from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any, NoReturn, TypedDict
from backend.core.settings import Settings
from backend.domain.models import PromptBundle
from .config_loader import load_json_file


COMMAND_KEY = "Command"
CRUCIAL_KEY = "Crucial Constraints"
STRICTLY_AVOID_KEY = "Strictly Avoid"
ADDITIONS_KEY = "Additions"
VFX_OPTION_TO_CONSTRAINT_KEY = {
    "animal_features": "Animal Features",
    "halo_vfx": "Halo VFX",
    "color_palette": "Styling",
}
SUPPORTED_PLACEHOLDER_KEYS = {
    "REFERENCE_IMG",
    "MASTER_IMG",
    "HAIR_COLOR",
    "EYE_COLOR",
    "PERSON_IMG",
    "CHARACTER_NAME",
}
PLACEHOLDER_PATTERN = re.compile(r"\[([A-Z0-9_]+)\]")
ERROR_NAMESPACE = "PROMPT_BUILDER"


class ModeRule(TypedDict):
    """
    모드별 프롬프트 구성 규칙 타입.
    """

    base: str
    sources: list[str]
    use_vfx: bool


@dataclass
class NormalizedPrompts:
    """
    병합/렌더링에 사용하는 정규화 프롬프트 타입.
    """

    command: list[str] = field(default_factory=list)
    crucial_constraints: dict[str, list[str]] = field(default_factory=dict)
    strictly_avoid: list[str] = field(default_factory=list)


MODE_RULES: dict[str, ModeRule] = {
    "mode1_general_trans.json": {
        "base": "common_base.json",
        "sources": ["mode1_general_trans.json", "user_custom_prompts.json"],
        "use_vfx": True,
    },
    "mode2_face_consistency.json": {
        "base": "common_base.json",
        "sources": ["mode2_face_consistency.json", "user_custom_prompts.json"],
        "use_vfx": True,
    },
    "mode3_master_image.json": {
        "base": "mode3_master_image.json",
        "sources": ["user_custom_prompts.json"],
        "use_vfx": False,
    },
}


class PromptBuilder:
    """configs 기반 신규 프롬프트 병합 규칙을 검증하기 위한 빌더."""

    def __init__(self, settings: Settings, config_dir: Path | None = None) -> None:
        """
        설정 디렉터리를 기준으로 빌더를 초기화한다.
        Args:
            settings: 프로젝트 경로 정보를 담은 Settings 객체.
            config_dir: 설정 루트 경로(선택). None이면 <project_root>/configs를 사용한다.
        """
        self.settings = settings
        self.config_dir = config_dir or (settings.project_root / "configs")
        self._json_cache: dict[Path, dict[str, Any]] = {}
        self._validate_static_configs()

    def _raise_value_error(self, code: str, detail: str) -> NoReturn:
        """
        프로젝트 표준 형식의 ValueError를 발생시킨다.
        Args:
            code: 예외 코드 식별자.
            detail: 예외 상세 메시지.
        Raises:
            ValueError: 표준화된 메시지 포맷으로 발생한다.
        """
        raise ValueError(f"[{ERROR_NAMESPACE}:{code}] {detail}")

    def build(
        self,
        mode_config_name: str,
        variables: dict[str, str] | None = None,
        vfx_options: list[str] | None = None,
        vfx_params: dict[str, str] | None = None,
        user_custom_text: str | None = None,
    ) -> PromptBundle:
        """
        모드별 병합/매핑 규칙을 적용해 최종 프롬프트를 생성한다.
        Args:
            mode_config_name: MODE_RULES에 등록된 모드 파일명 키.
            variables: 플레이스홀더 치환 변수. 예: REFERENCE_IMG.
            vfx_options: 활성화할 VFX 옵션 목록. 허용값: animal_features, halo_vfx, color_palette.
            vfx_params: VFX 전용 추가 치환 변수.
            user_custom_text: user_custom_prompts의 Additions를 덮어쓸 사용자 입력 문자열.
        Returns:
            PromptBundle: 치환까지 완료된 최종 프롬프트 텍스트와 모드 파일명.
        Raises:
            ValueError: 모드/스키마/키 검증 실패 또는 잘못된 VFX 옵션일 때 발생한다.
            FileNotFoundError: 필요한 설정 파일이 없을 때 발생한다.
        """
        variables = dict(variables or {})
        vfx_options = list(vfx_options or [])

        if vfx_params:
            variables.update(vfx_params)

        merged_prompts = self._merge_prompts_for_mode(
            mode_config_name=mode_config_name,
            vfx_options=vfx_options,
            variables=variables,
            user_custom_text=user_custom_text,
        )

        prompt_text = self._to_prompt_text(merged_prompts)
        prompt_text = self._map_prompt_values(prompt_text, variables)
        return PromptBundle(text=prompt_text, mode_config_name=mode_config_name)

    def _merge_prompts_for_mode(
        self,
        mode_config_name: str,
        vfx_options: list[str],
        variables: dict[str, str],
        user_custom_text: str | None,
    ) -> NormalizedPrompts:
        """
        모드 규칙에 따라 base/mode/user/VFX 프롬프트를 병합한다.
        Args:
            mode_config_name: MODE_RULES에 등록된 모드 파일명 키.
            vfx_options: 활성화할 VFX 옵션 목록.
            variables: VFX 필수값 검증 및 후속 플레이스홀더 매핑에 사용하는 변수 맵.
            user_custom_text: Additions 덮어쓰기에 사용할 사용자 입력 문자열.
        Returns:
            NormalizedPrompts: 정규화된 병합 프롬프트 블록.
        Raises:
            ValueError: 지원하지 않는 모드이거나 스키마/키 검증이 실패하면 발생한다.
            FileNotFoundError: 필요한 설정 파일이 없으면 발생한다.
        """
        mode_rule = MODE_RULES.get(mode_config_name)
        if mode_rule is None:
            allowed = ", ".join(sorted(MODE_RULES))
            self._raise_value_error(
                code="E_UNSUPPORTED_MODE",
                detail=f"지원하지 않는 mode_config_name='{mode_config_name}'. 허용값: {allowed}",
            )

        base_file_name = str(mode_rule["base"])
        base_doc = self._load_json_cached(base_file_name)
        merged = self._normalize_prompt_structure(
            doc=base_doc,
            file_name=base_file_name,
            require_command=True,
            require_constraints=True,
        )

        for source_file_name in mode_rule["sources"]:
            source_doc = self._load_json_cached(source_file_name)
            source_prompts = self._normalize_prompt_structure(
                doc=source_doc,
                file_name=source_file_name,
                require_command=False,
                require_constraints=True,
            )

            if source_file_name == "user_custom_prompts.json":
                self._apply_user_custom_text(source_prompts, user_custom_text)

            self._merge_prompt_block(
                base_prompts=merged,
                source_prompts=source_prompts,
                base_file_name=base_file_name,
                source_file_name=source_file_name,
            )

        if bool(mode_rule["use_vfx"]):
            vfx_doc = self._load_json_cached("VFX_prompt.json")
            vfx_prompts = self._normalize_prompt_structure(
                doc=vfx_doc,
                file_name="VFX_prompt.json",
                require_command=False,
                require_constraints=True,
            )
            selected_vfx = self._build_vfx_overlay(vfx_prompts, vfx_options, variables)
            self._merge_prompt_block(
                base_prompts=merged,
                source_prompts=selected_vfx,
                base_file_name=base_file_name,
                source_file_name="VFX_prompt.json",
            )

        return merged

    def _load_json_cached(self, file_name: str) -> dict[str, Any]:
        """
        설정 JSON 파일을 캐시 기반으로 로드한다.
        Args:
            file_name: 설정 파일명.
        Returns:
            dict[str, Any]: 로드된 JSON 문서 객체.
        Raises:
            FileNotFoundError: 설정 파일이 존재하지 않을 때 발생한다.
            ValueError: JSON 문법이 올바르지 않을 때 발생한다.
        """
        full_path = (self.config_dir / file_name).resolve()
        cached = self._json_cache.get(full_path)
        if cached is not None:
            return cached

        loaded = load_json_file(full_path)
        self._json_cache[full_path] = loaded
        return loaded

    def _validate_static_configs(self) -> None:
        """
        초기화 시 모드별 정적 설정 파일을 1회 사전검증한다.
        Args:
            없음.
        Raises:
            ValueError: 스키마 불일치, 키 호환 불일치가 있으면 발생한다.
            FileNotFoundError: 필수 설정 파일이 없으면 발생한다.
        """
        for _mode_name, mode_rule in MODE_RULES.items():
            base_file_name = mode_rule["base"]
            base_doc = self._load_json_cached(base_file_name)
            base_prompts = self._normalize_prompt_structure(
                doc=base_doc,
                file_name=base_file_name,
                require_command=True,
                require_constraints=True,
            )

            merged_probe = self._clone_normalized_prompts(base_prompts)
            for source_file_name in mode_rule["sources"]:
                source_doc = self._load_json_cached(source_file_name)
                source_prompts = self._normalize_prompt_structure(
                    doc=source_doc,
                    file_name=source_file_name,
                    require_command=False,
                    require_constraints=True,
                )
                self._merge_prompt_block(
                    base_prompts=merged_probe,
                    source_prompts=source_prompts,
                    base_file_name=base_file_name,
                    source_file_name=source_file_name,
                )

            if not mode_rule["use_vfx"]:
                continue

            vfx_doc = self._load_json_cached("VFX_prompt.json")
            vfx_prompts = self._normalize_prompt_structure(
                doc=vfx_doc,
                file_name="VFX_prompt.json",
                require_command=False,
                require_constraints=True,
            )
            for option in VFX_OPTION_TO_CONSTRAINT_KEY:
                probe_variables = {"HAIR_COLOR": "tmp", "EYE_COLOR": "tmp"} if option == "color_palette" else {}
                selected_vfx = self._build_vfx_overlay(
                    vfx_prompts=vfx_prompts,
                    vfx_options=[option],
                    variables=probe_variables,
                )
                self._merge_prompt_block(
                    base_prompts=self._clone_normalized_prompts(base_prompts),
                    source_prompts=selected_vfx,
                    base_file_name=base_file_name,
                    source_file_name="VFX_prompt.json",
                )

    def _clone_normalized_prompts(self, source: NormalizedPrompts) -> NormalizedPrompts:
        """
        정규화 프롬프트를 병합 검증용으로 깊은 복제한다.
        Args:
            source: 복제할 정규화 프롬프트.
        Returns:
            NormalizedPrompts: 내부 리스트/딕셔너리가 분리된 복제 객체.
        """
        return NormalizedPrompts(
            command=[*source.command],
            crucial_constraints={key: [*values] for key, values in source.crucial_constraints.items()},
            strictly_avoid=[*source.strictly_avoid],
        )

    def _normalize_prompt_structure(
        self,
        doc: dict[str, Any],
        file_name: str,
        require_command: bool,
        require_constraints: bool,
    ) -> NormalizedPrompts:
        """
        단일 프롬프트 문서를 검증하고 병합용 표준 형태로 정규화한다.
        Args:
            doc: 로드된 JSON 문서 객체.
            file_name: 에러 메시지에 포함할 소스 파일명.
            require_command: Command 키 필수 여부.
            require_constraints: Crucial Constraints 키 필수 여부.
        Returns:
            NormalizedPrompts: 리스트 기반 값으로 통일된 표준 프롬프트 구조.
        Raises:
            ValueError: prompts 블록 또는 허용 키 규칙이 올바르지 않을 때 발생한다.
        """
        prompts = doc.get("prompts")
        if not isinstance(prompts, dict):
            self._raise_value_error(
                code="E_INVALID_PROMPTS_SECTION",
                detail=f"{file_name}: 'prompts'는 object(dict)여야 합니다.",
            )

        allowed_keys = {COMMAND_KEY, CRUCIAL_KEY, STRICTLY_AVOID_KEY}
        for key in prompts:
            if key not in allowed_keys:
                self._raise_value_error(
                    code="E_UNSUPPORTED_PROMPTS_KEY",
                    detail=f"{file_name}: 지원하지 않는 prompts 키 '{key}'. 허용 키: {sorted(allowed_keys)}",
                )

        if require_command and COMMAND_KEY not in prompts:
            self._raise_value_error(
                code="E_MISSING_COMMAND",
                detail=f"{file_name}: 필수 키 '{COMMAND_KEY}'가 없습니다.",
            )
        if require_constraints and CRUCIAL_KEY not in prompts:
            self._raise_value_error(
                code="E_MISSING_CONSTRAINTS",
                detail=f"{file_name}: 필수 키 '{CRUCIAL_KEY}'가 없습니다.",
            )

        strictly_avoid_raw = self._extract_strictly_avoid_raw(prompts=prompts)
        return NormalizedPrompts(
            command=self._to_clean_list(prompts.get(COMMAND_KEY, "")),
            crucial_constraints=self._normalize_constraints(
                constraints_value=prompts.get(CRUCIAL_KEY, {}),
                file_name=file_name,
            ),
            strictly_avoid=self._to_clean_list(strictly_avoid_raw),
        )

    def _extract_strictly_avoid_raw(self, prompts: dict[str, Any]) -> Any:
        """
        Strictly Avoid 원본 값을 위치 규칙에 따라 추출한다.
        Args:
            prompts: 문서 내부의 prompts 블록.
        Returns:
            Any: Strictly Avoid 원본 값.
        """
        return prompts.get(STRICTLY_AVOID_KEY, "")

    def _normalize_constraints(self, constraints_value: Any, file_name: str) -> dict[str, list[str]]:
        """
        Crucial Constraints 값을 리스트 형태로 정규화한다.
        Args:
            constraints_value: 원본 constraints 값. 기대 형태는 dict[str, str|list[str]].
            file_name: 에러 메시지에 포함할 소스 파일명.
        Returns:
            dict[str, list[str]]: 각 키가 정리된 문자열 리스트를 갖는 constraints 딕셔너리.
        Raises:
            ValueError: constraints 값이 객체(dict)가 아닐 때 발생한다.
        """
        if constraints_value is None:
            return {}
        if not isinstance(constraints_value, dict):
            self._raise_value_error(
                code="E_INVALID_CONSTRAINTS_SECTION",
                detail=f"{file_name}: '{CRUCIAL_KEY}'는 object(dict)여야 합니다.",
            )

        normalized: dict[str, list[str]] = {}
        for key, value in constraints_value.items():
            normalized[str(key)] = self._to_clean_list(value)
        return normalized

    def _merge_prompt_block(
        self,
        base_prompts: NormalizedPrompts,
        source_prompts: NormalizedPrompts,
        base_file_name: str,
        source_file_name: str,
    ) -> None:
        """
        소스 프롬프트 블록 하나를 base 프롬프트 블록에 병합한다.
        Args:
            base_prompts: 병합 대상(가변) 프롬프트 블록.
            source_prompts: 병합 소스 프롬프트 블록.
            base_file_name: 키 범위 검증 에러에 사용할 base 파일명.
            source_file_name: 키 범위 검증 에러에 사용할 source 파일명.
        Raises:
            ValueError: source에 base 스키마에 없는 키가 포함되면 발생한다.
        """
        if source_prompts.command:
            base_prompts.command.extend(source_prompts.command)

        if source_prompts.strictly_avoid:
            base_prompts.strictly_avoid.extend(source_prompts.strictly_avoid)

        base_constraints = base_prompts.crucial_constraints
        for constraint_key, incoming_values in source_prompts.crucial_constraints.items():
            if not incoming_values:
                continue
            if constraint_key not in base_constraints:
                self._raise_value_error(
                    code="E_UNKNOWN_CONSTRAINT_KEY",
                    detail=(
                        f"{source_file_name}: constraint key '{constraint_key}'는 "
                        f"base 파일 {base_file_name}에 존재하지 않습니다."
                    ),
                )
            base_constraints[constraint_key].extend(incoming_values)

    def _apply_user_custom_text(self, user_prompts: NormalizedPrompts, user_custom_text: str | None) -> None:
        """
        런타임 사용자 입력으로 user_custom_prompts의 Additions를 덮어쓴다.
        Args:
            user_prompts: 표준 형태의 사용자 프롬프트 블록.
            user_custom_text: 런타임 사용자 입력 문자열. None/빈 문자열은 무시한다.
        Raises:
            ValueError: user 프롬프트에 Crucial Constraints 블록이 없을 때 발생한다.
        """
        if user_custom_text is None:
            return

        custom_text = user_custom_text.strip()
        if not custom_text:
            return

        user_prompts.crucial_constraints[ADDITIONS_KEY] = [custom_text]

    def _build_vfx_overlay(
        self,
        vfx_prompts: NormalizedPrompts,
        vfx_options: list[str],
        variables: dict[str, str],
    ) -> NormalizedPrompts:
        """
        선택된 옵션만 반영한 VFX 전용 프롬프트 블록을 생성한다.
        Args:
            vfx_prompts: 표준 형태의 VFX 프롬프트 블록.
            vfx_options: 요청에서 전달된 VFX 옵션 키 목록.
            variables: VFX 필수 파라미터 검증에 사용할 플레이스홀더 변수 맵.
        Returns:
            NormalizedPrompts: 선택된 VFX constraints만 포함한 표준 프롬프트 블록.
        Raises:
            ValueError: 지원하지 않는 VFX 옵션이거나 필수 파라미터가 누락되면 발생한다.
        """
        unique_options = list(dict.fromkeys(vfx_options))
        if not unique_options:
            return NormalizedPrompts()

        selected_constraints: dict[str, list[str]] = {}
        for option in unique_options:
            constraint_key = VFX_OPTION_TO_CONSTRAINT_KEY.get(option)
            if constraint_key is None:
                allowed = ", ".join(sorted(VFX_OPTION_TO_CONSTRAINT_KEY))
                self._raise_value_error(
                    code="E_UNSUPPORTED_VFX_OPTION",
                    detail=f"지원하지 않는 vfx option='{option}'. 허용값: {allowed}",
                )

            if option == "color_palette":
                self._validate_color_palette_inputs(variables)

            incoming_values = self._to_clean_list(vfx_prompts.crucial_constraints.get(constraint_key, []))
            if incoming_values:
                selected_constraints[constraint_key] = incoming_values

        return NormalizedPrompts(crucial_constraints=selected_constraints)

    def _to_prompt_text(self, merged_prompts: NormalizedPrompts) -> str:
        """
        표준 병합 프롬프트를 최종 문자열 포맷으로 렌더링한다.
        Args:
            merged_prompts: 병합 완료된 정규화 프롬프트 블록.
        Returns:
            str: Command / Crucial Constraints / Strictly Avoid 순서의 최종 프롬프트 문자열.
        """
        blocks: list[str] = []

        command_value = " ".join(merged_prompts.command).strip()
        if command_value:
            blocks.append(f"{COMMAND_KEY}: {command_value}")

        lines: list[str] = []
        for key, values in merged_prompts.crucial_constraints.items():
            cleaned_values = self._to_clean_list(values)
            if not cleaned_values:
                continue
            lines.append(f"- {key}: {', '.join(cleaned_values)}")
        if lines:
            blocks.append(f"{CRUCIAL_KEY}:\n" + "\n".join(lines))

        strictly_avoid_value = ", ".join(merged_prompts.strictly_avoid).strip()
        if strictly_avoid_value:
            blocks.append(f"{STRICTLY_AVOID_KEY}: {strictly_avoid_value}")

        return "\n\n".join(blocks).strip()

    def _map_prompt_values(self, text: str, variables: dict[str, str]) -> str:
        """
        [PLACEHOLDER] 토큰을 전달된 변수값으로 치환한다.
        Args:
            text: 치환 전 프롬프트 문자열.
            variables: 플레이스홀더 매핑 값. KEY와 [KEY] 스타일을 모두 지원한다.
        Returns:
            str: 플레이스홀더 치환이 완료된 문자열.
        """
        normalized_variables: dict[str, str] = {}
        for raw_key, raw_value in variables.items():
            key_text = str(raw_key).strip()
            if key_text.startswith("[") and key_text.endswith("]") and len(key_text) > 2:
                key_text = key_text[1:-1].strip()
            if not key_text:
                continue
            normalized_variables[key_text] = str(raw_value)

        def _replace(match: re.Match[str]) -> str:
            token = match.group(1)
            if token in normalized_variables:
                return normalized_variables[token]
            if token in SUPPORTED_PLACEHOLDER_KEYS:
                return match.group(0)
            return match.group(0)

        return PLACEHOLDER_PATTERN.sub(_replace, text)

    def _validate_color_palette_inputs(self, variables: dict[str, str]) -> None:
        """
        color_palette VFX에 필요한 필수 변수를 검증한다.
        Args:
            variables: 플레이스홀더 치환 변수 맵.
        Raises:
            ValueError: HAIR_COLOR 또는 EYE_COLOR가 비어 있거나 누락되면 발생한다.
        """
        required_keys = ("HAIR_COLOR", "EYE_COLOR")
        missing = [key for key in required_keys if not str(variables.get(key, "")).strip()]
        if missing:
            self._raise_value_error(
                code="E_MISSING_COLOR_PALETTE_PARAMS",
                detail="color_palette 사용 시 HAIR_COLOR, EYE_COLOR가 모두 필요합니다.",
            )

    def _to_clean_list(self, value: Any) -> list[str]:
        """
        스칼라/리스트 입력을 공백 제거된 문자열 리스트로 변환하고 빈 값은 제거한다.
        Args:
            value: str | list[Any] | None 형태의 입력값.
        Returns:
            list[str]: 정리된 비어 있지 않은 문자열 리스트.
        """
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        text = str(value).strip()
        return [text] if text else []
