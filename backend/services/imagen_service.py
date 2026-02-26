from __future__ import annotations

from pathlib import Path

from backend.domain.models import PromptBundle


class ImagenService:
    def __init__(self, api_key: str | None, model_name: str) -> None:
        # 외부 모델 호출(google-genai) 책임만 담당
        self.api_key = api_key
        self.model_name = model_name

    def edit_image(self, reference_paths: list[Path], prompt: PromptBundle) -> bytes:
        # 1) API 키 확인
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")

        try:
            # 2) 필요할 때만 라이브러리를 import (테스트/문서 작업 시 부담 감소)
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise RuntimeError("google-genai package is required. Install with: pip install google-genai") from exc

        # 3) reference 이미지들을 Imagen edit_image 형식으로 변환
        client = genai.Client(api_key=self.api_key)
        raw_refs = [
            types.RawReferenceImage(
                reference_id=index + 1,
                reference_image=types.Image.from_file(str(path)),
            )
            for index, path in enumerate(reference_paths)
        ]

        # 4) Imagen 편집 호출 (모든 기능이 결국 여기로 모인다)
        result = client.models.edit_image(
            model=self.model_name,
            prompt=prompt.positive,
            reference_images=raw_refs,
            config=types.EditImageConfig(
                number_of_images=1,
                output_mime_type="image/png",
                negative_prompt=prompt.negative,
            ),
        )

        # 5) 결과 이미지가 없으면 예외 처리
        if not getattr(result, "generated_images", None):
            raise RuntimeError("Imagen returned no generated images")

        # 6) 첫 번째 생성 결과의 바이트를 반환
        return result.generated_images[0].image.image_bytes
