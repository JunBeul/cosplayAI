from __future__ import annotations

from backend.core.settings import Settings
from backend.domain.models import PromptBundle

from .config_loader import load_json_file


OPTIONAL_VFX_KEYS = ("animal_features", "halo_vfx", "color_palette")


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
    ) -> PromptBundle:
        # 1) 공통 프롬프트 + 모드 프롬프트 + negative 프롬프트 JSON 로드
        variables = dict(variables or {})
        if vfx_params:
            # color_palette 같은 선택형 VFX에서 쓰는 치환값을 프롬프트 변수에 합친다.
            variables.update(vfx_params)

        base_data = load_json_file(self.settings.config_dir / "common_base.json")
        mode_data = load_json_file(self.settings.config_dir / mode_config_name)
        negative_data = load_json_file(self.settings.config_dir / "negative_prompt.json")

        # 2) 공통 positive + 모드별 positive 를 하나의 문자열로 합친다.
        base_text = " ".join(base_data.get("positive_prompts", {}).values())
        mode_text = " ".join(mode_data.get("prompts", {}).values())
        positive_parts = [base_text, mode_text]
        vfx_text = self._build_optional_vfx_text(vfx_options or [], variables)
        if vfx_text:
            positive_parts.append(vfx_text)
        positive = " ".join(part for part in positive_parts if part).strip()

        # 3) negative 프롬프트는 리스트이면 쉼표로 이어 붙인다.
        core_avoidance = negative_data.get("system_default", {}).get("core_avoidance", [])
        if isinstance(core_avoidance, list):
            negative = ", ".join(str(item) for item in core_avoidance)
        else:
            negative = str(core_avoidance)

        # 4) [REFERENCE_IMG] 같은 플레이스홀더를 실제 파일명/값으로 치환한다.
        for key, value in variables.items():
            placeholder = key if key.startswith("[") else f"[{key}]"
            positive = positive.replace(placeholder, value)

        return PromptBundle(positive=positive, negative=negative, mode_config_name=mode_config_name)

    def build_for_basic(
        self,
        illustration_filename: str,
        extra_variables: dict[str, str] | None = None,
        vfx_options: list[str] | None = None,
        vfx_params: dict[str, str] | None = None,
    ) -> PromptBundle:
        # 기능 1 전용 프롬프트 조립
        variables = {"REFERENCE_IMG": illustration_filename}
        if extra_variables:
            variables.update(extra_variables)
        return self.build(
            "mode1_general_trans.json",
            variables,
            vfx_options=vfx_options,
            vfx_params=vfx_params,
        )

    def build_for_with_master(
        self,
        illustration_filename: str,
        master_filename: str,
        extra_variables: dict[str, str] | None = None,
        vfx_options: list[str] | None = None,
        vfx_params: dict[str, str] | None = None,
    ) -> PromptBundle:
        # 기능 2 전용 프롬프트 조립 (일러스트 + 마스터 이미지)
        variables = {"REFERENCE_IMG": illustration_filename, "MASTER_IMG": master_filename}
        if extra_variables:
            variables.update(extra_variables)
        return self.build(
            "mode2_face_consistency.json",
            variables,
            vfx_options=vfx_options,
            vfx_params=vfx_params,
        )

    def build_for_master_image(
        self,
        person_filename: str,
        extra_variables: dict[str, str] | None = None,
    ) -> PromptBundle:
        # 기능 3 전용 프롬프트 조립 (인물 사진 -> 마스터 이미지)
        variables = {"PERSON_IMG": person_filename}
        if extra_variables:
            variables.update(extra_variables)
        return self.build("mode3_master_image.json", variables)

    def _build_optional_vfx_text(self, vfx_options: list[str], variables: dict[str, str]) -> str:
        # 선택형 VFX 프롬프트를 요청된 항목만 이어붙인다.
        if not vfx_options:
            return ""

        vfx_data = load_json_file(self.settings.config_dir / "VFX_prompt.json")
        vfx_prompts = vfx_data.get("prompts", {})

        selected_texts: list[str] = []
        seen: set[str] = set()
        for option in vfx_options:
            if option in seen:
                continue
            seen.add(option)

            if option not in OPTIONAL_VFX_KEYS:
                raise ValueError(
                    f"Unsupported vfx option: {option}. Allowed: {list(OPTIONAL_VFX_KEYS)}"
                )

            if option == "color_palette":
                self._validate_color_palette_inputs(variables)

            text = vfx_prompts.get(option)
            if text:
                selected_texts.append(str(text))

        return " ".join(selected_texts)

    def _validate_color_palette_inputs(self, variables: dict[str, str]) -> None:
        # color_palette 선택 시 색상 값이 둘 다 있어야 프롬프트 치환이 완성된다.
        required_keys = ("HAIR_COLOR", "EYE_COLOR")
        missing = [key for key in required_keys if not variables.get(key)]
        if missing:
            raise ValueError(
                f"color_palette requires {', '.join(required_keys)} in vfx_params"
            )
