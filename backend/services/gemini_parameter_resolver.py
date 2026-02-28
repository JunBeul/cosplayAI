"""
파일명: gemini_parameter_resolver.py
작성자: Codex
설명: Gemini GenerateContentConfig 파라미터를 단일 정책으로 해석/조합한다.
상위 모듈: backend.services.pipelines
하위 모듈: 없음
"""


from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import NoReturn, TypedDict
import struct


ERROR_NAMESPACE = "GEMINI_PARAMETER_RESOLVER"

class SafetySettingPolicy(TypedDict):
    """safety_settings 한 항목 정책."""
    category: str
    threshold: str

class ImageConfigPolicy(TypedDict, total=False):
    """image_config 정책."""
    aspect_ratio: str
    image_size: str

# 고정 Generation 정책
FIXED_TEMPERATURE = 1.0  # 생성 다양성(창의성) 강도. (0.0 ~ 2.0)
FIXED_RESPONSE_MODALITY = "IMAGE"  # 응답 모달리티. (IMAGE 고정)
FIXED_TOP_P = 0.95  # 누적 확률 샘플링. (0.0 ~ 1.0)
FIXED_CANDIDATE_COUNT = 1  # 후보 수. (1 ~ 10)
FIXED_SAFETY_SETTINGS: tuple[SafetySettingPolicy, ...] = (
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_CIVIC_INTEGRITY", "threshold": "BLOCK_NONE"},
)
# 기본 image_config 정책
DEFAULT_IMAGE_CONFIG_POLICY: ImageConfigPolicy = {
    "aspect_ratio": "AUTO",  # AUTO 또는 SUPPORTED_ASPECT_RATIOS
    "image_size": "1K",  # AUTO 또는 1K/2K/4K
}
# 모드별 image_config 정책
MODE_IMAGE_CONFIG_OVERRIDES: dict[str, ImageConfigPolicy] = {
    "mode1_general_trans.json": {},
    "mode2_face_consistency.json": {},
    "mode3_master_image.json": {},
}


@dataclass(frozen=True)
class GeminiParameterContext:
    """요청 단위 파라미터 해석 입력"""
    mode_config_name: str
    reference_paths: list[Path] = field(default_factory=list)


@dataclass(frozen=True)
class ResolvedGeminiParameters:
    """Resolver 확정 결과"""
    generate_content_config: object
    resolved_image_config: ImageConfigPolicy
    resolved_safety_settings: list[SafetySettingPolicy]


