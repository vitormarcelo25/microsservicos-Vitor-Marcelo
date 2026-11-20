"""Proteções aplicadas a todas as respostas HTTP deste serviço (API só com JSON)."""
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import TAMANHO_MAXIMO_REQUISICAO

CSP_API = "default-src 'none'; frame-ancestors 'none'"
CSP_DOCS = (
    "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https://fastapi.tiangolo.com; "
    "frame-ancestors 'none'; base-uri 'none'"
)


class CabecalhosDeSeguranca(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        tamanho = request.headers.get("content-length")
        if tamanho and (not tamanho.isdigit() or int(tamanho) > TAMANHO_MAXIMO_REQUISICAO):
            return JSONResponse(status_code=413, content={"detail": "Requisição grande demais."})

        resposta = await call_next(request)
        documentacao = request.url.path in ("/docs", "/redoc", "/openapi.json")
        resposta.headers["Content-Security-Policy"] = CSP_DOCS if documentacao else CSP_API
        resposta.headers["X-Content-Type-Options"] = "nosniff"
        resposta.headers["X-Frame-Options"] = "DENY"
        resposta.headers["Referrer-Policy"] = "no-referrer"
        if request.headers.get("authorization"):
            resposta.headers["Cache-Control"] = "no-store"
        return resposta
