from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.domain.models import (
    CosplayBasicRequest,
    CosplayWithMasterRequest,
    GenerationResult,
    MasterImageRequest,
)
from backend.services.pipelines import ImageGenerationPipeline

from .deps import get_pipeline
from .schemas import HealthResponseSchema


router = APIRouter(prefix="/api/v1", tags=["generation"])


@router.get("/health", response_model=HealthResponseSchema)
def health() -> HealthResponseSchema:
    # 서버가 떠 있는지만 확인하는 엔드포인트
    return HealthResponseSchema(status="ok")


@router.post("/generation/cosplay/basic", response_model=GenerationResult)
def generate_cosplay_basic(
    payload: CosplayBasicRequest,
    pipeline: ImageGenerationPipeline = Depends(get_pipeline),
) -> GenerationResult:
    # API 요청 모델과 파이프라인 요청 모델을 공용으로 사용하여 중복을 줄인다.
    return pipeline.generate_cosplay_basic(payload)


@router.post("/generation/cosplay/with-master", response_model=GenerationResult)
def generate_cosplay_with_master(
    payload: CosplayWithMasterRequest,
    pipeline: ImageGenerationPipeline = Depends(get_pipeline),
) -> GenerationResult:
    # 기능 2: 일러스트 + 마스터 이미지 기반 생성
    return pipeline.generate_cosplay_with_master(payload)


@router.post("/generation/master-image", response_model=GenerationResult)
def generate_master_image(
    payload: MasterImageRequest,
    pipeline: ImageGenerationPipeline = Depends(get_pipeline),
) -> GenerationResult:
    # 기능 3: 인물 사진으로 마스터 이미지 생성
    return pipeline.generate_master_image(payload)
