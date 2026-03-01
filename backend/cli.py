"""
파일명: cli.py
작성자: JunBeul
설명: 로컬 실행용 CLI 진입점으로 명령/옵션을 파싱하고 VFX 입력 조합을 검증한 뒤 생성 파이프라인을 실행해 JSON 결과를 출력한다.
상위 모듈: 없음
하위 모듈: backend.domain.models, backend.services.pipelines
"""


from __future__ import annotations
import argparse
import json
from pathlib import Path
from backend.domain.models import CosplayBasicRequest, CosplayWithMasterRequest, MasterImageRequest
from backend.services.pipelines import ImageGenerationPipeline


PROPS_CATALOG_PATH = Path(__file__).resolve().parents[1] / "configs" / "props_catalog.json"


def _to_catalog_map(raw: object, key_name: str) -> dict[str, str]:
    # 카탈로그 섹션을 key->label 맵으로 정규화
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid props catalog: '{key_name}' must be an object")

    normalized: dict[str, str] = {}
    for key, label in raw.items():
        key_text = str(key).strip().lower()
        label_text = str(label).strip()
        if not key_text or not label_text:
            continue
        normalized[key_text] = label_text
    return normalized


def _load_props_catalog() -> tuple[dict[str, str], dict[str, str]]:
    # props 카탈로그를 로드하고 combat/wig 섹션을 반환
    try:
        with PROPS_CATALOG_PATH.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise ValueError(f"Props catalog not found: {PROPS_CATALOG_PATH}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in props catalog: {PROPS_CATALOG_PATH}") from exc

    if not isinstance(data, dict):
        raise ValueError("Invalid props catalog: root must be an object")

    combat_catalog = _to_catalog_map(data.get("combat_props", {}), "combat_props")
    wig_catalog = _to_catalog_map(data.get("wig_props", {}), "wig_props")
    return combat_catalog, wig_catalog


def _dedupe_keep_order(values: list[str] | None) -> list[str]:
    # 중복 제거(순서 유지)
    unique: list[str] = []
    seen: set[str] = set()
    for raw in values or []:
        key = str(raw).strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(key)
    return unique


def _resolve_selected_labels(selected_keys: list[str], catalog: dict[str, str], option_name: str) -> str:
    # 선택된 key를 카탈로그 label 문자열로 변환
    invalid = [key for key in selected_keys if key not in catalog]
    if invalid:
        allowed = ", ".join(sorted(catalog))
        invalid_text = ", ".join(invalid)
        raise ValueError(f"Unsupported {option_name}: {invalid_text}. Allowed: {allowed}")

    labels = [catalog[key] for key in selected_keys]
    return ", ".join(labels)


def _add_vfx_args(parser: argparse.ArgumentParser) -> None:
    # CLI에서 선택형 VFX 옵션을 검증한다
    parser.add_argument("--user-custom-text", help="Optional custom prompt text (Crucial Constraints - Additions)")
    parser.add_argument("--animal-features", action="store_true", help="Enable animal feature VFX prompt")
    parser.add_argument("--halo-vfx", action="store_true", help="Enable halo VFX prompt")
    parser.add_argument("--hair-color", help="Value for [HAIR_COLOR] when using color_palette VFX")
    parser.add_argument("--eye-color", help="Value for [EYE_COLOR] when using color_palette VFX")
    parser.add_argument("--combat-prop", action="append", help="Combat prop key from configs/props_catalog.json (repeatable)")
    parser.add_argument("--wig-prop", action="append", help="Wing prop key from configs/props_catalog.json (repeatable)")


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

    selected_combat_props = _dedupe_keep_order(getattr(args, "combat_prop", None))
    selected_wig_props = _dedupe_keep_order(getattr(args, "wig_prop", None))

    if selected_combat_props or selected_wig_props:
        combat_catalog, wig_catalog = _load_props_catalog()

        if selected_combat_props:
            vfx_options.append("combat_props")
            vfx_params["COMBAT_PROP_ITEMS"] = _resolve_selected_labels(
                selected_keys=selected_combat_props,
                catalog=combat_catalog,
                option_name="--combat-prop",
            )

        if selected_wig_props:
            vfx_options.append("wig_props")
            vfx_params["WIG_PROP_ITEMS"] = _resolve_selected_labels(
                selected_keys=selected_wig_props,
                catalog=wig_catalog,
                option_name="--wig-prop",
            )

    return vfx_options, vfx_params


def build_parser() -> argparse.ArgumentParser:
    # 로컬에서 빠르게 기능별 파이프라인을 실행해보기 위한 CLI 엔트리
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
    master.add_argument("--user-custom-text", help="Optional custom prompt text (Additions)")
    master.add_argument("--output-filename")
    master.add_argument("--dry-run", action="store_true")

    return parser


def main() -> int:
    # 1) 명령과 인자 파싱
    parser = build_parser()
    args = parser.parse_args()

    # 2) 기본 설정/서비스를 묶은 파이프라인 생성
    pipeline = ImageGenerationPipeline.create_default()

    # 3) 명령 종류에 따라 기능 1/2/3 중 하나를 실행
    try:
        vfx_options, vfx_params = _build_vfx_payload(args)
    except ValueError as exc:
        parser.error(str(exc))

    if args.command == "cosplay-basic":
        result = pipeline.generate_cosplay_basic(
            CosplayBasicRequest(
                illustration_path=args.illustration_path,
                user_custom_text=args.user_custom_text,
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
                user_custom_text=args.user_custom_text,
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
                user_custom_text=args.user_custom_text,
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