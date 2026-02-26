"""
파일명: gemini_image_service.py
작성자: JunBeul
설명: 이미지 파일과 텍스트 프롬프트를 Gemini 멀티모달 입력(contents)으로 구성하고, google-genai의 generate_content를 호출한 뒤 응답에서 생성된 이미지 바이트를 추출한다.
상위 모듈: backend.services.pipelines
하위 모듈: backend.domain.models
"""


from __future__ import annotations
import mimetypes
from pathlib import Path
from backend.domain.models import PromptBundle


class GeminiImageService:
    def __init__(
        self,
        api_key: str | None,
        model_name: str,
    ) -> None:
        # 외부 모델 호출(google-genai, Gemini image) 책임만 담당
        self.api_key = api_key
        self.model_name = model_name

    def generate_image(self, reference_paths: list[Path], prompt: PromptBundle) -> bytes:
        # 1) API 키 확인
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")

        try:
            # 2) 필요할 때만 라이브러리를 import (테스트/문서 작업 시 부담 감소)
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise RuntimeError("google-genai package is required. Install with: pip install google-genai") from exc

        # 3) API 키 기반 클라이언트 생성
        client = genai.Client(api_key=self.api_key)

        # 4) 멀티모달 입력 구성 (이미지 Part + 텍스트 프롬프트)
        contents: list[object] = [
            self._image_part_from_path(path, types) for path in reference_paths
        ]
        role_hint = self._build_role_hint_text(len(reference_paths))
        if role_hint:
            contents.append(role_hint)
        # prompt_builder가 만들어준 최종 포맷 텍스트를 그대로 전달한다.
        contents.append(prompt.text)

        # 5) Gemini 2.5 Flash Image 생성 호출
        result = client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=1.0,
                responseModalities=["IMAGE"],
                safetySettings=[
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                        threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                    )
                ],
            ),
        )

        # 6) 응답에서 첫 번째 이미지 파트 추출
        image_bytes = self._extract_first_image_bytes(result)
        if image_bytes is None:
            raise RuntimeError("Gemini image response returned no inline image data")

        return image_bytes

    def _image_part_from_path(self, path: Path, types_module):
        mime_type, _ = mimetypes.guess_type(str(path))
        if not mime_type:
            mime_type = "image/png"

        image_bytes = path.read_bytes()
        return types_module.Part.from_bytes(data=image_bytes, mime_type=mime_type)

    def _build_role_hint_text(self, reference_count: int) -> str:
        # 이미지 순서를 모델에게 알려주는 보조 텍스트 (프롬프트 본문과 분리)
        if reference_count == 2:
            return (
                "The first image is the illustration reference for pose/costume/style. "
                "The second image is the master face reference for identity consistency. "
            )
        if reference_count == 1:
            return "A reference image is provided. Use it faithfully according to the prompt."
        return ""

    def _extract_first_image_bytes(self, response) -> bytes | None:
        candidates = getattr(response, "candidates", None) or []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None) or []
            for part in parts:
                inline_data = getattr(part, "inline_data", None)
                if inline_data and getattr(inline_data, "data", None):
                    return inline_data.data
        return None
