from __future__ import annotations

from pathlib import Path


ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def _sanitize_path_value(image_path: str) -> str:
    # `.env`에 따옴표가 섞여 있어도 안전하게 제거한다.
    return image_path.strip().strip('"').strip("'")


def _resolve_input_path(image_path: str) -> Path:
    # 경로 규칙:
    # - 절대경로면 그대로 사용
    # - 상대경로면 "프로젝트 루트 기준"으로 해석
    path = Path(_sanitize_path_value(image_path))
    if path.is_absolute():
        return path

    project_root = Path(__file__).resolve().parents[2]
    return project_root / path


def validate_image_path(image_path: str, field_name: str) -> Path:
    # 입력 파일 경로 존재 여부 + 확장자 검증
    if not image_path:
        raise ValueError(f"{field_name} is required")

    path = _resolve_input_path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Input image not found: {image_path}")

    if path.suffix.lower() not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError(
            f"Unsupported image extension for {field_name}: {path.suffix}. "
            f"Allowed: {sorted(ALLOWED_IMAGE_EXTENSIONS)}"
        )

    return path
