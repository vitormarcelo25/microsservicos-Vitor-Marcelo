"""Regras do serviço de Chamados (as mesmas do monólito: SLA, transições e comentários)."""
from datetime import datetime


def abrir(cliente, contas, quem="ana", prioridade="alta", **extra):
    dados = {"titulo": "PC não liga", "descricao": "Nada acontece", "prioridade": prioridade, "ativo_id": 1, **extra}
    return cliente.post("/chamados", headers=contas[quem]["headers"], json=dados)


def test_abrir_calcula_sla_e_publica_evento(cliente, contas, fila):
    r = abrir(cliente, contas, prioridade="critica")
    assert r.status_code == 201
    c = r.json()
    assert c["solicitante_id"] == contas["ana"]["id"] and c["status"] == "aberto"
    horas = (datetime.fromisoformat(c["prazo_sla"]) - datetime.fromisoformat(c["criado_em"])).total_seconds() / 3600
    assert round(horas) == 4
    assert [(e["tipo"], e["destinatario_id"]) for e in fila] == [("ChamadoAberto", contas["ana"]["id"])]
    assert f"#{c['id']}" in fila[0]["mensagem"]


def test_abrir_sem_equipamento_nao_chama_o_inventario(cliente, contas, externos):
    r = abrir(cliente, contas, ativo_id=None)
    assert r.status_code == 201
    assert externos.requisicoes == []


def test_abrir_com_ativo_inexistente(cliente, contas, fila):
    assert abrir(cliente, contas, ativo_id=999).status_code == 404
    assert fila == []  # nada foi salvo, nenhum evento foi publicado


def test_atribuir_muda_status_e_avisa_tecnico(cliente, contas, fila):
    cid = abrir(cliente, contas).json()["id"]
    r = cliente.patch(f"/chamados/{cid}/atribuir", headers=contas["carla"]["headers"], json={"tecnico_id": contas["carla"]["id"]})
    assert r.json()["status"] == "em_atendimento" and r.json()["tecnico_id"] == contas["carla"]["id"]
    assert (fila[-1]["tipo"], fila[-1]["destinatario_id"]) == ("ChamadoAtribuido", contas["carla"]["id"])


def test_so_tecnico_pode_ser_atribuido(cliente, contas):
    cid = abrir(cliente, contas).json()["id"]
    r = cliente.patch(f"/chamados/{cid}/atribuir", headers=contas["carla"]["headers"], json={"tecnico_id": contas["ana"]["id"]})
    assert r.status_code == 422


def test_atribuir_a_usuario_inexistente(cliente, contas):
    cid = abrir(cliente, contas).json()["id"]
    r = cliente.patch(f"/chamados/{cid}/atribuir", headers=contas["carla"]["headers"], json={"tecnico_id": 77})
    assert r.status_code == 404


def test_fluxo_completo_de_status(cliente, contas, fila):
    cid = abrir(cliente, contas).json()["id"]
    tec = contas["carla"]["headers"]
    cliente.patch(f"/chamados/{cid}/atribuir", headers=tec, json={"tecnico_id": contas["carla"]["id"]})
    assert cliente.patch(f"/chamados/{cid}/status", headers=tec, json={"status": "resolvido"}).status_code == 200
    assert fila[-1]["tipo"] == "ChamadoResolvido" and fila[-1]["destinatario_id"] == contas["ana"]["id"]
    # o próprio solicitante confirma e fecha
    r = cliente.patch(f"/chamados/{cid}/status", headers=contas["ana"]["headers"], json={"status": "fechado"})
    assert r.json()["status"] == "fechado"


def test_transicao_invalida(cliente, contas):
    cid = abrir(cliente, contas).json()["id"]
    r = cliente.patch(f"/chamados/{cid}/status", headers=contas["carla"]["headers"], json={"status": "fechado"})
    assert r.status_code == 422


def test_iniciar_atendimento_sem_tecnico(cliente, contas):
    cid = abrir(cliente, contas).json()["id"]
    r = cliente.patch(f"/chamados/{cid}/status", headers=contas["carla"]["headers"], json={"status": "em_atendimento"})
    assert r.status_code == 422


def test_comentar_usa_o_usuario_logado(cliente, contas):
    cid = abrir(cliente, contas).json()["id"]
    r = cliente.post(f"/chamados/{cid}/comentarios", headers=contas["carla"]["headers"], json={"texto": "Verificando a fonte."})
    assert r.status_code == 201 and r.json()["autor_id"] == contas["carla"]["id"]
    assert len(cliente.get(f"/chamados/{cid}", headers=contas["ana"]["headers"]).json()["comentarios"]) == 1


def test_chamado_fechado_nao_recebe_comentarios(cliente, contas):
    cid = abrir(cliente, contas).json()["id"]
    tec = contas["carla"]["headers"]
    cliente.patch(f"/chamados/{cid}/atribuir", headers=tec, json={"tecnico_id": contas["carla"]["id"]})
    cliente.patch(f"/chamados/{cid}/status", headers=tec, json={"status": "resolvido"})
    cliente.patch(f"/chamados/{cid}/status", headers=tec, json={"status": "fechado"})
    assert cliente.post(f"/chamados/{cid}/comentarios", headers=tec, json={"texto": "oi"}).status_code == 422


def test_painel(cliente, contas):
    abrir(cliente, contas)
    abrir(cliente, contas, prioridade="baixa")
    p = cliente.get("/chamados/painel", headers=contas["carla"]["headers"]).json()
    assert p["total"] == 2 and p["por_status"] == {"aberto": 2} and p["atrasados"] == 0
