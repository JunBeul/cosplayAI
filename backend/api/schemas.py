from __future__ import annotations

from pydantic import BaseModel


class HealthResponseSchema(BaseModel):
    # 서버 생존 여부만 확인하는 간단한 응답
    # 생성 요청/응답 모델은 `backend.domain.models`를 공용으로 사용한다.
    status: str = "ok"
