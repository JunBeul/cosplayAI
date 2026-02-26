from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    # 프로젝트 전역에서 공통으로 참조하는 경로/환경설정 묶음
    project_root: Path
    config_dir: Path
    inputs_dir: Path
    outputs_dir: Path
    gemini_api_key: str | None
    imagen_edit_model: str = "imagen-3.0-capability-001"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    # backend/core/settings.py 기준으로 프로젝트 루트를 계산한다.
    project_root = Path(__file__).resolve().parents[2]
    env_path = project_root / ".env"

    # 실제 실행 환경은 `.env`만 읽는다. (`.env.example`는 템플릿 문서 역할)
    if env_path.exists():
        load_dotenv(env_path, override=False)

    # 이후 서비스 계층에서 이 설정 객체를 주입받아 동일한 경로/환경을 사용한다.
    return Settings(
        project_root=project_root,
        config_dir=project_root / "configs",
        inputs_dir=project_root / "inputs",
        outputs_dir=project_root / "outputs",
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
    )
