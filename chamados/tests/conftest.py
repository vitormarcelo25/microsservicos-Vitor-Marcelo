import os

# O segredo precisa existir antes de importar a aplicação
os.environ.setdefault("JWT_SEGREDO", "segredo-de-teste-com-mais-de-32-caracteres-ok")

from datetime import datetime, timedelta, timezone

import httpx
import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import clientes, config, eventos
from app.database import Base, get_db
from app.main import app

PUBLICAR_REAL = eventos.publicar  # guardado antes de a fixture `fila` trocá-lo


def gerar_token(usuario_id: int, perfil: str, **extra) -> str:
    """Faz o papel do serviço de Usuários: assina um token como ele assinaria."""
    agora = datetime.now(timezone.utc)
    dados = {"sub": str(usuario_id), "perfil": perfil, "iss": config.JWT_EMISSOR, "iat": agora,
             "exp": agora + timedelta(hours=1), **extra}
    return jwt.encode(dados, config.JWT_SEGREDO, algorithm="HS256")


class ServicosFalsos:
    """Finge ser os serviços de Usuários e de Inventário (responde no lugar da rede).

    Guarda cada requisição recebida e permite "derrubar" um serviço, como o
    `docker compose stop` faz de verdade.
    """

    def __init__(self):
        self.ativos = {1: {"id": 1, "patrimonio": "PAT-1", "tipo": "computador", "descricao": "Desktop", "setor": "TI"}}
        self.usuarios = {
            2: {"id": 2, "nome": "Ana", "perfil": "solicitante"},
            3: {"id": 3, "nome": "Bia", "perfil": "solicitante"},
            4: {"id": 4, "nome": "Carla", "perfil": "tecnico"},
            5: {"id": 5, "nome": "Diego", "perfil": "tecnico"},
        }
        self.fora: set[str] = set()      # serviços que recusam conexão
        self.lentos: set[str] = set()    # serviços que estouram o tempo limite
        self.quebrados: set[str] = set()  # serviços que respondem erro 500
        self.requisicoes: list[httpx.Request] = []

    def __call__(self, req: httpx.Request) -> httpx.Response:
        self.requisicoes.append(req)
        servico = req.url.host  # "usuarios" ou "inventario"
        if servico in self.fora:
            raise httpx.ConnectError("fora do ar", request=req)
        if servico in self.lentos:
            raise httpx.ReadTimeout("muito lento", request=req)
        if servico in self.quebrados:
            return httpx.Response(500, json={"detail": "erro interno"})
        if not req.headers.get("authorization", "").startswith("Bearer "):
            return httpx.Response(401, json={"detail": "Faça login para continuar."})
        tabela = self.ativos if servico == "inventario" else self.usuarios
        registro = tabela.get(int(req.url.path.rsplit("/", 1)[1]))
        return httpx.Response(200, json=registro) if registro else httpx.Response(404, json={"detail": "não encontrado"})


@pytest.fixture
def externos(monkeypatch):
    falsos = ServicosFalsos()
    monkeypatch.setattr(clientes, "_http", httpx.Client(transport=httpx.MockTransport(falsos)))
    clientes.reiniciar_disjuntores()
    yield falsos
    clientes.reiniciar_disjuntores()


@pytest.fixture
def fila(monkeypatch):
    """Troca o Redis por uma lista, para os testes olharem os eventos publicados."""
    publicados = []

    def publicar(tipo, chamado_id, destinatario_id, mensagem):
        publicados.append({"tipo": tipo, "chamado_id": chamado_id, "destinatario_id": destinatario_id, "mensagem": mensagem})
        return True

    monkeypatch.setattr(eventos, "publicar", publicar)
    return publicados


@pytest.fixture
def sessao(monkeypatch):
    """Banco novo, em memória, para cada teste."""
    monkeypatch.setenv("DADOS_EXEMPLO", "0")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Sessao = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def db_de_teste():
        db = Sessao()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = db_de_teste
    yield Sessao
    app.dependency_overrides.clear()


@pytest.fixture
def cliente(sessao, externos, fila):
    with TestClient(app) as c:
        yield c


@pytest.fixture
def contas():
    """Cabeçalho de login de cada pessoa (ids iguais aos de ServicosFalsos)."""
    pessoas = {"admin": (1, "admin"), "ana": (2, "solicitante"), "bia": (3, "solicitante"),
               "carla": (4, "tecnico"), "diego": (5, "tecnico")}
    return {n: {"headers": {"Authorization": f"Bearer {gerar_token(i, p)}"}, "id": i} for n, (i, p) in pessoas.items()}
