"""Serviço de Notificações: API, consumidor da fila e segurança."""
from datetime import datetime, timedelta, timezone

import jwt
import redis

from app import config
from app.consumidor import Consumidor, processar
from app.notificacoes import servico

EVENTO = {"tipo": "ChamadoAberto", "chamado_id": "7", "destinatario_id": "2",
          "mensagem": "Seu chamado #7 foi aberto.", "ocorrido_em": "2026-11-20T12:00:00+00:00"}


# ---------- API ----------

def test_rotas_exigem_login(cliente):
    assert cliente.get("/notificacoes").status_code == 401


def test_token_de_outro_segredo(cliente):
    agora = datetime.now(timezone.utc)
    falso = jwt.encode({"sub": "2", "perfil": "admin", "iss": config.JWT_EMISSOR, "iat": agora, "exp": agora + timedelta(hours=1)},
                       "segredo-de-outra-pessoa-com-mais-de-32-caracteres", algorithm="HS256")
    assert cliente.get("/notificacoes", headers={"Authorization": f"Bearer {falso}"}).status_code == 401


def test_cada_usuario_ve_so_as_proprias_notificacoes(cliente, sessao, contas):
    with sessao() as db:
        servico.notificar(db, "ChamadoAberto", contas["ana"]["id"], "Para a Ana")
        servico.notificar(db, "ChamadoAtribuido", contas["carla"]["id"], "Para a Carla")
    ana = cliente.get("/notificacoes", headers=contas["ana"]["headers"]).json()
    assert [a["mensagem"] for a in ana] == ["Para a Ana"]
    assert cliente.get("/notificacoes", headers=contas["bia"]["headers"]).json() == []


def test_saude(cliente):
    assert cliente.get("/saude").json() == {"status": "ok", "servico": "notificacoes"}


# ---------- consumidor ----------

def test_processar_evento_grava_o_aviso(sessao):
    with sessao() as db:
        assert processar(db, "1-0", EVENTO) is True
        aviso = servico.listar(db, 2)[0]
        assert (aviso.tipo, aviso.mensagem, aviso.evento_id) == ("ChamadoAberto", "Seu chamado #7 foi aberto.", "1-0")


def test_evento_repetido_nao_duplica_o_aviso(sessao):
    with sessao() as db:
        processar(db, "1-0", EVENTO)
        processar(db, "1-0", EVENTO)  # a fila entregou de novo
        assert len(servico.listar(db, 2)) == 1


def test_evento_invalido_e_descartado(sessao):
    with sessao() as db:
        assert processar(db, "2-0", {"tipo": "Inventado", "destinatario_id": "2", "mensagem": "x"}) is False
        assert processar(db, "3-0", {"tipo": "ChamadoAberto", "destinatario_id": "abc", "mensagem": "x"}) is False
        assert processar(db, "4-0", {"tipo": "ChamadoAberto", "destinatario_id": "2", "mensagem": "x" * 301}) is False
        assert servico.listar(db) == []


class RedisFalso:
    """Imita só o que o consumidor usa: uma fila com um lote de eventos."""

    def __init__(self, mensagens):
        self.mensagens, self.confirmados = list(mensagens), []

    def xreadgroup(self, grupo, consumidor, streams, count, block):
        lote, self.mensagens = self.mensagens[:count], self.mensagens[count:]
        return [(config.STREAM_EVENTOS, lote)] if lote else []

    def xack(self, stream, grupo, evento_id):
        self.confirmados.append(evento_id)


def test_ciclo_grava_e_so_depois_confirma(sessao):
    fila = RedisFalso([("1-0", EVENTO), ("2-0", {**EVENTO, "tipo": "ChamadoResolvido", "mensagem": "Resolvido"})])
    consumidor = Consumidor(sessao, cliente=fila)
    assert consumidor.ciclo(">") == 2
    assert fila.confirmados == ["1-0", "2-0"]
    with sessao() as db:
        assert [a.tipo for a in servico.listar(db, 2)] == ["ChamadoAberto", "ChamadoResolvido"]


def test_ciclo_confirma_evento_invalido_para_nao_travar_a_fila(sessao):
    fila = RedisFalso([("1-0", {"tipo": "Lixo"})])
    assert Consumidor(sessao, cliente=fila).ciclo(">") == 1
    assert fila.confirmados == ["1-0"]


def test_grupo_ja_existente_nao_e_erro(sessao):
    class Redis:
        def xgroup_create(self, *args, **kwargs):
            raise redis.ResponseError("BUSYGROUP Consumer Group name already exists")

    Consumidor(sessao, cliente=Redis())._garantir_grupo()  # não lança
