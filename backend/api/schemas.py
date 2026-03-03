"""
파일명: schemas.py
작성자: JunBeul
설명: API 계층에서만 사용하는 간단한 Pydantic 스키마(예: 헬스체크 응답, API 키 검증 결과)를 정의한다.
상위 모듈: backend.api.routes_generation
하위 모듈: 없음
"""


from __future__ import annotations
from pydantic import BaseModel


class HealthResponseSchema(BaseModel):
    # 서버 생존 여부만 확인하는 간단한 응답
    # 생성 요청/응답 모델은 `backend.domain.models`를 공용으로 사용한다.
    status: str = "ok"

class ApiKeyVerificationResponseSchema(BaseModel):
    # 사용자 Gemini API 키 검증 성공 응답
    valid: bool = True
    provider: str = "gemini"
