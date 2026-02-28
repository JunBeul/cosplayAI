"""
파일명: pipelines.py
작성자: JunBeul
설명: 입력 검증 -> 프롬프트 생성 -> contents 순서 조립 -> Gemini 호출 -> 저장 흐름을 담당한다.
상위 모듈: backend.api.deps, backend.api.routes_generation, backend.cli
하위 모듈: backend.core.settings, backend.services.*
"""


from __future__ import annotations

from datetime import datetime, timezone
import mimetypes
from pathlib import Path
from typing import Any, NoReturn

from backend.core.settings import Settings, get_settings
from backend.domain.enums import TaskType
from backend.domain.models import (
    CosplayBasicRequest,
    CosplayWithMasterRequest,
    GenerationArtifact,
    GenerationResult,
    MasterImageRequest,
    PromptBundle,
)

from .gemini_image_service import GeminiImageService
from .gemini_parameter_resolver import GeminiParameterContext, GeminiParameterResolver
from .prompt_builder import PromptBuilder
from .storage import StorageManager
from .validators import validate_image_path


ERROR_NAMESPACE = "IMAGE_GENERATION_PIPELINE"

MODE1_CONFIG_NAME = "mode1_general_trans.json"
MODE2_CONFIG_NAME = "mode2_face_consistency.json"
MODE3_CONFIG_NAME = "mode3_master_image.json"

DEFAULT_IMAGE_ROLE_INSTRUCTIONS: dict[str, str] = {
    MODE1_CONFIG_NAME: (
        "The following image is the reference image. "
        "Use it for costume, pose, composition, and overall scene mood."
    ),
    MODE2_CONFIG_NAME: (
        "Two images follow in this exact order: "
        "first is the master face image (identity priority), "
        "second is the reference image (costume, pose, composition, and scene mood)."
    ),
    MODE3_CONFIG_NAME: (
        "The following image is the person image. "
        "Use it to preserve facial identity and create a clean master portrait."
    ),
}


