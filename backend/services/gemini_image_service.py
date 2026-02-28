"""
파일명: gemini_image_service.py
작성자: Codex
설명: Gemini 호출 실행 책임만 담당한다.
상위 모듈: backend.services.pipelines
하위 모듈: backend.services.gemini_response_observer
"""


from __future__ import annotations
from typing import NoReturn
from .gemini_response_observer import GeminiResponseObserver, ResponseSummary


ERROR_NAMESPACE = "GEMINI_IMAGE_SERVICE"


class GeminiImageService:
    """Gemini API 호출 어댑터."""

    def __init__(
        self,
        api_key: str | None,
        model_name: str,
        observer: GeminiResponseObserver | None = None,
    ) -> None:
        """
        Gemini 호출에 필요한 고정값을 초기화한다.
        Args:
            api_key: str | None: GEMINI_API_KEY 값.
            model_name: str: 호출할 Gemini 모델 이름.
            observer: GeminiResponseObserver | None: 응답 파싱/진단 전담 객체.
        """
        self.api_key = api_key
        self.model_name = model_name
        self.observer = observer or GeminiResponseObserver()

    def _raise_runtime_error(self, code: str, detail: str) -> NoReturn:
        """
        서비스 표준 형식의 RuntimeError를 발생시킨다.
        Args:
            code: str: 에러 코드 식별자.
            detail: str: 에러 상세 메시지.
        Raises:
            RuntimeError: 표준화된 메시지 포맷으로 발생한다.
        """
        raise RuntimeError(f"[{ERROR_NAMESPACE}:{code}] {detail}")

    def generate_image(self, contents: list[object], config: object) -> tuple[bytes, ResponseSummary]:
        """
        완성된 입력(contents/config)으로 Gemini를 호출하고 이미지 바이트를 반환한다.
        Args:
            contents: list[object]: 텍스트/이미지 Part가 조합된 멀티모달 입력 목록.
            config: object: google.genai.types.GenerateContentConfig 호환 객체.
        Returns:
            tuple[bytes, ResponseSummary]:
                - bytes: 응답에서 추출한 첫 번째 inline image 바이트.
                - ResponseSummary: 응답 관측성 요약 정보.
        Raises:
            RuntimeError: API 키 누락, SDK 미설치, inline 이미지 부재 시 발생한다.
        """
        if not self.api_key:
            self._raise_runtime_error(
                code="E_API_KEY_MISSING",
                detail="GEMINI_API_KEY is not set",
            )

        try:
            from google import genai
        except ImportError:
            self._raise_runtime_error(
                code="E_SDK_IMPORT_FAILED",
                detail="google-genai package is required. Install with: pip install google-genai",
            )

        client = genai.Client(api_key=self.api_key)
        try:
            response = client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config,
            )
        except Exception as exc:
            self._raise_runtime_error(
                code="E_GENERATE_CONTENT_FAILED",
                detail=f"Gemini generate_content failed: {str(exc)}",
            )

        response_summary = self.observer.build_response_summary(response)
        image_bytes = self.observer.extract_first_image_bytes(response)
        if image_bytes is None:
            self._raise_runtime_error(
                code="E_NO_INLINE_IMAGE_DATA",
                detail=self.observer.build_no_inline_image_error(response),
            )

        return image_bytes, response_summary
