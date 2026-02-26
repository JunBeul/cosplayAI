"""
파일명: prompt_builder.py
작성자: JunBeul
설명: common/mode/user/VFX 프롬프트 JSON을 규칙에 맞게 병합하고, 플레이스홀더 치환과 negative 블록 포함 형식화를 거쳐 최종 텍스트 프롬프트를 생성한다.
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
    # UI/CLI 토글 옵션명 -> VFX_prompt.json의 실제 키
    "animal_features": "Crucial Constraints - Animal Features",
    "halo_vfx": "Crucial Constraints - Halo VFX",
    # color_palette는 공통 Styling 항목에 덧붙이는 구조
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
        # configs 폴더 경로 등 프롬프트 조립에 필요한 설정을 보관
        self.settings = settings

    def build(
        self,
        mode_config_name: str,
        variables: dict[str, str] | None = None,
        vfx_options: list[str] | None = None,
        vfx_params: dict[str, str] | None = None,
        user_custom_text: str | None = None,
    ) -> PromptBundle:
        # mode1/mode2 공통 빌드:
        # 1) 병합
        # 2) 텍스트 생성
        # 3) 텍스트 매핑(변수 치환)
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

        # 텍스트 생성 -> 텍스트 매핑
        prompt_text = self._generate_prompt_text(merged)
        prompt_text = self._map_prompt_text(prompt_text, variables)

        return PromptBundle(text=prompt_text, mode_config_name=mode_config_name)

    def build_for_basic(
        self,
        illustration_filename: str,
        extra_variables: dict[str, str] | None = None,
        user_custom_text: str | None = None,
        vfx_options: list[str] | None = None,
        vfx_params: dict[str, str] | None = None,
    ) -> PromptBundle:
        # 기능 1 전용 프롬프트 조립 (common + mode1 + user_custom + selected VFX)
        variables = {"REFERENCE_IMG": illustration_filename}
        if extra_variables:
            variables.update(extra_variables)
        return self.build(
            "mode1_general_trans.json",
            variables,
            user_custom_text=user_custom_text,
            vfx_options=vfx_options,
            vfx_params=vfx_params,
        )

    def build_for_with_master(
        self,
        illustration_filename: str,
        master_filename: str,
        extra_variables: dict[str, str] | None = None,
        user_custom_text: str | None = None,
        vfx_options: list[str] | None = None,
        vfx_params: dict[str, str] | None = None,
    ) -> PromptBundle:
        # 기능 2 전용 프롬프트 조립 (common + mode2 + user_custom + selected VFX)
        variables = {"REFERENCE_IMG": illustration_filename, "MASTER_IMG": master_filename}
        if extra_variables:
            variables.update(extra_variables)
        return self.build(
            "mode2_face_consistency.json",
            variables,
            user_custom_text=user_custom_text,
            vfx_options=vfx_options,
            vfx_params=vfx_params,
        )

    def build_for_master_image(
        self,
        person_filename: str,
        extra_variables: dict[str, str] | None = None,
    ) -> PromptBundle:
        # 기능 3(mode3)는 프롬프트 JSON 구조를 대폭 개편할 예정이므로 현재 구현을 제거한다.
        # 함수 시그니처만 유지하고, 추후 이 위치에 단독 텍스트 변환 로직을 구현할 예정.
        _ = (person_filename, extra_variables)
        raise NotImplementedError("mode3_master_image prompt builder is planned but not implemented yet")

    def _build_merged_prompt_config(
        self,
        mode_config_name: str,
        vfx_options: list[str],
        variables: dict[str, str],
        user_custom_text: str | None,
    ) -> dict[str, Any]:
        base_data = deepcopy(load_json_file(self.settings.config_dir / "common_base.json"))
        mode_data = load_json_file(self.settings.config_dir / mode_config_name)
        user_custom_data = load_json_file(self.settings.config_dir / "user_custom_prompts.json")
        vfx_data = load_json_file(self.settings.config_dir / "VFX_prompt.json")

        merged_prompts = deepcopy(base_data.get("prompts", {}))
        merged_negative = deepcopy(base_data.get(NEGATIVE_SECTION_KEY, {}))

        # 유저 입력은 선택사항이며, 입력 시 Additions 항목에 값으로 사용한다.
        self._apply_user_custom_text(user_custom_data, user_custom_text)

        # 순서대로 병합: mode -> user_custom -> selected VFX
        merged_prompts = self._merge_prompt_sections(merged_prompts, mode_data.get("prompts", {}))
        merged_prompts = self._merge_prompt_sections(merged_prompts, user_custom_data.get("prompts", {}))

        selected_vfx_prompts = self._select_vfx_prompts(
            vfx_all_prompts=vfx_data.get("prompts", {}),
            vfx_options=vfx_options,
            variables=variables,
        )
        merged_prompts = self._merge_prompt_sections(merged_prompts, selected_vfx_prompts)

        # 추후 확장 대비: 다른 파일에 negative_prompts가 생겨도 병합 가능하게 유지
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
        # 선택형 VFX만 추출하여 병합 대상 프롬프트 딕셔너리를 만든다.
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
            if json_key not in vfx_all_prompts:
                continue
            selected[json_key] = vfx_all_prompts[json_key]

        return selected

    def _apply_user_custom_text(self, user_custom_data: dict[str, Any], user_custom_text: str | None) -> None:
        if user_custom_text is None:
            return

        text = user_custom_text.strip()
        if not text:
            return

        prompts = user_custom_data.setdefault("prompts", {})
        prompts[USER_CUSTOM_ADDITIONS_KEY] = text

    def _merge_prompt_sections(self, target_prompts: dict[str, Any], source_prompts: dict[str, Any]) -> dict[str, Any]:
        # 병합 규칙:
        # 1) 동일 키가 있으면 common 값(대상)에 source 값을 추가
        # 2) 동일 키가 없으면 Crucial Constraints 구간 마지막 뒤에 삽입
        for key, source_value in source_prompts.items():
            if self._is_empty_prompt_value(source_value):
                continue

            if key in target_prompts:
                target_prompts[key] = self._merge_prompt_value(key, target_prompts[key], source_value)
            else:
                target_prompts = self._insert_after_last_crucial_constraint(target_prompts, key, source_value)

        return target_prompts

    def _merge_prompt_value(self, key: str, base_value: Any, incoming_value: Any) -> Any:
        if key == COMMAND_KEY:
            # Command는 문자열 중심 항목이라 자연스러운 문장 연결로 병합
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
        # "Crucial Constraints -" 계열 마지막 위치 뒤에 새 키를 삽입한다.
        items = list(prompts.items())
        insert_index = len(items)

        for index, (key, _value) in enumerate(items):
            if isinstance(key, str) and key.startswith(CRUCIAL_PREFIX):
                insert_index = index + 1

        items.insert(insert_index, (new_key, new_value))
        return dict(items)

    def _merge_negative_sections(self, target_negative: dict[str, Any], source_negative: dict[str, Any]) -> None:
        if not isinstance(source_negative, dict):
            return

        for key, value in source_negative.items():
            if value in (None, "", []):
                continue
            if key in target_negative and target_negative.get(key):
                target_negative[key] = self._merge_negative_value(target_negative[key], value)
            else:
                target_negative[key] = value

    def _merge_negative_value(self, base_value: Any, incoming_value: Any) -> str:
        base_text = self._coerce_negative_text(base_value)
        incoming_text = self._coerce_negative_text(incoming_value)
        if not base_text:
            return incoming_text
        if not incoming_text:
            return base_text
        return f"{base_text}, {incoming_text}"

    def _generate_prompt_text(self, merged: dict[str, Any]) -> str:
        # 최종 텍스트 포맷:
        # Command: ...
        #
        # Crucial Constraints - ...:
        # ...
        # ...
        #
        # negative_prompts(Strictly Avoid):...
        prompts = merged.get("prompts", {})
        negative_text = self._extract_negative_prompt(merged)
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

    def _extract_negative_prompt(self, merged: dict[str, Any]) -> str:
        negative_section = merged.get(NEGATIVE_SECTION_KEY, {})
        if not isinstance(negative_section, dict):
            return ""

        strict_avoid = negative_section.get(NEGATIVE_STRICT_KEY, "")
        return self._coerce_negative_text(strict_avoid)

    def _map_prompt_text(self, text: str, variables: dict[str, str]) -> str:
        # 텍스트 생성 후 플레이스홀더를 실제 값으로 치환
        for key, value in variables.items():
            placeholder = key if key.startswith("[") else f"[{key}]"
            text = text.replace(placeholder, str(value))
        return text

    def _validate_color_palette_inputs(self, variables: dict[str, str]) -> None:
        # color_palette 선택 시 색상 값이 둘 다 있어야 프롬프트 치환이 완성된다.
        required_keys = ("HAIR_COLOR", "EYE_COLOR")
        missing = [key for key in required_keys if not variables.get(key)]
        if missing:
            raise ValueError(f"color_palette requires {', '.join(required_keys)} in vfx_params")

    def _is_empty_prompt_value(self, value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            return value.strip() == ""
        if isinstance(value, list):
            return len([v for v in value if str(v).strip()]) == 0
        return False

    def _coerce_prompt_list(self, value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()]
        text = self._coerce_prompt_text(value)
        return [text] if text else []

    def _coerce_prompt_text(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, list):
            # 비정상 구조 방어: 리스트면 문자열로 합쳐 Command에 반영
            return " ".join(str(v).strip() for v in value if str(v).strip()).strip()
        return str(value).strip()

    def _coerce_negative_text(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, list):
            return ", ".join(str(v).strip() for v in value if str(v).strip())
        return str(value).strip()
