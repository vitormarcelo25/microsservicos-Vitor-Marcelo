"""Regras, permissões e segurança do serviço de Inventário."""
from datetime import datetime, timedelta, timezone

import jwt

from app import config

NOVO = {"patrimonio": "PAT-9", "tipo": "outro", "descricao": "X", "setor": "TI"}


def test_rotas_exigem_login(cliente):
    assert cliente.get("/ativos").status_code == 401
    assert cliente.get("/ativos/1").status_code == 401
    assert cliente.post("/ativos", json=NOVO).status_code == 401


def test_tecnico_cadastra_ativo_e_filtra_por_setor(cliente, contas):
    h = contas["carla"]["headers"]
    cliente.post("/ativos", headers=h, json={"patrimonio": "PAT-1", "tipo": "impressora", "descricao": "HP", "setor": "RH"})
    cliente.post("/ativos", headers=h, json={"patrimonio": "PAT-2", "tipo": "computador", "descricao": "Dell", "setor": "TI"})
    assert len(cliente.get("/ativos", params={"setor": "RH"}, headers=h).json()) == 1


def test_solicitante_nao_cadastra_ativo(cliente, contas):
    assert cliente.post("/ativos", headers=contas["ana"]["headers"], json=NOVO).status_code == 403


def test_solicitante_consulta_ativo(cliente, contas):
    """O serviço de Chamados repassa o token de quem abre o chamado, que costuma ser solicitante."""
    ativo = cliente.post("/ativos", headers=contas["carla"]["headers"], json=NOVO).json()
    r = cliente.get(f"/ativos/{ativo['id']}", headers=contas["ana"]["headers"])
    assert r.status_code == 200 and r.json()["patrimonio"] == "PAT-9"


def test_ativo_inexistente(cliente, contas):
    assert cliente.get("/ativos/99", headers=contas["ana"]["headers"]).status_code == 404


def test_patrimonio_repetido(cliente, contas):
    h = contas["carla"]["headers"]
    cliente.post("/ativos", headers=h, json=NOVO)
    assert cliente.post("/ativos", headers=h, json=NOVO).status_code == 422


def test_campos_extras_e_formato_sao_recusados(cliente, contas):
    h = contas["carla"]["headers"]
    assert cliente.post("/ativos", headers=h, json={**NOVO, "id": 5}).status_code == 422
    assert cliente.post("/ativos", headers=h, json={**NOVO, "patrimonio": "PAT 9; DROP"}).status_code == 422


def test_token_adulterado(cliente, contas):
    h = {"Authorization": contas["ana"]["headers"]["Authorization"] + "x"}
    assert cliente.get("/ativos", headers=h).status_code == 401


def test_token_de_outro_segredo(cliente):
    agora = datetime.now(timezone.utc)
    falso = jwt.encode({"sub": "1", "perfil": "admin", "iss": config.JWT_EMISSOR, "iat": agora,
                        "exp": agora + timedelta(hours=1)}, "segredo-de-outra-pessoa-com-mais-de-32-caracteres", algorithm="HS256")
    assert cliente.get("/ativos", headers={"Authorization": f"Bearer {falso}"}).status_code == 401


def test_token_alg_none(cliente):
    agora = datetime.now(timezone.utc)
    falso = jwt.encode({"sub": "1", "perfil": "admin", "iss": config.JWT_EMISSOR, "iat": agora,
                        "exp": agora + timedelta(hours=1)}, None, algorithm="none")
    assert cliente.get("/ativos", headers={"Authorization": f"Bearer {falso}"}).status_code == 401


def test_token_expirado(cliente):
    antigo = datetime.now(timezone.utc) - timedelta(hours=2)
    vencido = jwt.encode({"sub": "1", "perfil": "admin", "iss": config.JWT_EMISSOR, "iat": antigo,
                          "exp": antigo + timedelta(minutes=5)}, config.JWT_SEGREDO, algorithm="HS256")
    assert cliente.get("/ativos", headers={"Authorization": f"Bearer {vencido}"}).status_code == 401


def test_token_sem_perfil_ou_com_perfil_inventado(cliente):
    agora = datetime.now(timezone.utc)
    base = {"sub": "1", "iss": config.JWT_EMISSOR, "iat": agora, "exp": agora + timedelta(hours=1)}
    sem_perfil = jwt.encode(base, config.JWT_SEGREDO, algorithm="HS256")
    inventado = jwt.encode({**base, "perfil": "super"}, config.JWT_SEGREDO, algorithm="HS256")
    assert cliente.get("/ativos", headers={"Authorization": f"Bearer {sem_perfil}"}).status_code == 401
    assert cliente.get("/ativos", headers={"Authorization": f"Bearer {inventado}"}).status_code == 401


def test_saude_nao_exige_login(cliente):
    r = cliente.get("/saude")
    assert r.status_code == 200 and r.json() == {"status": "ok", "servico": "inventario"}
