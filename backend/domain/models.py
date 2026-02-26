"""
파일명: models.py
작성자: JunBeul
설명: CLI, API, 파이프라인에서 공유하는 Pydantic 요청/응답 모델과 프롬프트 번들·산출물 정보 구조를 정의한다.
상위 모듈: backend.api.routes_generation, backend.cli, backend.services.gemini_image_service, backend.services.pipelines, backend.services.prompt_builder
하위 모듈: backend.domain.enums
"""


from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field
from .enums import TaskType


@dataclass(frozen=True)
class PromptBundle:
    # 최종 텍스트 프롬프트 + 어떤 모드 설정을 썼는지
    # (negative는 별도 분리하지 않고 text 내부에 포함)
    text: str
    mode_config_name: str


class BaseGenerationRequest(BaseModel):
    # 기능 1/2/3 요청에서 공통으로 쓰는 옵션
    prompt_variables: dict[str, str] = Field(default_factory=dict)
    # 유저 커스텀 텍스트 (선택사항): Crucial Constraints - Additions에 삽입
    user_custom_text: str | None = None
    # 선택형 VFX 옵션 (예: animal_features, halo_vfx, color_palette)
    vfx_options: list[str] = Field(default_factory=list)
    # VFX 옵션에 필요한 추가 값 (예: HAIR_COLOR, EYE_COLOR)
    vfx_params: dict[str, str] = Field(default_factory=dict)
    output_filename: str | None = None
    dry_run: bool = False


class CosplayBasicRequest(BaseGenerationRequest):
    # 기능 1: 일러스트 -> 코스프레
    illustration_path: str = ""


class CosplayWithMasterRequest(BaseGenerationRequest):
    # 기능 2: 일러스트 + 마스터 이미지 -> 얼굴 일관성 있는 코스프레
    illustration_path: str = ""
    master_image_path: str = ""


class MasterImageRequest(BaseGenerationRequest):
    # 기능 3: 인물 사진 -> 마스터 이미지
    person_image_path: str = ""


class GenerationResult(BaseModel):
    # 외부(API/CLI)로 반환할 최종 결과
    success: bool
    task: TaskType
    image_path: str | None
    metadata_path: str | None
    prompt: str | None
    negative_prompt: str | None
    error: str | None = None


@dataclass
class GenerationArtifact:
    # 내부 저장 단계에서 사용하는 산출물(파일 경로 + 메타데이터)
    image_path: Path | None
    metadata_path: Path
    metadata: dict[str, Any]
