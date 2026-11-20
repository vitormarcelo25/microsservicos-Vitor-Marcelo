"""Serviço de Chamados: abrir, atribuir, comentar e resolver chamados (com SLA).

Dono do banco de chamados. Para conferir técnico e equipamento, chama os serviços de
Usuários e de Inventário por HTTP; para avisar o resto do sistema, publica eventos.
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app import dados_exemplo
from app.chamados.rotas import router as chamados_router
from app.config import DOCS_ATIVA
from app.database import Base, SessionLocal, engine
from app.erros import NaoEncontrado, RegraDeNegocio, SemPermissao, ServicoIndisponivel
from app.seguranca_http import CabecalhosDeSeguranca


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    """Cria as tabelas e, se pedido, os dados de exemplo ao iniciar."""
    Base.metadata.create_all(engine)
    if os.getenv("DADOS_EXEMPLO", "1") == "1":
        with SessionLocal() as db:
            dados_exemplo.carregar(db)
    yield


app = FastAPI(
    title="HelpDesk TI · Serviço de Chamados", version="3.0.0", lifespan=ciclo_de_vida,
    docs_url="/docs" if DOCS_ATIVA else None, redoc_url=None,
    openapi_url="/openapi.json" if DOCS_ATIVA else None,
)
app.add_middleware(CabecalhosDeSeguranca)
app.include_router(chamados_router)


@app.exception_handler(NaoEncontrado)
def tratar_nao_encontrado(request: Request, erro: NaoEncontrado):
    return JSONResponse(status_code=404, content={"detail": str(erro)})


@app.exception_handler(RegraDeNegocio)
def tratar_regra(request: Request, erro: RegraDeNegocio):
    return JSONResponse(status_code=422, content={"detail": str(erro)})


@app.exception_handler(SemPermissao)
def tratar_sem_permissao(request: Request, erro: SemPermissao):
    return JSONResponse(status_code=403, content={"detail": str(erro)})


@app.exception_handler(IntegrityError)
def tratar_conflito(request: Request, erro: IntegrityError):
    return JSONResponse(status_code=409, content={"detail": "O registro conflita com outro já existente."})


@app.exception_handler(ServicoIndisponivel)
def tratar_servico_indisponivel(request: Request, erro: ServicoIndisponivel):
    # 503 com mensagem clara: o sistema não trava e a pessoa sabe o que tentar de novo
    return JSONResponse(
        status_code=503, headers={"Retry-After": "10"},
        content={"detail": f"O serviço de {erro.servico} está indisponível no momento. Tente novamente em instantes."},
    )


@app.get("/saude", tags=["Saúde"])
def saude():
    return {"status": "ok", "servico": "chamados"}
