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
        # 파이프라인은 "조립자" 역할만 한다.
        # 실제 작업은 prompt/storage/모델 호출 서비스에 위임한다.
        self.settings = settings
        self.prompt_builder = prompt_builder
        self.storage = storage
        self.gemini_image_service = gemini_image_service

    @classmethod
    def create_default(cls) -> "ImageGenerationPipeline":
        # 앱/CLI에서 바로 쓰기 위한 기본 조합 팩토리
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
        # 기능 1 흐름:
        # 입력 검증 -> 프롬프트 생성 -> 이미지 생성/저장 -> 결과 반환
        task = TaskType.COSPLAY_BASIC
        try:
            illustration = validate_image_path(request.illustration_path, "illustration_path")
            prompt = self.prompt_builder.build_for_basic(
                illustration_filename=illustration.name,
                extra_variables=request.prompt_variables,
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
        # 기능 2 흐름:
        # 일러스트/마스터 이미지 둘 다 검증 -> 얼굴 일관성 프롬프트 -> 생성
        task = TaskType.COSPLAY_WITH_MASTER
        try:
            illustration = validate_image_path(request.illustration_path, "illustration_path")
            master = validate_image_path(request.master_image_path, "master_image_path")
            prompt = self.prompt_builder.build_for_with_master(
                illustration_filename=illustration.name,
                master_filename=master.name,
                extra_variables=request.prompt_variables,
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
        # 기능 3 흐름 (보류):
        # mode3 프롬프트 구조를 대폭 개편할 예정이므로 현재는 스텁 함수만 유지한다.
        task = TaskType.MASTER_IMAGE
        try:
            person = validate_image_path(request.person_image_path, "person_image_path")
            prompt = self.prompt_builder.build_for_master_image(
                person_filename=person.name,
                extra_variables=request.prompt_variables,
            )
            artifact = self._run_generation(
                task=task,
                reference_paths=[person],
                prompt=prompt,
                requested_output_filename=request.output_filename,
                dry_run=request.dry_run,
                extra_metadata={"person_image_path": str(person)},
            )
            return self._to_result(task, artifact)
        except Exception as exc:
            return self._error_result(task, exc)

    def _run_generation(
        self,
        task: TaskType,
        reference_paths: list[Path],
        prompt: Any,
        requested_output_filename: str | None,
        dry_run: bool,
        extra_metadata: dict[str, Any],
    ) -> GenerationArtifact:
        # 공통 실행부:
        # 1) 결과 파일명 결정
        # 2) 메타데이터 구성
        # 3) dry_run이면 메타데이터만 저장
        # 4) 아니면 모델 호출 -> 이미지 저장 -> 메타데이터 저장
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

        # 실제 모델 호출은 서비스 계층에 위임
        image_bytes, gemini_response_summary = self.gemini_image_service.generate_image(reference_paths, prompt)
        metadata["gemini_response_summary"] = gemini_response_summary
        image_path = self.storage.save_image_bytes(output_path, image_bytes)
        metadata_path = self.storage.save_metadata(image_path, metadata)
        return GenerationArtifact(image_path=image_path, metadata_path=metadata_path, metadata=metadata)

    def _to_result(self, task: TaskType, artifact: GenerationArtifact) -> GenerationResult:
        # 내부 산출물 객체를 외부 응답용 형태로 변환
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
        # 예외를 삼켜서(앱/CLI가 처리하기 쉽게) 표준 실패 응답으로 바꾼다.
        return GenerationResult(
            success=False,
            task=task,
            image_path=None,
            metadata_path=None,
            prompt=None,
            negative_prompt=None,
            error=str(exc),
        )
