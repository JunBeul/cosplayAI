from enum import Enum


class TaskType(str, Enum):
    # 내부 파이프라인과 API 응답에서 공통으로 사용하는 작업 타입
    COSPLAY_BASIC = "cosplay_basic"
    COSPLAY_WITH_MASTER = "cosplay_with_master"
    MASTER_IMAGE = "master_image"
