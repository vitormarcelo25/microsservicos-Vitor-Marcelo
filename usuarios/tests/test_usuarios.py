"""Regras e permissões do serviço de Usuários."""


def test_admin_cria_usuario(cliente, contas):
    r = cliente.post("/usuarios", headers=contas["admin"]["headers"],
                     json={"nome": "Davi", "email": "davi@x.com", "perfil": "tecnico", "senha": "Forte1234"})
    assert r.status_code == 201
    assert "senha" not in r.json() and "senha_hash" not in r.json()


def test_solicitante_nao_cria_usuario(cliente, contas):
    r = cliente.post("/usuarios", headers=contas["ana"]["headers"],
                     json={"nome": "Eva", "email": "eva@x.com", "perfil": "admin", "senha": "Forte1234"})
    assert r.status_code == 403


def test_email_repetido_e_recusado(cliente, contas):
    dados = {"nome": "Ana 2", "email": "ANA@x.com", "perfil": "solicitante", "senha": "Forte1234"}
    assert cliente.post("/usuarios", headers=contas["admin"]["headers"], json=dados).status_code == 422


def test_usuario_inexistente(cliente, contas):
    assert cliente.get("/usuarios/99", headers=contas["ana"]["headers"]).status_code == 404


def test_lista_publica_nao_mostra_email(cliente, contas):
    lista = cliente.get("/usuarios", headers=contas["ana"]["headers"]).json()
    assert lista and all("email" not in u for u in lista)


def test_obter_usuario_devolve_o_perfil(cliente, contas):
    """O serviço de Chamados usa este perfil para saber se a pessoa é técnica."""
    u = cliente.get(f"/usuarios/{contas['carla']['id']}", headers=contas["ana"]["headers"]).json()
    assert u == {"id": contas["carla"]["id"], "nome": "Carla", "perfil": "tecnico"}


def test_filtra_por_perfil(cliente, contas):
    tecnicos = cliente.get("/usuarios", params={"perfil": "tecnico"}, headers=contas["ana"]["headers"]).json()
    assert [t["nome"] for t in tecnicos] == ["Carla"]
