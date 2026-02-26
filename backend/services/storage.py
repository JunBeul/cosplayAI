from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class StorageManager:
    def __init__(self, outputs_dir: Path) -> None:
        # 결과 이미지/메타데이터 저장 디렉터리 보장
        self.outputs_dir = outputs_dir
        self.outputs_dir.mkdir(parents=True, exist_ok=True)

    def build_output_path(self, prefix: str, requested_filename: str | None = None) -> Path:
        # 사용자가 파일명을 지정하면 우선 사용하고, 아니면 UTC 타임스탬프로 생성
        if requested_filename:
            output_path = self.outputs_dir / requested_filename
            output_path.parent.mkdir(parents=True, exist_ok=True)
            return output_path

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return self.outputs_dir / f"{prefix}_{timestamp}.png"

    def save_image_bytes(self, output_path: Path, image_bytes: bytes) -> Path:
        # 생성된 이미지 바이트를 실제 파일로 저장
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(image_bytes)
        return output_path

    def save_metadata(self, image_path: Path | None, metadata: dict[str, Any]) -> Path:
        # 생성에 사용된 프롬프트/모델/입력 경로를 JSON으로 남겨 재현 가능성을 확보
        if image_path is None:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            metadata_path = self.outputs_dir / f"dry_run_{timestamp}.json"
        else:
            metadata_path = image_path.with_suffix(".json")

        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        return metadata_path
