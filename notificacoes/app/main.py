"""Serviço de Notificações: avisos para quem abre, recebe e vê resolvido um chamado.

Dono do banco de notificações. Não é chamado pelo serviço de Chamados: ele só lê a fila de
eventos. Se este serviço cair, os chamados continuam sendo abertos.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app import config
from app.config import DOCS_ATIVA
from app.consumidor import Consumidor
from app.database import Base, SessionLocal, engine
from app.erros import NaoEncontrado, RegraDeNegocio, SemPermissao
from app.notificacoes.rotas import router as notificacoes_router
from app.seguranca_http import CabecalhosDeSeguranca


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    """Cria as tabelas e liga o consumidor da fila de eventos."""
    Base.metadata.create_all(engine)
    consumidor = Consumidor(SessionLocal) if config.CONSUMIDOR_ATIVO else None
    if consumidor:
        consumidor.start()
    yield
    if consumidor:
        consumidor.parar()


app = FastAPI(
    title="HelpDesk TI · Serviço de Notificações", version="3.0.0", lifespan=ciclo_de_vida,
    docs_url="/docs" if DOCS_ATIVA else None, redoc_url=None,
    openapi_url="/openapi.json" if DOCS_ATIVA else None,
)
app.add_middleware(CabecalhosDeSeguranca)
app.include_router(notificacoes_router)


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
    return {"status": "ok", "servico": "notificacoes"}
