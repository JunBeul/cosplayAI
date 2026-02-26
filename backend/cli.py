from __future__ import annotations

import argparse
import json

from backend.domain.models import CosplayBasicRequest, CosplayWithMasterRequest, MasterImageRequest
from backend.services.pipelines import ImageGenerationPipeline


def _add_vfx_args(parser: argparse.ArgumentParser) -> None:
    # CLI에서 선택형 VFX 옵션을 검증
    parser.add_argument("--animal-features", action="store_true", help="Enable animal feature VFX prompt")
    parser.add_argument("--halo-vfx", action="store_true", help="Enable halo VFX prompt")
    parser.add_argument("--hair-color", help="Value for [HAIR_COLOR] when using color_palette VFX")
    parser.add_argument("--eye-color", help="Value for [EYE_COLOR] when using color_palette VFX")


def _build_vfx_payload(args: argparse.Namespace) -> tuple[list[str], dict[str, str]]:
    vfx_options: list[str] = []
    vfx_params: dict[str, str] = {}

    if getattr(args, "animal_features", False):
        vfx_options.append("animal_features")
    if getattr(args, "halo_vfx", False):
        vfx_options.append("halo_vfx")

    hair_color = getattr(args, "hair_color", None)
    eye_color = getattr(args, "eye_color", None)
    if hair_color or eye_color:
        if not (hair_color and eye_color):
            raise ValueError("--hair-color and --eye-color must be provided together")
        vfx_options.append("color_palette")
        vfx_params["HAIR_COLOR"] = hair_color
        vfx_params["EYE_COLOR"] = eye_color

    return vfx_options, vfx_params


def build_parser() -> argparse.ArgumentParser:
    # 로컬에서 빠르게 기능별 파이프라인을 실행해보기 위한 CLI 인터페이스
    parser = argparse.ArgumentParser(description="CosplayAI local CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    basic = subparsers.add_parser("cosplay-basic", help="Illustration -> cosplay image")
    basic.add_argument("--illustration-path", required=True)
    basic.add_argument("--output-filename")
    basic.add_argument("--dry-run", action="store_true")
    _add_vfx_args(basic)

    with_master = subparsers.add_parser("cosplay-with-master", help="Illustration + master -> cosplay image")
    with_master.add_argument("--illustration-path", required=True)
    with_master.add_argument("--master-image-path", required=True)
    with_master.add_argument("--output-filename")
    with_master.add_argument("--dry-run", action="store_true")
    _add_vfx_args(with_master)

    master = subparsers.add_parser("master-image", help="Person photo -> master image")
    master.add_argument("--person-image-path", required=True)
    master.add_argument("--output-filename")
    master.add_argument("--dry-run", action="store_true")

    return parser


def main() -> int:
    # 1) 명령행 인자 파싱
    parser = build_parser()
    args = parser.parse_args()

    # 2) 기본 설정/서비스를 묶은 파이프라인 생성
    pipeline = ImageGenerationPipeline.create_default()

    # 3) 명령어 종류에 따라 기능 1/2/3 중 하나를 실행
    try:
        vfx_options, vfx_params = _build_vfx_payload(args)
    except ValueError as exc:
        parser.error(str(exc))

    if args.command == "cosplay-basic":
        result = pipeline.generate_cosplay_basic(
            CosplayBasicRequest(
                illustration_path=args.illustration_path,
                vfx_options=vfx_options,
                vfx_params=vfx_params,
                output_filename=args.output_filename,
                dry_run=args.dry_run,
            )
        )
    elif args.command == "cosplay-with-master":
        result = pipeline.generate_cosplay_with_master(
            CosplayWithMasterRequest(
                illustration_path=args.illustration_path,
                master_image_path=args.master_image_path,
                vfx_options=vfx_options,
                vfx_params=vfx_params,
                output_filename=args.output_filename,
                dry_run=args.dry_run,
            )
        )
    else:
        result = pipeline.generate_master_image(
            MasterImageRequest(
                person_image_path=args.person_image_path,
                output_filename=args.output_filename,
                dry_run=args.dry_run,
            )
        )

    # 4) 사람이 보기 쉬운 JSON으로 결과 출력 (성공/실패, 파일 경로)
    print(
        json.dumps(
            {
                "success": result.success,
                "task": result.task.value,
                "image_path": result.image_path,
                "metadata_path": result.metadata_path,
                "error": result.error,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if result.success else 1


if __name__ == "__main__":
    # 스크립트 직접 실행 시 종료 코드를 반환한다.
    raise SystemExit(main())
