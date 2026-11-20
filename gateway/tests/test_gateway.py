"""Testes do API Gateway: encaminhamento, falhas dos serviços, saúde e segurança."""
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app


class ServicosFalsos:
    """Responde no lugar dos serviços e guarda o que o gateway encaminhou."""

    def __init__(self):
        self.requisicoes: list[httpx.Request] = []
        self.fora: set[str] = set()
        self.lentos: set[str] = set()

    def __call__(self, req: httpx.Request) -> httpx.Response:
        self.requisicoes.append(req)
        servico = req.url.host
        if servico in self.fora:
            raise httpx.ConnectError("fora do ar", request=req)
        if servico in self.lentos:
            raise httpx.ReadTimeout("lento", request=req)
        if req.url.path == "/saude":
            return httpx.Response(200, json={"status": "ok", "servico": servico})
        return httpx.Response(
            201 if req.method == "POST" else 200,
            json={"servico": servico, "caminho": req.url.path, "consulta": req.url.query.decode()},
            headers={"X-Interno": "nao-deve-vazar", "Retry-After": "7"},
        )


@pytest.fixture
def servicos():
    return ServicosFalsos()


@pytest.fixture
def cliente(servicos):
    with TestClient(app) as c:
        app.state.http = httpx.AsyncClient(transport=httpx.MockTransport(servicos))
        yield c


@pytest.mark.parametrize("rota,servico", [
    ("/auth/login", "usuarios"), ("/auth/eu", "usuarios"), ("/usuarios", "usuarios"), ("/usuarios/3", "usuarios"),
    ("/ativos", "inventario"), ("/ativos/1", "inventario"),
    ("/chamados", "chamados"), ("/chamados/painel", "chamados"), ("/chamados/4/atribuir", "chamados"),
    ("/notificacoes", "notificacoes"),
])
def test_cada_rota_vai_para_o_servico_certo(cliente, rota, servico):
    r = cliente.get(rota)
    assert r.status_code == 200
    assert r.json()["servico"] == servico and r.json()["caminho"] == rota


def test_repassa_metodo_corpo_e_consulta(cliente, servicos):
    r = cliente.post("/chamados?status=aberto", json={"titulo": "x"})
    assert r.status_code == 201
    req = servicos.requisicoes[-1]
    assert req.method == "POST" and req.read() == b'{"titulo":"x"}' and req.url.query == b"status=aberto"


def test_repassa_o_token(cliente, servicos):
    cliente.get("/chamados", headers={"Authorization": "Bearer abc"})
    assert servicos.requisicoes[-1].headers["authorization"] == "Bearer abc"


def test_x_forwarded_for_do_cliente_e_descartado_e_o_gateway_informa_o_real(cliente, servicos):
    cliente.post("/auth/login", json={}, headers={"X-Forwarded-For": "1.2.3.4", "X-Forwarded-Host": "evil"})
    req = servicos.requisicoes[-1]
    assert req.headers["x-forwarded-for"] == "testclient"
    assert "x-forwarded-host" not in req.headers


def test_cabecalhos_internos_do_servico_nao_vazam(cliente):
    r = cliente.get("/chamados")
    assert "x-interno" not in r.headers and r.headers["retry-after"] == "7"


def test_rota_desconhecida_ou_com_ponto_ponto(cliente, servicos):
    assert cliente.get("/admin").status_code == 404
    assert cliente.get("/saude/x").status_code == 404
    assert cliente.get("/chamados/../auth/login").status_code in (404, 200)  # o cliente HTTP pode normalizar o caminho
    assert cliente.get("/chamados/%2e%2e/auth/login").status_code == 404
    assert all(r.url.path != "/auth/login" for r in servicos.requisicoes if r.url.host == "chamados")


def test_servico_fora_do_ar_responde_503_claro(cliente, servicos):
    servicos.fora.add("inventario")
    r = cliente.get("/ativos")
    assert r.status_code == 503 and "Inventário" in r.json()["detail"]
    # os outros serviços seguem funcionando
    assert cliente.get("/chamados").status_code == 200


def test_servico_lento_responde_504(cliente, servicos):
    servicos.lentos.add("chamados")
    assert cliente.get("/chamados").status_code == 504


def test_requisicao_grande_demais(cliente):
    r = cliente.post("/chamados", content="x" * 70000, headers={"Content-Type": "application/json"})
    assert r.status_code == 413


def test_saude_mostra_quem_esta_no_ar(cliente, servicos):
    r = cliente.get("/saude").json()
    assert r["status"] == "ok" and set(r["servicos"].values()) == {"ok"}
    servicos.fora.add("inventario")
    r = cliente.get("/saude").json()
    assert r["status"] == "degradado" and r["gateway"] == "ok"
    assert r["servicos"]["inventario"] == "fora do ar" and r["servicos"]["usuarios"] == "ok"


def test_tela_e_cabecalhos_de_seguranca(cliente):
    r = cliente.get("/")
    assert r.status_code == 200 and "HelpDesk TI" in r.text
    assert "script-src 'self'" in r.headers["content-security-policy"]
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["x-frame-options"] == "DENY"
    assert cliente.get("/app.js").status_code == 200 and cliente.get("/estilo.css").status_code == 200


def test_documentacao_nao_e_exposta(cliente):
    assert cliente.get("/docs").status_code == 404 and cliente.get("/openapi.json").status_code == 404


def test_tela_escapa_o_html():
    js = (Path(__file__).parent.parent / "web" / "app.js").read_text()
    assert "const esc =" in js and "onclick" not in js
