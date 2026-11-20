"""Serviço de Inventário: computadores, impressoras e outros equipamentos de TI.

Dono do banco de inventário. O serviço de Chamados nunca acessa este banco:
ele chama `GET /ativos/{id}` pela rede, repassando o token da pessoa.
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app import dados_exemplo
from app.config import DOCS_ATIVA
from app.database import Base, SessionLocal, engine
from app.erros import NaoEncontrado, RegraDeNegocio, SemPermissao
from app.inventario.rotas import router as inventario_router
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
    title="HelpDesk TI · Serviço de Inventário", version="3.0.0", lifespan=ciclo_de_vida,
    docs_url="/docs" if DOCS_ATIVA else None, redoc_url=None,
    openapi_url="/openapi.json" if DOCS_ATIVA else None,
)
app.add_middleware(CabecalhosDeSeguranca)
app.include_router(inventario_router)


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


@app.get("/saude", tags=["Saúde"])
def saude():
    return {"status": "ok", "servico": "inventario"}
