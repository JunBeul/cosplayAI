"""
파일명: enums.py
작성자: JunBeul
설명: 생성 작업 종류를 표시하는 TaskType 등 도메인 열거형을 정의한다.
상위 모듈: backend.domain.models, backend.services.pipelines
하위 모듈: 없음
"""


from enum import Enum


class TaskType(str, Enum):
    # 내부 파이프라인과 API 응답에서 공통으로 사용하는 작업 타입
    COSPLAY_BASIC = "cosplay_basic"
    COSPLAY_WITH_MASTER = "cosplay_with_master"
    MASTER_IMAGE = "master_image"
