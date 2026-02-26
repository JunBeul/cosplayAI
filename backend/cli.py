from __future__ import annotations

import argparse
import json

from backend.domain.models import CosplayBasicRequest, CosplayWithMasterRequest, MasterImageRequest
from backend.services.pipelines import ImageGenerationPipeline


def build_parser() -> argparse.ArgumentParser:
    # 로컬에서 빠르게 기능별 파이프라인을 실행해보기 위한 CLI 인터페이스
    parser = argparse.ArgumentParser(description="CosplayAI local CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    basic = subparsers.add_parser("cosplay-basic", help="Illustration -> cosplay image")
    basic.add_argument("--illustration-path", required=True)
    basic.add_argument("--output-filename")
    basic.add_argument("--dry-run", action="store_true")

    with_master = subparsers.add_parser("cosplay-with-master", help="Illustration + master -> cosplay image")
    with_master.add_argument("--illustration-path", required=True)
    with_master.add_argument("--master-image-path", required=True)
    with_master.add_argument("--output-filename")
    with_master.add_argument("--dry-run", action="store_true")

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
    if args.command == "cosplay-basic":
        result = pipeline.generate_cosplay_basic(
            CosplayBasicRequest(
                illustration_path=args.illustration_path,
                output_filename=args.output_filename,
                dry_run=args.dry_run,
            )
        )
    elif args.command == "cosplay-with-master":
        result = pipeline.generate_cosplay_with_master(
            CosplayWithMasterRequest(
                illustration_path=args.illustration_path,
                master_image_path=args.master_image_path,
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
