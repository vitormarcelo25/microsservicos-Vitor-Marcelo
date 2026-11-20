import os

# O segredo precisa existir antes de importar a aplicação
os.environ.setdefault("JWT_SEGREDO", "segredo-de-teste-com-mais-de-32-caracteres-ok")
os.environ["CONSUMIDOR_ATIVO"] = "0"  # nos testes não há Redis: o consumidor é testado à parte

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import config
from app.database import Base, get_db
from app.main import app


def gerar_token(usuario_id: int, perfil: str) -> str:
    agora = datetime.now(timezone.utc)
    dados = {"sub": str(usuario_id), "perfil": perfil, "iss": config.JWT_EMISSOR, "iat": agora, "exp": agora + timedelta(hours=1)}
    return jwt.encode(dados, config.JWT_SEGREDO, algorithm="HS256")


@pytest.fixture
def sessao():
    """Banco novo, em memória, para cada teste."""
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
def cliente(sessao):
    with TestClient(app) as c:
        yield c


@pytest.fixture
def contas():
    pessoas = {"ana": (2, "solicitante"), "bia": (3, "solicitante"), "carla": (4, "tecnico")}
    return {n: {"headers": {"Authorization": f"Bearer {gerar_token(i, p)}"}, "id": i} for n, (i, p) in pessoas.items()}
