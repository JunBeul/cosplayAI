from __future__ import annotations

from backend.core.settings import Settings
from backend.domain.models import PromptBundle

from .config_loader import load_json_file


class PromptBuilder:
    def __init__(self, settings: Settings) -> None:
        # configs 폴더 경로 등 프롬프트 조립에 필요한 설정을 보관
        self.settings = settings

    def build(self, mode_config_name: str, variables: dict[str, str] | None = None) -> PromptBundle:
        # 1) 공통 프롬프트 + 모드 프롬프트 + negative 프롬프트 JSON 로드
        variables = variables or {}

        base_data = load_json_file(self.settings.config_dir / "common_base.json")
        mode_data = load_json_file(self.settings.config_dir / mode_config_name)
        negative_data = load_json_file(self.settings.config_dir / "negative_prompt.json")

        # 2) 공통 positive + 모드별 positive 를 하나의 문자열로 합친다.
        base_text = " ".join(base_data.get("positive_prompts", {}).values())
        mode_text = " ".join(mode_data.get("prompts", {}).values())
        positive = f"{base_text} {mode_text}".strip()

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

    def build_for_basic(self, illustration_filename: str, extra_variables: dict[str, str] | None = None) -> PromptBundle:
        # 기능 1 전용 프롬프트 조립
        variables = {"REFERENCE_IMG": illustration_filename}
        if extra_variables:
            variables.update(extra_variables)
        return self.build("mode1_general_trans.json", variables)

    def build_for_with_master(
        self,
        illustration_filename: str,
        master_filename: str,
        extra_variables: dict[str, str] | None = None,
    ) -> PromptBundle:
        # 기능 2 전용 프롬프트 조립 (일러스트 + 마스터 이미지)
        variables = {"REFERENCE_IMG": illustration_filename, "MASTER_IMG": master_filename}
        if extra_variables:
            variables.update(extra_variables)
        return self.build("mode2_face_consistency.json", variables)

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
