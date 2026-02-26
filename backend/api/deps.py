from __future__ import annotations

from functools import lru_cache

from backend.services.pipelines import ImageGenerationPipeline


@lru_cache(maxsize=1)
def get_pipeline() -> ImageGenerationPipeline:
    # 요청마다 새로 만들지 않고, 같은 파이프라인 인스턴스를 재사용한다.
    return ImageGenerationPipeline.create_default()
