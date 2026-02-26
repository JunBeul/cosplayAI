"""
파일명: main.py
작성자: JunBeul
설명: FastAPI 앱 객체를 생성하고 생성 관련 라우터를 등록한 뒤, Uvicorn 실행용 app 인스턴스를 노출한다.
상위 모듈: 없음
하위 모듈: backend.api.routes_generation
"""


from __future__ import annotations
from fastapi import FastAPI
from .routes_generation import router as generation_router


def create_app() -> FastAPI:
    # FastAPI 앱 생성 후, 라우터를 붙이는 가장 바깥쪽 엔트리 함수
    app = FastAPI(title="CosplayAI Backend", version="0.1.0")
    app.include_router(generation_router)
    return app


app = create_app() # uvicorn이 `backend.api.main:app` 형태로 불러갈 객체
