"""
파일명: config_loader.py
작성자: JunBeul
설명: configs 폴더의 JSON 파일을 읽어 dict 형태로 반환하며, 프롬프트 빌더가 템플릿 설정을 불러올 때 사용한다.
상위 모듈: backend.services.prompt_builder
하위 모듈: 없음
"""


from __future__ import annotations
import json
from pathlib import Path
from typing import Any


def load_json_file(path: Path) -> dict[str, Any]:
    # 프롬프트/설정 JSON을 안전하게 읽는 공통 함수
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
            return data if isinstance(data, dict) else {}
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Config file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON config: {path}") from exc
