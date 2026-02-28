"""
파일명: prompt_builder.py
작성자: JunBeul
설명: common/mode/user/VFX 프롬프트 JSON을 규칙에 맞게 병합하고, 플레이스홀더 치환과 negative 블록 포함 포맷으로 최종 텍스트 프롬프트를 생성한다.
상위 모듈: backend.services.pipelines
하위 모듈: backend.core.settings, backend.domain.models, backend.services.config_loader
"""


from __future__ import annotations
from copy import deepcopy
from typing import Any
from backend.core.settings import Settings
from backend.domain.models import PromptBundle
from .config_loader import load_json_file


VFX_OPTION_KEY_MAP = {
    "animal_features": "Crucial Constraints - Animal Features",
    "halo_vfx": "Crucial Constraints - Halo VFX",
    "color_palette": "Crucial Constraints - Styling",
}
OPTIONAL_VFX_KEYS = tuple(VFX_OPTION_KEY_MAP.keys())
CRUCIAL_PREFIX = "Crucial Constraints -"
COMMAND_KEY = "Command"
NEGATIVE_SECTION_KEY = "negative_prompts"
NEGATIVE_STRICT_KEY = "Strictly Avoid"
USER_CUSTOM_ADDITIONS_KEY = "Crucial Constraints - Additions"


