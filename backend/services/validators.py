from __future__ import annotations

from pathlib import Path


ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def validate_image_path(image_path: str, field_name: str) -> Path:
    # 입력 파일 경로 존재 여부 + 확장자 검증
    if not image_path:
        raise ValueError(f"{field_name} is required")

    # 경로 규칙:
    # - 절대경로면 그대로 사용
    # - 상대경로면 프로젝트 루트 기준으로 해석
    path = Path(image_path)
    if not path.is_absolute():
        project_root = Path(__file__).resolve().parents[2]
        path = project_root / path

    if not path.exists():
        raise FileNotFoundError(f"Input image not found: {image_path}")

    if path.suffix.lower() not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError(
            f"Unsupported image extension for {field_name}: {path.suffix}. "
            f"Allowed: {sorted(ALLOWED_IMAGE_EXTENSIONS)}"
        )

    return path