class GeminiParameterResolver:
    """Gemini 호출 파라미터를 중앙에서 관리"""
    # 지원 값 정책
    SUPPORTED_ASPECT_RATIOS: tuple[str, ...] = (
        "1:1",
        "3:2",
        "2:3",
        "3:4",
        "4:3",
        "4:5",
        "5:4",
        "9:16",
        "16:9",
        "21:9",
    )
    SUPPORTED_IMAGE_SIZES: tuple[str, ...] = ("1K", "2K", "4K")

    def _raise_value_error(self, code: str, detail: str) -> NoReturn:
        """표준 ValueError를 발생시킨다."""
        raise ValueError(f"[{ERROR_NAMESPACE}:{code}] {detail}")

    def _raise_runtime_error(self, code: str, detail: str) -> NoReturn:
        """표준 RuntimeError를 발생시킨다."""
        raise RuntimeError(f"[{ERROR_NAMESPACE}:{code}] {detail}")

    def resolve(self, context: GeminiParameterContext) -> ResolvedGeminiParameters:
        """
        요청 컨텍스트에서 최종 GenerateContentConfig를 확정한다.
        Args:
            context: GeminiParameterContext: 모드/레퍼런스 입력.
        Returns:
            ResolvedGeminiParameters: 호출 config와 추적 메타데이터.
        Raises:
            ValueError: 정책 값이 유효하지 않을 때 발생한다.
            RuntimeError: SDK import 실패 등 런타임 오류.
        """
        image_policy = self._build_effective_image_config_policy(mode_config_name=context.mode_config_name)

        image_config = self._resolve_image_config(
            reference_paths=context.reference_paths,
            image_config=image_policy,
        )
        safety_settings = self._resolve_safety_settings()

        generate_content_config = self._build_generate_content_config(
            image_config=image_config,
            safety_settings=safety_settings,
        )

        return ResolvedGeminiParameters(
            generate_content_config=generate_content_config,
            resolved_image_config=image_config,
            resolved_safety_settings=safety_settings,
        )

    def _build_effective_image_config_policy(self, mode_config_name: str) -> ImageConfigPolicy:
        """mode별 image_config 정책을 확정한다."""
        if mode_config_name not in MODE_IMAGE_CONFIG_OVERRIDES:
            allowed = ", ".join(sorted(MODE_IMAGE_CONFIG_OVERRIDES))
            self._raise_value_error(
                code="E_UNSUPPORTED_MODE",
                detail=f"지원하지 않는 mode_config_name='{mode_config_name}'. 허용값: {allowed}",
            )

        merged: ImageConfigPolicy = dict(DEFAULT_IMAGE_CONFIG_POLICY)
        merged.update(MODE_IMAGE_CONFIG_OVERRIDES[mode_config_name])
        return merged

    def _resolve_image_config(self, reference_paths: list[Path], image_config: ImageConfigPolicy) -> ImageConfigPolicy:
        """
        첫 번째 레퍼런스 이미지를 기준으로 image_config를 확정한다.
        Args:
            reference_paths: list[Path]: 요청 레퍼런스 이미지 목록.
            image_config: ImageConfigPolicy: 정책 image_config 값.
        Returns:
            ImageConfigPolicy: 최종 image_config.
        Raises:
            ValueError: image_config 값이 유효하지 않으면 발생한다.
        """
        resolved: ImageConfigPolicy = {
            "aspect_ratio": "AUTO",
            "image_size": "1K",
        }

        if isinstance(image_config, dict):
            for key in ("aspect_ratio", "image_size"):
                value = image_config.get(key)
                if value is not None:
                    resolved[key] = value  # type: ignore[index]

        # NOTE: 비율/사이즈 계산은 첫 번째 레퍼런스 이미지만 사용한다.
        reference = reference_paths[0] if reference_paths else None
        width_height = self._read_image_size(reference) if reference else None

        if str(resolved.get("aspect_ratio", "")).upper() == "AUTO":
            if width_height is None:
                resolved["aspect_ratio"] = "1:1"
            else:
                width, height = width_height
                resolved["aspect_ratio"] = self._pick_nearest_aspect_ratio(width=width, height=height)

        if str(resolved.get("image_size", "")).upper() == "AUTO":
            if width_height is None:
                resolved["image_size"] = "1K"
            else:
                width, height = width_height
                resolved["image_size"] = self._pick_image_size(width=width, height=height)

        aspect_ratio = str(resolved.get("aspect_ratio", "")).strip()
        if aspect_ratio not in self.SUPPORTED_ASPECT_RATIOS:
            self._raise_value_error(
                code="E_UNSUPPORTED_ASPECT_RATIO",
                detail=f"지원하지 않는 aspect_ratio='{aspect_ratio}'",
            )

        image_size = str(resolved.get("image_size", "")).strip()
        if image_size not in self.SUPPORTED_IMAGE_SIZES:
            self._raise_value_error(
                code="E_UNSUPPORTED_IMAGE_SIZE",
                detail=f"지원하지 않는 image_size='{image_size}'",
            )

        return resolved

    def _resolve_safety_settings(self) -> list[SafetySettingPolicy]:
        """고정 safety_settings를 반환한다."""
        return [dict(item) for item in FIXED_SAFETY_SETTINGS]

    def _build_generate_content_config(
        self,
        image_config: ImageConfigPolicy,
        safety_settings: list[SafetySettingPolicy],
    ) -> object:
        """
        SDK GenerateContentConfig를 생성한다.
        Args:
            image_config: ImageConfigPolicy: image_config.
            safety_settings: list[SafetySettingPolicy]: safety_settings.
        Returns:
            object: GenerateContentConfig 객체.
        Raises:
            RuntimeError: google-genai import 실패 시 발생한다.
        """
        try:
            from google.genai import types
        except ImportError:
            self._raise_runtime_error(
                code="E_SDK_IMPORT_FAILED",
                detail="google-genai package is required. Install with: pip install google-genai",
            )

        safety_items = [
            types.SafetySetting(
                category=getattr(types.HarmCategory, item["category"], item["category"]),
                threshold=getattr(types.HarmBlockThreshold, item["threshold"], item["threshold"]),
            )
            for item in safety_settings
        ]

        image_kwargs: dict[str, object] = {}
        for key in ("aspect_ratio", "image_size"):
            value = image_config.get(key)
            if value is not None:
                image_kwargs[key] = value

        config_kwargs: dict[str, object] = {
            "temperature": FIXED_TEMPERATURE,
            "response_modalities": [FIXED_RESPONSE_MODALITY],
            "top_p": FIXED_TOP_P,
            "candidate_count": FIXED_CANDIDATE_COUNT,
            "safety_settings": safety_items,
        }

        if image_kwargs:
            config_kwargs["image_config"] = types.ImageConfig(**image_kwargs)

        return types.GenerateContentConfig(**config_kwargs)

    def _pick_nearest_aspect_ratio(self, width: int, height: int) -> str:
        """폭/높이 비율과 가장 가까운 지원 ratio를 선택한다."""
        if width <= 0 or height <= 0:
            return "1:1"

        target = float(width) / float(height)

        def _ratio_value(ratio: str) -> float:
            left, right = ratio.split(":")
            return float(left) / float(right)

        return min(self.SUPPORTED_ASPECT_RATIOS, key=lambda ratio: abs(_ratio_value(ratio) - target))

    def _pick_image_size(self, width: int, height: int) -> str:
        """해상도 기준 image_size를 선택한다."""
        longest = max(width, height)
        if longest >= 3072:
            return "4K"
        if longest >= 1536:
            return "2K"
        return "1K"

    def _read_image_size(self, path: Path | None) -> tuple[int, int] | None:
        """이미지 크기(width, height)를 읽는다."""
        if path is None or not path.exists() or not path.is_file():
            return None

        try:
            data = path.read_bytes()
        except OSError:
            return None

        # PNG
        if len(data) >= 24 and data.startswith(b"\x89PNG\r\n\x1a\n"):
            return struct.unpack(">I", data[16:20])[0], struct.unpack(">I", data[20:24])[0]

        # JPEG
        if len(data) >= 4 and data[0:2] == b"\xff\xd8":
            return self._read_jpeg_size(data)

        return None

    def _read_jpeg_size(self, data: bytes) -> tuple[int, int] | None:
        """JPEG 바이트에서 SOF 세그먼트로 크기를 추출한다."""
        sof_markers = {
            0xC0,
            0xC1,
            0xC2,
            0xC3,
            0xC5,
            0xC6,
            0xC7,
            0xC9,
            0xCA,
            0xCB,
            0xCD,
            0xCE,
            0xCF,
        }

        idx = 2
        length = len(data)
        while idx < length:
            if data[idx] != 0xFF:
                idx += 1
                continue

            while idx < length and data[idx] == 0xFF:
                idx += 1
            if idx >= length:
                break

            marker = data[idx]
            idx += 1
            if marker in (0xD8, 0xD9):
                continue

            if idx + 2 > length:
                break
            segment_length = int.from_bytes(data[idx: idx + 2], "big")
            if segment_length < 2 or idx + segment_length > length:
                break

            if marker in sof_markers:
                if idx + 7 > length:
                    break
                height = int.from_bytes(data[idx + 3: idx + 5], "big")
                width = int.from_bytes(data[idx + 5: idx + 7], "big")
                if width > 0 and height > 0:
                    return width, height
                break

            idx += segment_length

        return None