class PromptBuilder:
    def __init__(self, settings: Settings) -> None:
        """
        PromptBuilder를 초기화한다.
        Args:
            - settings: 설정 객체.
        """
        self.settings = settings

    def build(
        self,
        mode_config_name: str,
        variables: dict[str, str] | None = None,
        vfx_options: list[str] | None = None,
        vfx_params: dict[str, str] | None = None,
        user_custom_text: str | None = None,
    ) -> PromptBundle:
        """
        모드 설정 파일 기준으로 최종 프롬프트를 조립한다.
        Args:
            - mode_config_name: 모드 JSON 파일명.
            - variables: 플레이스홀더 치환 변수.
            - vfx_options: 활성화할 VFX 옵션 목록.
            - vfx_params: VFX 옵션용 추가 변수.
            - user_custom_text: 사용자 추가 텍스트.
        Returns:
            - PromptBundle: 최종 텍스트와 모드 파일명을 담은 객체.
        """
        variables = dict(variables or {})
        vfx_params = dict(vfx_params or {})
        if vfx_params:
            variables.update(vfx_params)

        merged = self._build_merged_prompt_config(
            mode_config_name=mode_config_name,
            vfx_options=vfx_options or [],
            variables=variables,
            user_custom_text=user_custom_text,
        )

        prompt_text = self._generate_prompt_text(merged)
        prompt_text = self._map_prompt_text(prompt_text, variables)
        return PromptBundle(text=prompt_text, mode_config_name=mode_config_name)

    def _build_merged_prompt_config(
        self,
        mode_config_name: str,
        vfx_options: list[str],
        variables: dict[str, str],
        user_custom_text: str | None,
    ) -> dict[str, Any]:
        """
        공통/모드/유저/VFX 프롬프트 설정을 병합한다.
        Args:
            - mode_config_name: 모드 JSON 파일명.
            - vfx_options: 활성화할 VFX 옵션 목록.
            - variables: 플레이스홀더 치환 변수.
            - user_custom_text: 사용자 추가 텍스트.
        Returns:
            - dict[str, Any]: prompts와 negative_prompts를 가진 병합 결과.
        """
        base_data = deepcopy(load_json_file(self.settings.config_dir / "common_base.json"))
        mode_data = load_json_file(self.settings.config_dir / mode_config_name)
        user_custom_data = load_json_file(self.settings.config_dir / "user_custom_prompts.json")
        vfx_data = load_json_file(self.settings.config_dir / "VFX_prompt.json")

        merged_prompts = deepcopy(base_data.get("prompts", {}))
        merged_negative = deepcopy(base_data.get(NEGATIVE_SECTION_KEY, {}))

        self._apply_user_custom_text(user_custom_data, user_custom_text)

        merged_prompts = self._merge_prompt_sections(merged_prompts, mode_data.get("prompts", {}))
        merged_prompts = self._merge_prompt_sections(merged_prompts, user_custom_data.get("prompts", {}))

        selected_vfx_prompts = self._select_vfx_prompts(
            vfx_all_prompts=vfx_data.get("prompts", {}),
            vfx_options=vfx_options,
            variables=variables,
        )
        merged_prompts = self._merge_prompt_sections(merged_prompts, selected_vfx_prompts)

        self._merge_negative_sections(merged_negative, mode_data.get(NEGATIVE_SECTION_KEY, {}))
        self._merge_negative_sections(merged_negative, user_custom_data.get(NEGATIVE_SECTION_KEY, {}))
        self._merge_negative_sections(merged_negative, vfx_data.get(NEGATIVE_SECTION_KEY, {}))

        return {
            "prompts": merged_prompts,
            NEGATIVE_SECTION_KEY: merged_negative,
        }

    def _select_vfx_prompts(
        self,
        vfx_all_prompts: dict[str, Any],
        vfx_options: list[str],
        variables: dict[str, str],
    ) -> dict[str, Any]:
        """
        선택한 VFX 옵션에 대응하는 프롬프트만 추출한다.
        Args:
            - vfx_all_prompts: VFX_prompt.json의 prompts 섹션.
            - vfx_options: 활성화할 VFX 옵션 목록.
            - variables: 검증에 사용할 치환 변수.
        Returns:
            - dict[str, Any]: 선택된 VFX 프롬프트.
        """
        if not vfx_options:
            return {}

        selected: dict[str, Any] = {}
        seen_options: set[str] = set()

        for option in vfx_options:
            if option in seen_options:
                continue
            seen_options.add(option)

            if option not in OPTIONAL_VFX_KEYS:
                raise ValueError(
                    f"Unsupported vfx option: {option}. Allowed: {list(OPTIONAL_VFX_KEYS)}"
                )

            if option == "color_palette":
                self._validate_color_palette_inputs(variables)

            json_key = VFX_OPTION_KEY_MAP[option]
            if json_key in vfx_all_prompts:
                selected[json_key] = vfx_all_prompts[json_key]

        return selected

    def _apply_user_custom_text(self, user_custom_data: dict[str, Any], user_custom_text: str | None) -> None:
        """
        사용자 커스텀 텍스트를 Additions 항목에 반영한다.
        Args:
            - user_custom_data: user_custom_prompts.json 데이터.
            - user_custom_text: 사용자 추가 텍스트.
        """
        if user_custom_text is None:
            return

        text = user_custom_text.strip()
        if not text:
            return

        prompts = user_custom_data.setdefault("prompts", {})
        prompts[USER_CUSTOM_ADDITIONS_KEY] = text

    def _merge_prompt_sections(self, target_prompts: dict[str, Any], source_prompts: dict[str, Any]) -> dict[str, Any]:
        """
        prompt 섹션을 규칙에 맞게 병합한다.
        Args:
            - target_prompts: 병합 대상 prompt 딕셔너리.
            - source_prompts: 병합할 source prompt 딕셔너리.
        Returns:
            - dict[str, Any]: 병합된 prompt 딕셔너리.
        """
        for key, source_value in source_prompts.items():
            if self._is_empty_prompt_value(source_value):
                continue

            if key in target_prompts:
                target_prompts[key] = self._merge_prompt_value(key, target_prompts[key], source_value)
            else:
                target_prompts = self._insert_after_last_crucial_constraint(target_prompts, key, source_value)

        return target_prompts

    def _merge_prompt_value(self, key: str, base_value: Any, incoming_value: Any) -> Any:
        """
        동일 prompt 키의 값을 병합한다.
        Args:
            - key: 병합 키.
            - base_value: 기존 값.
            - incoming_value: 신규 값.
        Returns:
            - Any: 병합된 값.
        """
        if key == COMMAND_KEY:
            base_text = self._coerce_prompt_text(base_value)
            incoming_text = self._coerce_prompt_text(incoming_value)
            if not base_text:
                return incoming_text
            if not incoming_text:
                return base_text
            return f"{base_text} {incoming_text}".strip()

        base_list = self._coerce_prompt_list(base_value)
        incoming_list = self._coerce_prompt_list(incoming_value)
        return [*base_list, *incoming_list]

    def _insert_after_last_crucial_constraint(
        self,
        prompts: dict[str, Any],
        new_key: str,
        new_value: Any,
    ) -> dict[str, Any]:
        """
        신규 키를 마지막 Crucial Constraints 키 뒤에 삽입한다.
        Args:
            - prompts: 기존 prompt 딕셔너리.
            - new_key: 삽입할 키.
            - new_value: 삽입할 값.
        Returns:
            - dict[str, Any]: 삽입이 반영된 딕셔너리.
        """
        items = list(prompts.items())
        insert_index = len(items)

        for index, (key, _value) in enumerate(items):
            if isinstance(key, str) and key.startswith(CRUCIAL_PREFIX):
                insert_index = index + 1

        items.insert(insert_index, (new_key, new_value))
        return dict(items)

    def _merge_negative_sections(self, target_negative: dict[str, Any], source_negative: dict[str, Any]) -> None:
        """
        negative_prompts 섹션을 문자열 기준으로 병합한다.
        Args:
            - target_negative: 병합 대상 negative 딕셔너리.
            - source_negative: 병합할 source negative 딕셔너리.
        """
        if not isinstance(source_negative, dict):
            return

        for key, value in source_negative.items():
            if value is None:
                continue
            incoming_text = str(value).strip()
            if not incoming_text:
                continue
            base_text = str(target_negative.get(key, "")).strip()
            target_negative[key] = f"{base_text}, {incoming_text}" if base_text else incoming_text

    def _generate_prompt_text(self, merged: dict[str, Any]) -> str:
        """
        병합 결과를 최종 텍스트 프롬프트로 직렬화한다.
        Args:
            - merged: 병합된 프롬프트 데이터.
        Returns:
            - str: 최종 프롬프트 문자열.
        """
        prompts = merged.get("prompts", {})
        negative_text = ""
        negative_section = merged.get(NEGATIVE_SECTION_KEY, {})
        if isinstance(negative_section, dict):
            negative_text = str(negative_section.get(NEGATIVE_STRICT_KEY, "")).strip()

        blocks: list[str] = []

        for key, raw_value in prompts.items():
            if self._is_empty_prompt_value(raw_value):
                continue

            if key == COMMAND_KEY:
                command_text = self._coerce_prompt_text(raw_value)
                if command_text:
                    blocks.append(f"{COMMAND_KEY}: {command_text}")
                continue

            if isinstance(key, str) and key.startswith(CRUCIAL_PREFIX):
                lines = self._coerce_prompt_list(raw_value)
                if not lines:
                    continue
                blocks.append(f"{key}:\n" + "\n".join(lines))
                continue

            if isinstance(raw_value, list):
                lines = self._coerce_prompt_list(raw_value)
                if not lines:
                    continue
                blocks.append(f"{key}:\n" + "\n".join(lines))
                continue

            text = self._coerce_prompt_text(raw_value)
            if text:
                blocks.append(f"{key}: {text}")

        if negative_text:
            blocks.append(f"{NEGATIVE_SECTION_KEY}({NEGATIVE_STRICT_KEY}):{negative_text}")

        return "\n\n".join(blocks).strip()

    def _map_prompt_text(self, text: str, variables: dict[str, str]) -> str:
        """
        [KEY] 플레이스홀더를 변수 값으로 1:1 치환한다.
        Args:
            - text: 치환 전 텍스트.
            - variables: 치환 변수.
        Returns:
            - str: 치환된 텍스트.
        """
        for key, value in variables.items():
            placeholder = key if key.startswith("[") else f"[{key}]"
            text = text.replace(placeholder, str(value))
        return text

    def _validate_color_palette_inputs(self, variables: dict[str, str]) -> None:
        """
        color_palette 옵션의 필수 변수를 검증한다.
        Args:
            - variables: 치환 변수.
        """
        required_keys = ("HAIR_COLOR", "EYE_COLOR")
        missing = [key for key in required_keys if not variables.get(key)]
        if missing:
            raise ValueError(f"color_palette requires {', '.join(required_keys)} in vfx_params")

    def _is_empty_prompt_value(self, value: Any) -> bool:
        """
        프롬프트 값이 비었는지 확인한다.
        Args:
            - value: 확인 대상 값.
        Returns:
            - bool: 비었으면 True.
        """
        if value is None:
            return True
        if isinstance(value, str):
            return value.strip() == ""
        if isinstance(value, list):
            return len([v for v in value if str(v).strip()]) == 0
        return False

    def _coerce_prompt_list(self, value: Any) -> list[str]:
        """
        입력값을 문자열 리스트로 정규화한다.
        Args:
            - value: 정규화 대상 값.
        Returns:
            - list[str]: 정규화된 문자열 리스트.
        """
        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()]
        text = self._coerce_prompt_text(value)
        return [text] if text else []

    def _coerce_prompt_text(self, value: Any) -> str:
        """
        입력값을 단일 문자열로 정규화한다.
        Args:
            - value: 정규화 대상 값.
        Returns:
            - str: 정규화된 문자열.
        """
        if value is None:
            return ""
        if isinstance(value, list):
            return " ".join(str(v).strip() for v in value if str(v).strip()).strip()
        return str(value).strip()
