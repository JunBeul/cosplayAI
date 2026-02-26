from __future__ import annotations

from fastapi import FastAPI

from .routes_generation import router as generation_router


def create_app() -> FastAPI:
    # FastAPI 앱 생성 후, 라우터를 붙이는 가장 바깥쪽 엔트리 함수
    app = FastAPI(title="CosplayAI Backend", version="0.1.0")
    app.include_router(generation_router)
    return app


# uvicorn이 `backend.api.main:app` 형태로 불러갈 객체
app = create_app()