class ImageGenerationPipeline:
    """이미지 생성 파이프라인."""
    def __init__(
        self,
        settings: Settings,
        prompt_builder: PromptBuilder,
        storage: StorageManager,
        gemini_image_service: GeminiImageService,
        parameter_resolver: GeminiParameterResolver,
        image_role_instructions: dict[str, str] | None = None,
    ) -> None:
        """
        파이프라인 의존성을 주입하고 모드별 이미지 역할 문구를 초기화한다.
        Args:
            settings: Settings: 프로젝트 경로/모델 정보를 담은 설정 객체.
            prompt_builder: PromptBuilder: 모드별 최종 프롬프트를 조립하는 빌더.
            storage: StorageManager: 결과 이미지/메타데이터 저장 모듈.
            gemini_image_service: GeminiImageService: Gemini 호출 어댑터.
            parameter_resolver: GeminiParameterResolver: Gemini 호출 config 해석기.
            image_role_instructions: dict[str, str] | None: 기본 역할 문구를 덮어쓸 모드별 문구 맵.
        """
        self.settings = settings
        self.prompt_builder = prompt_builder
        self.storage = storage
        self.gemini_image_service = gemini_image_service
        self.parameter_resolver = parameter_resolver

        self.image_role_instructions = dict(DEFAULT_IMAGE_ROLE_INSTRUCTIONS)
        if image_role_instructions:
            self.image_role_instructions.update(image_role_instructions)

    @classmethod
    def create_default(cls) -> "ImageGenerationPipeline":
        """
        기본 설정 기반 파이프라인 인스턴스를 생성한다.
        Returns:
            ImageGenerationPipeline: 기본 의존성이 연결된 파이프라인.
        """
        settings = get_settings()
        return cls(
            settings=settings,
            prompt_builder=PromptBuilder(settings),
            storage=StorageManager(settings.outputs_dir),
            gemini_image_service=GeminiImageService(
                api_key=settings.gemini_api_key,
                model_name=settings.image_generation_model,
            ),
            parameter_resolver=GeminiParameterResolver(),
        )

    def set_image_role_instruction(self, mode_config_name: str, instruction: str) -> None:
        """
        런타임에 모드별 이미지 역할 문구를 교체한다.
        Args:
            mode_config_name: str: 대상 모드 설정 파일명.
            instruction: str: Gemini contents에 넣을 이미지 역할 설명 문구.
        """
        self.image_role_instructions[mode_config_name] = instruction

    def _raise_runtime_error(self, code: str, detail: str) -> NoReturn:
        """
        파이프라인 표준 형식의 RuntimeError를 발생시킨다.
        Args:
            code: str: 에러 코드 식별자.
            detail: str: 에러 상세 메시지.
        Raises:
            RuntimeError: 표준 포맷(`[{ERROR_NAMESPACE}:{code}] {detail}`)으로 발생한다.
        """
        raise RuntimeError(f"[{ERROR_NAMESPACE}:{code}] {detail}")

    # mode 1
    def generate_cosplay_basic(self, request: CosplayBasicRequest) -> GenerationResult:
        """
        모드1(일러스트 단일 입력) 이미지 생성을 수행한다.
        Args:
            request: CosplayBasicRequest: mode1 요청 객체.
        Returns:
            GenerationResult: 성공/실패 상태와 산출물 경로를 담은 결과 객체.
        """
        task = TaskType.COSPLAY_BASIC
        try:
            illustration = validate_image_path(request.illustration_path, "illustration_path")

            prompt = self.prompt_builder.build(
                mode_config_name=MODE1_CONFIG_NAME,
                variables=self._merge_prompt_variables(
                    request.prompt_variables,
                    {"REFERENCE_IMG": illustration.name},
                ),
                user_custom_text=request.user_custom_text,
                vfx_options=request.vfx_options,
                vfx_params=request.vfx_params,
            )

            artifact = self._run_generation(
                task=task,
                mode_config_name=MODE1_CONFIG_NAME,
                prompt=prompt,
                content_image_items=[("reference_image", illustration)],
                resolver_reference_paths=[illustration],
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

    # mode 2
    def generate_cosplay_with_master(self, request: CosplayWithMasterRequest) -> GenerationResult:
        """
        모드2(마스터 얼굴 + 레퍼런스) 이미지 생성을 수행한다.
        Args:
            request: CosplayWithMasterRequest: mode2 요청 객체.
        Returns:
            GenerationResult: 성공/실패 상태와 산출물 경로를 담은 결과 객체.
        """
        task = TaskType.COSPLAY_WITH_MASTER
        try:
            illustration = validate_image_path(request.illustration_path, "illustration_path")
            master = validate_image_path(request.master_image_path, "master_image_path")

            prompt = self.prompt_builder.build(
                mode_config_name=MODE2_CONFIG_NAME,
                variables=self._merge_prompt_variables(
                    request.prompt_variables,
                    {
                        "REFERENCE_IMG": illustration.name,
                        "MASTER_IMG": master.name,
                    },
                ),
                user_custom_text=request.user_custom_text,
                vfx_options=request.vfx_options,
                vfx_params=request.vfx_params,
            )

            artifact = self._run_generation(
                task=task,
                mode_config_name=MODE2_CONFIG_NAME,
                prompt=prompt,
                # 요구 순서: [텍스트, 역할 문구, 마스터 이미지, 레퍼런스 이미지]
                content_image_items=[
                    ("master_image", master),
                    ("reference_image", illustration),
                ],
                # image_config 해석은 마스터와 무관하게 레퍼런스 기준으로만 처리한다.
                resolver_reference_paths=[illustration],
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

    # mode 3
    def generate_master_image(self, request: MasterImageRequest) -> GenerationResult:
        """
        모드3(사람 이미지 -> 마스터 이미지) 생성을 수행한다.
        Args:
            request: MasterImageRequest: mode3 요청 객체.
        Returns:
            GenerationResult: 성공/실패 상태와 산출물 경로를 담은 결과 객체.
        """
        task = TaskType.MASTER_IMAGE
        try:
            person = validate_image_path(request.person_image_path, "person_image_path")

            prompt = self.prompt_builder.build(
                mode_config_name=MODE3_CONFIG_NAME,
                variables=self._merge_prompt_variables(
                    request.prompt_variables,
                    {"PERSON_IMG": person.name},
                ),
                user_custom_text=request.user_custom_text,
                vfx_options=request.vfx_options,
                vfx_params=request.vfx_params,
            )

            artifact = self._run_generation(
                task=task,
                mode_config_name=MODE3_CONFIG_NAME,
                prompt=prompt,
                # 요구 순서: [텍스트, 역할 문구, 사람 이미지]
                content_image_items=[("person_image", person)],
                resolver_reference_paths=[person],
                requested_output_filename=request.output_filename,
                dry_run=request.dry_run,
                extra_metadata={
                    "person_image_path": str(person),
                    "user_custom_text": request.user_custom_text,
                    "vfx_options": request.vfx_options,
                    "vfx_params": request.vfx_params,
                },
            )
            return self._to_result(task, artifact)
        except Exception as exc:
            return self._error_result(task, exc)

    def _merge_prompt_variables(
        self,
        request_variables: dict[str, str],
        base_variables: dict[str, str],
    ) -> dict[str, str]:
        """
        기본 변수 위에 요청 변수를 덮어써 최종 치환 변수 맵을 만든다.
        Args:
            request_variables: dict[str, str]: 사용자 입력 변수 맵.
            base_variables: dict[str, str]: 모드 필수 기본 변수 맵.
        Returns:
            dict[str, str]: PromptBuilder에 전달할 최종 변수 맵.
        """
        merged = dict(base_variables)
        if request_variables:
            merged.update(request_variables)
        return merged

    def _run_generation(
        self,
        task: TaskType,
        mode_config_name: str,
        prompt: PromptBundle,
        content_image_items: list[tuple[str, Path]],
        resolver_reference_paths: list[Path],
        requested_output_filename: str | None,
        dry_run: bool,
        extra_metadata: dict[str, Any],
    ) -> GenerationArtifact:
        """
        공통 생성 흐름(메타데이터 구성, resolver 적용, contents 조립, Gemini 호출, 저장)을 수행한다.
        Args:
            task: TaskType: 실행할 작업 타입.
            mode_config_name: str: 역할 문구 조회와 resolver에 사용할 모드명.
            prompt: PromptBundle: PromptBuilder가 조립한 최종 프롬프트.
            content_image_items: list[tuple[str, Path]]: contents 순서대로 투입할 이미지 라벨/경로 목록.
            resolver_reference_paths: list[Path]: image_config 해석 기준이 되는 레퍼런스 목록.
            requested_output_filename: str | None: 사용자 지정 출력 파일명.
            dry_run: bool: True면 모델 호출 없이 메타데이터만 저장한다.
            extra_metadata: dict[str, Any]: 요청별 추가 메타데이터.
        Returns:
            GenerationArtifact: 이미지/메타데이터 저장 결과.
        Raises:
            RuntimeError: 역할 문구 누락, SDK import 실패, 이미지 파트 생성 실패 시 발생한다.
        """
        output_path = self.storage.build_output_path(task.value, requested_output_filename)
        content_order = ["text", "image_role_instruction", *[label for label, _ in content_image_items]]

        metadata: dict[str, Any] = {
            "task": task.value,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "model": self.settings.image_generation_model,
            "dry_run": dry_run,
            "prompt_config": prompt.mode_config_name,
            "prompt": prompt.text,
            "content_order": content_order,
            **extra_metadata,
        }

        if dry_run:
            metadata_path = self.storage.save_metadata(None, metadata)
            return GenerationArtifact(image_path=None, metadata_path=metadata_path, metadata=metadata)

        resolved = self.parameter_resolver.resolve(
            GeminiParameterContext(
                mode_config_name=mode_config_name,
                reference_paths=resolver_reference_paths,
            )
        )

        role_instruction = self._get_image_role_instruction(mode_config_name)
        contents = self._build_contents(
            prompt_text=prompt.text,
            role_instruction=role_instruction,
            content_image_items=content_image_items,
        )

        image_bytes, gemini_response_summary = self.gemini_image_service.generate_image(
            contents=contents,
            config=resolved.generate_content_config,
        )

        metadata["image_role_instruction"] = role_instruction
        metadata["resolved_image_config"] = resolved.resolved_image_config
        metadata["resolved_safety_settings"] = resolved.resolved_safety_settings
        metadata["gemini_response_summary"] = gemini_response_summary

        image_path = self.storage.save_image_bytes(output_path, image_bytes)
        metadata_path = self.storage.save_metadata(image_path, metadata)
        return GenerationArtifact(image_path=image_path, metadata_path=metadata_path, metadata=metadata)

    def _get_image_role_instruction(self, mode_config_name: str) -> str:
        """
        모드별 이미지 역할 설명 문구를 가져온다.
        Args:
            mode_config_name: str: 조회 대상 모드 설정 파일명.
        Returns:
            str: 해당 모드에서 사용할 역할 문구.
        Raises:
            RuntimeError: 문구가 없거나 비어 있으면 발생한다.
        """
        instruction = str(self.image_role_instructions.get(mode_config_name, "")).strip()
        if not instruction:
            self._raise_runtime_error(
                code="E_MISSING_IMAGE_ROLE_INSTRUCTION",
                detail=f"이미지 역할 설명 문구가 없습니다. mode_config_name='{mode_config_name}'",
            )
        return instruction

    def _build_contents(
        self,
        prompt_text: str,
        role_instruction: str,
        content_image_items: list[tuple[str, Path]],
    ) -> list[object]:
        """
        Gemini 호출용 contents 배열을 최종 순서로 구성한다.
        Args:
            prompt_text: str: 최종 텍스트 프롬프트.
            role_instruction: str: 이미지 역할 설명 문구.
            content_image_items: list[tuple[str, Path]]: 이미지 라벨/경로 목록.
        Returns:
            list[object]: `[text, role_instruction, image_part...]` 순서의 멀티모달 입력 배열.
        Raises:
            RuntimeError: SDK import 실패 시 발생한다.
        """
        try:
            from google.genai import types
        except ImportError:
            self._raise_runtime_error(
                code="E_SDK_IMPORT_FAILED",
                detail="google-genai package is required. Install with: pip install google-genai",
            )

        contents: list[object] = [prompt_text, role_instruction]
        for _label, image_path in content_image_items:
            contents.append(self._image_part_from_path(image_path, types))
        return contents

    def _image_part_from_path(self, path: Path, types_module: object) -> object:
        """
        이미지 파일을 Gemini SDK Part 객체로 변환한다.
        Args:
            path: Path: 이미지 파일 경로.
            types_module: object: `google.genai.types` 모듈 객체.
        Returns:
            object: `types.Part.from_bytes`로 생성한 이미지 Part.
        Raises:
            RuntimeError: 파일 읽기 실패 또는 Part 생성 실패 시 발생한다.
        """
        mime_type, _ = mimetypes.guess_type(str(path))
        if not mime_type:
            mime_type = "image/png"

        try:
            part_factory = getattr(types_module, "Part")
            from_bytes = getattr(part_factory, "from_bytes")
            return from_bytes(data=path.read_bytes(), mime_type=mime_type)
        except OSError as exc:
            self._raise_runtime_error(
                code="E_IMAGE_READ_FAILED",
                detail=f"이미지 파일을 읽을 수 없습니다: {path} ({str(exc)})",
            )
        except Exception as exc:
            self._raise_runtime_error(
                code="E_IMAGE_PART_BUILD_FAILED",
                detail=f"Gemini image part 생성 실패: {path} ({str(exc)})",
            )

    def _to_result(self, task: TaskType, artifact: GenerationArtifact) -> GenerationResult:
        """
        내부 산출물을 성공 응답 모델로 변환한다.
        Args:
            task: TaskType: 실행한 작업 타입.
            artifact: GenerationArtifact: 생성 단계 산출물.
        Returns:
            GenerationResult: 성공 응답 객체.
        """
        return GenerationResult(
            success=True,
            task=task,
            image_path=str(artifact.image_path) if artifact.image_path else None,
            metadata_path=str(artifact.metadata_path),
            prompt=artifact.metadata.get("prompt"),
            negative_prompt=None,
            error=None,
        )

    def _error_result(self, task: TaskType, exc: Exception) -> GenerationResult:
        """
        예외를 실패 응답 모델로 변환한다.
        Args:
            task: TaskType: 실패한 작업 타입.
            exc: Exception: 발생한 예외 객체.
        Returns:
            GenerationResult: 실패 응답 객체.
        """
        return GenerationResult(
            success=False,
            task=task,
            image_path=None,
            metadata_path=None,
            prompt=None,
            negative_prompt=None,
            error=str(exc),
        )
