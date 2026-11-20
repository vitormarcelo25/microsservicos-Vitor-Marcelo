"""API Gateway do HelpDesk TI: o único ponto de entrada (porta 8000).

* serve a tela (index.html, app.js, estilo.css);
* encaminha cada rota da API para o serviço certo (Usuários, Inventário, Chamados, Notificações);
* mostra em `/saude` quais serviços estão no ar.

O gateway não confere tokens nem tem regras de negócio: ele só repassa. Cada serviço
confere o token sozinho, então um serviço continua protegido mesmo se alguém o alcançar
por outro caminho.
"""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, JSONResponse

from app import config
from app.seguranca_http import CabecalhosDeSeguranca

WEB = Path(__file__).parent.parent / "web"

# Só estes cabeçalhos do cliente seguem para o serviço. Quem não está na lista (inclusive qualquer
# X-Forwarded-For que o cliente tenha inventado) é descartado.
CABECALHOS_DA_REQUISICAO = {"authorization", "content-type", "accept", "accept-language", "user-agent"}
# Só estes cabeçalhos do serviço voltam para o cliente (os de segurança são do gateway).
CABECALHOS_DA_RESPOSTA = {"content-type", "www-authenticate", "retry-after"}


def novo_cliente_http() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=httpx.Timeout(config.TIMEOUT, connect=config.TIMEOUT_CONEXAO))


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    app.state.http = novo_cliente_http()
    yield
    await app.state.http.aclose()


app = FastAPI(
    title="HelpDesk TI · API Gateway", version="3.0.0", lifespan=ciclo_de_vida,
    docs_url=None, redoc_url=None, openapi_url=None,
)
app.add_middleware(CabecalhosDeSeguranca)


def erro(status: int, detalhe: str, **cabecalhos) -> JSONResponse:
    return JSONResponse(status_code=status, content={"detail": detalhe}, headers=cabecalhos or None)


# ---------- tela ----------

@app.get("/", include_in_schema=False)
def tela_inicial():
    return FileResponse(WEB / "index.html")


@app.get("/app.js", include_in_schema=False)
def script():
    return FileResponse(WEB / "app.js", media_type="text/javascript")


@app.get("/estilo.css", include_in_schema=False)
def estilo():
    return FileResponse(WEB / "estilo.css", media_type="text/css")


# ---------- saúde ----------

async def _saude_do_servico(http: httpx.AsyncClient, nome: str) -> tuple[str, str]:
    try:
        r = await http.get(f"{config.SERVICOS[nome]}/saude", timeout=config.TIMEOUT_SAUDE)
        return nome, "ok" if r.status_code == 200 else "com problema"
    except httpx.HTTPError:
        return nome, "fora do ar"


@app.get("/saude", tags=["Saúde"])
async def saude(request: Request):
    """O gateway está no ar (se respondeu, está). Mostra também o estado de cada serviço."""
    resultados = await asyncio.gather(*(_saude_do_servico(request.app.state.http, n) for n in config.SERVICOS))
    servicos = dict(resultados)
    todos_ok = all(estado == "ok" for estado in servicos.values())
    return {"status": "ok" if todos_ok else "degradado", "gateway": "ok", "servicos": servicos}


# ---------- encaminhamento da API ----------

@app.api_route("/{caminho:path}", methods=["GET", "POST", "PATCH", "PUT", "DELETE"], include_in_schema=False)
async def encaminhar(caminho: str, request: Request):
    partes = caminho.split("/")
    servico = config.ROTAS.get(partes[0])
    if servico is None or ".." in partes or "" in partes[1:]:
        return erro(404, "Rota não encontrada.")

    corpo = await request.body()
    if len(corpo) > config.TAMANHO_MAXIMO_REQUISICAO:
        return erro(413, "Requisição grande demais.")

    cabecalhos = {k: v for k, v in request.headers.items() if k.lower() in CABECALHOS_DA_REQUISICAO}
    # Quem está do outro lado é o gateway: informa o endereço real do cliente (usado no limite de login)
    cabecalhos["x-forwarded-for"] = request.client.host if request.client else "-"

    url = f"{config.SERVICOS[servico]}/{caminho}"
    if request.url.query:
        url += "?" + request.url.query

    try:
        resposta = await request.app.state.http.request(request.method, url, headers=cabecalhos, content=corpo)
    except httpx.TimeoutException:
        return erro(504, f"O serviço de {config.NOMES[servico]} demorou demais para responder.", **{"Retry-After": "10"})
    except httpx.HTTPError:
        return erro(503, f"O serviço de {config.NOMES[servico]} está indisponível no momento. Tente novamente em instantes.",
                    **{"Retry-After": "10"})

    return Response(
        content=resposta.content, status_code=resposta.status_code,
        headers={k: v for k, v in resposta.headers.items() if k.lower() in CABECALHOS_DA_RESPOSTA},
    )
