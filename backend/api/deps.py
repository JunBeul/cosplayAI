"""
파일명: deps.py
작성자: JunBeul
설명: FastAPI 라우터 의존성(파이프라인 생성, 사용자 API 키 검증)을 제공한다.
상위 모듈: backend.api.routes_generation
하위 모듈: backend.services.pipelines, backend.core.settings, backend.services.gemini_image_service
"""


from __future__ import annotations
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from backend.core.settings import get_settings
from backend.services.gemini_image_service import GeminiImageService
from backend.services.pipelines import ImageGenerationPipeline

USER_API_KEY_HEADER = "X-Gemini-Api-Key"

@lru_cache(maxsize=1)
def get_api_key_validator() -> GeminiImageService:
    """
    사용자 키 유효성 검사 전용 Gemini 서비스 인스턴스를 생성한다.
    Returns:
        GeminiImageService: 키 검증/모델 호출용 공용 서비스 객체.
    """
    settings = get_settings()
    return GeminiImageService(
        api_key=settings.gemini_api_key,
        model_name=settings.image_generation_model,
    )


@lru_cache(maxsize=32)
def get_pipeline_by_api_key(api_key: str) -> ImageGenerationPipeline:
    """
    사용자 API 키 단위로 파이프라인을 캐시한다.
    Args:
        api_key: str: 요청 헤더에서 전달받은 Gemini API 키.
    Returns:
        ImageGenerationPipeline: 해당 키를 사용하는 생성 파이프라인.
    """
    settings = get_settings()
    pipeline = ImageGenerationPipeline.create_default()
    pipeline.gemini_image_service = GeminiImageService(
        api_key=api_key,
        model_name=settings.image_generation_model,
    )
    return pipeline


def require_user_api_key(
    x_gemini_api_key: Annotated[str | None, Header(alias=USER_API_KEY_HEADER)] = None,
) -> str:
    """
    요청 헤더의 Gemini API 키를 필수로 받고 유효성을 검사한다.
    Args:
        x_gemini_api_key: str | None: `X-Gemini-Api-Key` 헤더 값.
    Returns:
        str: 검증을 통과한 API 키.
    Raises:
        HTTPException: 키 누락/검증 실패 시 4xx 에러를 반환한다.
    """
    api_key = str(x_gemini_api_key or "").strip()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                f"{USER_API_KEY_HEADER} header is required. "
                "사용자 본인 Gemini API 키를 헤더에 넣어주세요."
            ),
        )

    validator = get_api_key_validator()
    is_valid, reason = validator.validate_api_key(api_key)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Invalid Gemini API key: {reason}",
        )

    return api_key


def get_pipeline(api_key: Annotated[str, Depends(require_user_api_key)]) -> ImageGenerationPipeline:
    """
    검증된 사용자 API 키 기반 파이프라인 의존성을 반환한다.
    Args:
        api_key: str: `require_user_api_key`를 통과한 Gemini 키.
    Returns:
        ImageGenerationPipeline: 사용자 키가 주입된 파이프라인.
    """
    return get_pipeline_by_api_key(api_key)
