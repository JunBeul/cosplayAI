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
from typing import Any
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

    def generate_image(self, reference_paths: list[Path], prompt: PromptBundle) -> tuple[bytes, dict[str, Any]]:
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
        contents: list[object] = [prompt.text]
        # prompt_builder가 만들어준 최종 포맷 텍스트를 그대로 전달한다.
        contents.extend(self._build_reference_contents(reference_paths, types))

        # 5) Gemini 2.5 Flash Image 생성 호출
        result = client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=1.0,
                responseModalities=["IMAGE"],
                safetySettings=[
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE,
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE,
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE,
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE,
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE,
                    ),
                ],
            ),
        )

        # 6) 응답에서 첫 번째 이미지 파트 추출
        response_summary = self._build_response_summary(result)
        image_bytes = self._extract_first_image_bytes(result)
        if image_bytes is None:
            raise RuntimeError(self._build_no_inline_image_error(result))

        return image_bytes, response_summary

    def _image_part_from_path(self, path: Path, types_module):
        mime_type, _ = mimetypes.guess_type(str(path))
        if not mime_type:
            mime_type = "image/png"

        image_bytes = path.read_bytes()
        return types_module.Part.from_bytes(data=image_bytes, mime_type=mime_type)

    def _build_reference_contents(self, reference_paths: list[Path], types_module) -> list[object]:
        if len(reference_paths) == 2:
            illustration, master = reference_paths
            return [
                (
                    "Image 1 is the master face reference (identity priority). "
                    "Image 2 is the illustration reference for costume, pose, composition, and scene mood."
                ),
                (
                    "Master face reference (identity priority). Use this image for facial identity, "
                    "facial structure, eye makeup, and fine face details. If there is any conflict, "
                    "prioritize this image for identity."
                ),
                self._image_part_from_path(master, types_module),
                (
                    "Illustration reference. Use this image for costume, hairstyle, pose, composition, "
                    "camera angle, and scene mood. Do not copy, crop, trace, or reproduce the reference "
                    "image pixels."
                ),
                self._image_part_from_path(illustration, types_module),
            ]

        items: list[object] = []
        if len(reference_paths) == 1:
            items.append("A reference image is provided. Use it faithfully according to the prompt.")
        items.extend(self._image_part_from_path(path, types_module) for path in reference_paths)
        return items
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

    def _build_no_inline_image_error(self, response) -> str:
        base = "Gemini image response returned no inline image data"
        details: list[str] = []

        prompt_feedback = getattr(response, "prompt_feedback", None)
        if prompt_feedback is not None:
            block_reason = getattr(prompt_feedback, "block_reason", None)
            block_reason_message = getattr(prompt_feedback, "block_reason_message", None)
            if block_reason:
                details.append(f"prompt_block_reason={block_reason}")
            if block_reason_message:
                details.append(f"prompt_block_message={self._truncate_text(str(block_reason_message))}")
            prompt_safety_ratings = self._serialize_safety_ratings(getattr(prompt_feedback, "safety_ratings", None))
            if prompt_safety_ratings:
                details.append(f"prompt_safety_ratings={prompt_safety_ratings}")

        candidates = getattr(response, "candidates", None) or []
        details.append(f"candidates={len(candidates)}")

        for idx, candidate in enumerate(candidates, start=1):
            summary_parts: list[str] = [f"candidate{idx}"]
            finish_reason = getattr(candidate, "finish_reason", None)
            if finish_reason:
                summary_parts.append(f"finish_reason={finish_reason}")
            candidate_safety_ratings = self._serialize_safety_ratings(getattr(candidate, "safety_ratings", None))
            if candidate_safety_ratings:
                summary_parts.append(f"safety_ratings={candidate_safety_ratings}")

            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None) or []
            text_chunks: list[str] = []
            for part in parts:
                text = getattr(part, "text", None)
                if text:
                    text_chunks.append(str(text))
            if text_chunks:
                summary_parts.append(f"text={self._truncate_text(' '.join(text_chunks))}")

            details.append(", ".join(summary_parts))

        return f"{base}. " + " | ".join(details)

    def _truncate_text(self, text: str, limit: int = 500) -> str:
        compact = " ".join(text.split())
        if len(compact) <= limit:
            return compact
        return compact[: limit - 3] + "..."

    def _build_response_summary(self, response) -> dict[str, Any]:
        summary: dict[str, Any] = {}

        prompt_feedback = getattr(response, "prompt_feedback", None)
        if prompt_feedback is not None:
            prompt_feedback_summary: dict[str, Any] = {}
            block_reason = getattr(prompt_feedback, "block_reason", None)
            block_reason_message = getattr(prompt_feedback, "block_reason_message", None)
            if block_reason:
                prompt_feedback_summary["block_reason"] = str(block_reason)
            if block_reason_message:
                prompt_feedback_summary["block_reason_message"] = self._truncate_text(str(block_reason_message))

            prompt_safety_ratings = self._serialize_safety_ratings(getattr(prompt_feedback, "safety_ratings", None))
            if prompt_safety_ratings:
                prompt_feedback_summary["safety_ratings"] = prompt_safety_ratings

            if prompt_feedback_summary:
                summary["prompt_feedback"] = prompt_feedback_summary

        candidates = getattr(response, "candidates", None) or []
        summary["candidate_count"] = len(candidates)
        summary["candidates"] = []
        for candidate in candidates:
            candidate_summary: dict[str, Any] = {}
            finish_reason = getattr(candidate, "finish_reason", None)
            if finish_reason:
                candidate_summary["finish_reason"] = str(finish_reason)

            candidate_safety_ratings = self._serialize_safety_ratings(getattr(candidate, "safety_ratings", None))
            if candidate_safety_ratings:
                candidate_summary["safety_ratings"] = candidate_safety_ratings

            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None) or []
            candidate_summary["has_inline_image"] = any(
                getattr(getattr(part, "inline_data", None), "data", None) for part in parts
            )
            text_chunks = [str(getattr(part, "text")) for part in parts if getattr(part, "text", None)]
            if text_chunks:
                candidate_summary["text"] = self._truncate_text(" ".join(text_chunks))

            summary["candidates"].append(candidate_summary)

        return summary

    def _serialize_safety_ratings(self, ratings) -> list[dict[str, str]]:
        items = ratings or []
        serialized: list[dict[str, str]] = []
        for rating in items:
            row = {
                "category": str(getattr(rating, "category", "")),
                "probability": str(getattr(rating, "probability", "")),
            }
            blocked = getattr(rating, "blocked", None)
            if blocked is not None:
                row["blocked"] = str(blocked)
            serialized.append(row)
        return serialized
