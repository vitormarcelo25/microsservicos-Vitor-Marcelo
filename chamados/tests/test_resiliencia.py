"""O que acontece quando Usuários, Inventário ou a fila estão fora do ar.

É a parte nova em relação ao monólito: agora existe a rede no meio, e ela falha.
"""
import httpx
import redis

from app import clientes, config, eventos
from app.clientes import Disjuntor
from tests.conftest import PUBLICAR_REAL


def abrir(cliente, contas, **extra):
    dados = {"titulo": "PC não liga", "descricao": "Nada acontece", "prioridade": "alta", "ativo_id": 1, **extra}
    return cliente.post("/chamados", headers=contas["ana"]["headers"], json=dados)


# ---------- Inventário fora do ar ----------

def test_inventario_fora_do_ar_responde_503_claro(cliente, contas, externos, fila):
    externos.fora.add("inventario")
    r = abrir(cliente, contas)
    assert r.status_code == 503
    assert "Inventário" in r.json()["detail"] and "indisponível" in r.json()["detail"]
    assert r.headers["retry-after"] == "10"
    assert fila == []  # não salvou, não avisou


def test_inventario_lento_estoura_o_timeout_e_responde_503(cliente, contas, externos):
    externos.lentos.add("inventario")
    assert abrir(cliente, contas).status_code == 503


def test_inventario_com_erro_500_vira_503(cliente, contas, externos):
    externos.quebrados.add("inventario")
    assert abrir(cliente, contas).status_code == 503


def test_sem_inventario_ainda_abre_chamado_sem_equipamento_e_lista(cliente, contas, externos):
    externos.fora.add("inventario")
    assert abrir(cliente, contas, ativo_id=None).status_code == 201
    assert len(cliente.get("/chamados", headers=contas["carla"]["headers"]).json()) == 1


def test_volta_a_funcionar_quando_o_inventario_volta(cliente, contas, externos):
    externos.fora.add("inventario")
    assert abrir(cliente, contas).status_code == 503
    externos.fora.clear()
    clientes.reiniciar_disjuntores()
    assert abrir(cliente, contas).status_code == 201


# ---------- Usuários fora do ar ----------

def test_usuarios_fora_do_ar_nao_atribui_mas_o_resto_funciona(cliente, contas, externos):
    cid = abrir(cliente, contas).json()["id"]
    externos.fora.add("usuarios")
    r = cliente.patch(f"/chamados/{cid}/atribuir", headers=contas["carla"]["headers"], json={"tecnico_id": contas["carla"]["id"]})
    assert r.status_code == 503 and "Usuários" in r.json()["detail"]
    # o chamado continua intacto e a consulta continua funcionando
    c = cliente.get(f"/chamados/{cid}", headers=contas["carla"]["headers"]).json()
    assert c["status"] == "aberto" and c["tecnico_id"] is None


# ---------- token repassado ----------

def test_repassa_o_token_da_pessoa_ao_outro_servico(cliente, contas, externos):
    abrir(cliente, contas)
    assert externos.requisicoes[0].headers["authorization"] == contas["ana"]["headers"]["Authorization"]
    assert externos.requisicoes[0].url.path == "/ativos/1"


def test_token_recusado_pelo_outro_servico_nao_vaza_detalhes(cliente, contas, externos, monkeypatch):
    monkeypatch.setattr(clientes, "_http", httpx.Client(transport=httpx.MockTransport(
        lambda req: httpx.Response(401, json={"detail": "segredo interno do outro serviço"}))))
    r = abrir(cliente, contas)
    assert r.status_code == 503 and "segredo interno" not in r.text


# ---------- disjuntor (circuit breaker) ----------

def test_disjuntor_abre_depois_de_falhas_seguidas_e_responde_sem_chamar_a_rede(cliente, contas, externos):
    externos.fora.add("inventario")
    for _ in range(config.DISJUNTOR_FALHAS):
        assert abrir(cliente, contas).status_code == 503
    antes = len(externos.requisicoes)
    assert abrir(cliente, contas).status_code == 503
    assert len(externos.requisicoes) == antes  # disjuntor aberto: nem tentou a rede


def test_disjuntor_libera_uma_tentativa_depois_da_espera():
    relogio = [100.0]
    d = Disjuntor(falhas_max=2, espera=10, relogio=lambda: relogio[0])
    d.falha(); d.falha()
    assert d.aberto and not d.permite()
    relogio[0] += 11
    assert d.permite()          # tentativa de teste
    d.falha()                   # falhou de novo: reabre na hora
    assert d.aberto
    relogio[0] += 11
    assert d.permite()
    d.sucesso()                 # deu certo: fecha de vez
    assert not d.aberto and d.permite()


# ---------- fila de eventos fora do ar ----------

def test_publicar_sem_redis_nao_lanca_erro(monkeypatch):
    class RedisFora:
        def xadd(self, *args, **kwargs):
            raise redis.ConnectionError("sem conexão")

    monkeypatch.setattr(eventos, "_redis", RedisFora())
    assert eventos.publicar("ChamadoAberto", 1, 2, "oi") is False


def test_chamado_e_aberto_mesmo_com_a_fila_fora_do_ar(cliente, contas, monkeypatch):
    class RedisFora:
        def xadd(self, *args, **kwargs):
            raise redis.ConnectionError("sem conexão")

    monkeypatch.setattr(eventos, "publicar", PUBLICAR_REAL)  # a fixture `fila` tinha trocado o publicar
    monkeypatch.setattr(eventos, "_redis", RedisFora())
    assert abrir(cliente, contas).status_code == 201
