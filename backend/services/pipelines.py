"""
파일명: pipelines.py
작성자: JunBeul
설명: 입력 경로 검증, 프롬프트 생성, Gemini 모델 호출, 결과/메타데이터 저장을 순서대로 오케스트레이션하여 통합 GenerationResult를 반환하는 메인 파이프라인을 제공한다.
상위 모듈: backend.api.deps, backend.api.routes_generation, backend.cli
하위 모듈: backend.core.settings, backend.domain.enums, backend.domain.models, backend.services.gemini_image_service, backend.services.prompt_builder, backend.services.storage, backend.services.validators
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.core.settings import Settings, get_settings
from backend.domain.enums import TaskType
from backend.domain.models import (
    CosplayBasicRequest,
    CosplayWithMasterRequest,
    GenerationArtifact,
    GenerationResult,
    MasterImageRequest,
)

from .gemini_image_service import GeminiImageService
from .prompt_builder import PromptBuilder
from .storage import StorageManager
from .validators import validate_image_path


class ImageGenerationPipeline:
    def __init__(
        self,
        settings: Settings,
        prompt_builder: PromptBuilder,
        storage: StorageManager,
        gemini_image_service: GeminiImageService,
    ) -> None:
        self.settings = settings
        self.prompt_builder = prompt_builder
        self.storage = storage
        self.gemini_image_service = gemini_image_service

    @classmethod
    def create_default(cls) -> "ImageGenerationPipeline":
        settings = get_settings()
        return cls(
            settings=settings,
            prompt_builder=PromptBuilder(settings),
            storage=StorageManager(settings.outputs_dir),
            gemini_image_service=GeminiImageService(
                api_key=settings.gemini_api_key,
                model_name=settings.image_generation_model,
            ),
        )

    def generate_cosplay_basic(self, request: CosplayBasicRequest) -> GenerationResult:
        task = TaskType.COSPLAY_BASIC
        try:
            illustration = validate_image_path(request.illustration_path, "illustration_path")
            prompt_variables = {"REFERENCE_IMG": illustration.name}
            if request.prompt_variables:
                prompt_variables.update(request.prompt_variables)
            prompt = self.prompt_builder.build(
                mode_config_name="mode1_general_trans.json",
                variables=prompt_variables,
                user_custom_text=request.user_custom_text,
                vfx_options=request.vfx_options,
                vfx_params=request.vfx_params,
            )
            artifact = self._run_generation(
                task=task,
                reference_paths=[illustration],
                prompt=prompt,
                requested_output_filename=request.output_filename,
                dry_run=request.dry_run,
                extra_metadata={
                    "illustration_path": str(illustration),
                    "user_custom_text": request.user_custom_text,
                    "vfx_options": request.vfx_options,
                    "vfx_params": request.vfx_params,
                },
            )
            return self._to_result(task, artifact)
        except Exception as exc:
            return self._error_result(task, exc)

    def generate_cosplay_with_master(self, request: CosplayWithMasterRequest) -> GenerationResult:
        task = TaskType.COSPLAY_WITH_MASTER
        try:
            illustration = validate_image_path(request.illustration_path, "illustration_path")
            master = validate_image_path(request.master_image_path, "master_image_path")
            prompt_variables = {
                "REFERENCE_IMG": illustration.name,
                "MASTER_IMG": master.name,
            }
            if request.prompt_variables:
                prompt_variables.update(request.prompt_variables)
            prompt = self.prompt_builder.build(
                mode_config_name="mode2_face_consistency.json",
                variables=prompt_variables,
                user_custom_text=request.user_custom_text,
                vfx_options=request.vfx_options,
                vfx_params=request.vfx_params,
            )
            artifact = self._run_generation(
                task=task,
                reference_paths=[illustration, master],
                prompt=prompt,
                requested_output_filename=request.output_filename,
                dry_run=request.dry_run,
                extra_metadata={
                    "illustration_path": str(illustration),
                    "master_image_path": str(master),
                    "user_custom_text": request.user_custom_text,
                    "vfx_options": request.vfx_options,
                    "vfx_params": request.vfx_params,
                },
            )
            return self._to_result(task, artifact)
        except Exception as exc:
            return self._error_result(task, exc)

    def generate_master_image(self, request: MasterImageRequest) -> GenerationResult:
        task = TaskType.MASTER_IMAGE
        _ = request
        return self._error_result(task, NotImplementedError("master_image is not supported yet"))

    def _run_generation(
        self,
        task: TaskType,
        reference_paths: list[Path],
        prompt: Any,
        requested_output_filename: str | None,
        dry_run: bool,
        extra_metadata: dict[str, Any],
    ) -> GenerationArtifact:
        output_path = self.storage.build_output_path(task.value, requested_output_filename)
        metadata = {
            "task": task.value,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "model": self.settings.image_generation_model,
            "dry_run": dry_run,
            "reference_paths": [str(path) for path in reference_paths],
            "prompt_config": prompt.mode_config_name,
            "prompt": prompt.text,
            **extra_metadata,
        }

        if dry_run:
            metadata_path = self.storage.save_metadata(None, metadata)
            return GenerationArtifact(image_path=None, metadata_path=metadata_path, metadata=metadata)

        image_bytes, gemini_response_summary = self.gemini_image_service.generate_image(reference_paths, prompt)
        metadata["gemini_response_summary"] = gemini_response_summary
        image_path = self.storage.save_image_bytes(output_path, image_bytes)
        metadata_path = self.storage.save_metadata(image_path, metadata)
        return GenerationArtifact(image_path=image_path, metadata_path=metadata_path, metadata=metadata)

    def _to_result(self, task: TaskType, artifact: GenerationArtifact) -> GenerationResult:
        return GenerationResult(
            success=True,
            task=task,
            image_path=str(artifact.image_path) if artifact.image_path else None,
            metadata_path=str(artifact.metadata_path),
            prompt=artifact.metadata.get("prompt"),
            negative_prompt=artifact.metadata.get("negative_prompt"),
            error=None,
        )

    def _error_result(self, task: TaskType, exc: Exception) -> GenerationResult:
        return GenerationResult(
            success=False,
            task=task,
            image_path=None,
            metadata_path=None,
            prompt=None,
            negative_prompt=None,
            error=str(exc),
        )
