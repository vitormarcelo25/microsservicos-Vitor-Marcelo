"""Testes de segurança do serviço de Usuários: login, tokens e senhas."""
from datetime import datetime, timedelta, timezone

import jwt

from app import config
from tests.conftest import SENHA


def test_rotas_exigem_login(cliente, contas):
    for rota in ["/usuarios", "/usuarios/1", "/auth/eu"]:
        assert cliente.get(rota).status_code == 401, rota


def test_login_devolve_token_com_perfil(cliente, contas):
    r = cliente.post("/auth/login", json={"email": "carla@x.com", "senha": SENHA}).json()
    dados = jwt.decode(r["access_token"], config.JWT_SEGREDO, algorithms=["HS256"], issuer=config.JWT_EMISSOR)
    assert dados["perfil"] == "tecnico" and dados["sub"] == str(r["usuario"]["id"])


def test_login_com_senha_errada(cliente, contas):
    r = cliente.post("/auth/login", json={"email": "ana@x.com", "senha": "errada123"})
    assert r.status_code == 401 and r.json()["detail"] == "E-mail ou senha inválidos."


def test_login_com_email_inexistente_tem_a_mesma_mensagem(cliente, contas):
    r = cliente.post("/auth/login", json={"email": "ninguem@x.com", "senha": "errada123"})
    assert r.status_code == 401 and r.json()["detail"] == "E-mail ou senha inválidos."


def test_bloqueio_apos_varias_senhas_erradas(cliente, contas):
    for _ in range(config.LOGIN_MAX_FALHAS):
        cliente.post("/auth/login", json={"email": "ana@x.com", "senha": "errada123"})
    # mesmo com a senha certa, fica bloqueado por um tempo
    assert cliente.post("/auth/login", json={"email": "ana@x.com", "senha": SENHA}).status_code == 429


def test_bloqueio_considera_o_endereco_encaminhado_pelo_gateway(cliente, contas):
    for _ in range(config.LOGIN_MAX_FALHAS):
        cliente.post("/auth/login", json={"email": "ana@x.com", "senha": "errada123"}, headers={"X-Forwarded-For": "10.0.0.1"})
    # outra pessoa (outro endereço) não é bloqueada junto
    r = cliente.post("/auth/login", json={"email": "ana@x.com", "senha": SENHA}, headers={"X-Forwarded-For": "10.0.0.2"})
    assert r.status_code == 200


def test_token_adulterado(cliente, contas):
    token = contas["ana"]["headers"]["Authorization"] + "x"
    assert cliente.get("/auth/eu", headers={"Authorization": token}).status_code == 401


def _falso(sub, segredo, algoritmo="HS256", **extra):
    agora = datetime.now(timezone.utc)
    dados = {"sub": str(sub), "iss": config.JWT_EMISSOR, "iat": agora, "exp": agora + timedelta(hours=1), **extra}
    return jwt.encode(dados, segredo, algorithm=algoritmo)


def test_token_assinado_com_outro_segredo(cliente, contas):
    falso = _falso(contas["admin"]["id"], "segredo-de-outra-pessoa-com-mais-de-32-caracteres")
    assert cliente.get("/auth/eu", headers={"Authorization": f"Bearer {falso}"}).status_code == 401


def test_token_sem_assinatura_alg_none(cliente, contas):
    falso = _falso(contas["admin"]["id"], None, "none")
    assert cliente.get("/auth/eu", headers={"Authorization": f"Bearer {falso}"}).status_code == 401


def test_token_expirado(cliente, contas):
    antigo = datetime.now(timezone.utc) - timedelta(hours=2)
    vencido = jwt.encode({"sub": str(contas["ana"]["id"]), "iss": config.JWT_EMISSOR, "iat": antigo,
                          "exp": antigo + timedelta(minutes=5)}, config.JWT_SEGREDO, algorithm="HS256")
    assert cliente.get("/auth/eu", headers={"Authorization": f"Bearer {vencido}"}).status_code == 401


def test_senha_guardada_com_hash(sessao, contas):
    from app.usuarios.modelos import Usuario
    with sessao() as db:
        u = db.query(Usuario).filter_by(email="ana@x.com").one()
        assert SENHA not in u.senha_hash and u.senha_hash.startswith("scrypt$")


def test_senha_fraca_e_recusada(cliente, contas):
    r = cliente.post("/usuarios", headers=contas["admin"]["headers"],
                     json={"nome": "Eva", "email": "eva@x.com", "perfil": "solicitante", "senha": "abcdefgh"})
    assert r.status_code == 422


def test_cabecalhos_de_seguranca_e_saude(cliente):
    r = cliente.get("/saude")
    assert r.json() == {"status": "ok", "servico": "usuarios"}
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["x-frame-options"] == "DENY"


def test_requisicao_grande_demais(cliente, contas):
    corpo = '{"nome": "' + "x" * 70000 + '"}'
    r = cliente.post("/usuarios", headers={**contas["admin"]["headers"], "Content-Type": "application/json"}, content=corpo)
    assert r.status_code == 413
