"""
파일명: deps.py
작성자: JunBeul
설명: FastAPI 라우터에서 재사용할 의존성(기본 ImageGenerationPipeline)을 생성하고 캐시하는 함수를 제공한다.
상위 모듈: backend.api.routes_generation
하위 모듈: backend.services.pipelines
"""


from __future__ import annotations
from functools import lru_cache
from backend.services.pipelines import ImageGenerationPipeline


@lru_cache(maxsize=1)
def get_pipeline() -> ImageGenerationPipeline:
    # 요청마다 새로 만들지 않고, 같은 파이프라인 인스턴스를 재사용한다.
    return ImageGenerationPipeline.create_default()
