"""Lê os eventos de chamados da fila (Redis Streams) e grava as notificações.

Garantias:
* **Se este serviço cair**, os chamados continuam sendo abertos; os eventos esperam na fila
  e são lidos quando ele voltar (o grupo de consumidores lembra até onde já foi lido).
* **Se o Redis cair** (ou der erro ao gravar), o consumidor tenta de novo a cada poucos segundos, sem derrubar a API.
* **Entrega repetida** não duplica avisos (o id do evento é único no banco).
* **Evento inválido** é descartado com um aviso no log, para não travar a fila.
"""
import logging
import threading
from datetime import datetime

import redis
from sqlalchemy.orm import Session, sessionmaker

from app import config
from app.notificacoes import servico

log = logging.getLogger("notificacoes.consumidor")


def evento_valido(campos: dict) -> bool:
    return (
        campos.get("tipo") in servico.TIPOS
        and str(campos.get("destinatario_id", "")).isdigit()
        and 0 < len(campos.get("mensagem", "")) <= 300
    )


def _data(texto: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(texto).astimezone().replace(tzinfo=None) if texto else None
    except ValueError:
        return None


def processar(db: Session, evento_id: str, campos: dict) -> bool:
    """Grava o aviso do evento. Devolve False se o evento era inválido (e foi descartado)."""
    if not evento_valido(campos):
        log.warning("Evento %s descartado (formato inválido): %s", evento_id, campos)
        return False
    servico.notificar(
        db, campos["tipo"], int(campos["destinatario_id"]), campos["mensagem"],
        evento_id=evento_id, criada_em=_data(campos.get("ocorrido_em")),
    )
    return True


class Consumidor(threading.Thread):
    def __init__(self, sessao: sessionmaker, cliente: redis.Redis | None = None):
        super().__init__(name="consumidor-de-eventos", daemon=True)
        self._sessao = sessao
        self._redis = cliente or redis.Redis.from_url(config.REDIS_URL, decode_responses=True, socket_connect_timeout=2, socket_timeout=10)
        self._parar = threading.Event()

    def parar(self) -> None:
        self._parar.set()

    def _garantir_grupo(self) -> None:
        try:
            # "0" = o grupo começa do primeiro evento da fila (nada que veio antes se perde)
            self._redis.xgroup_create(config.STREAM_EVENTOS, config.GRUPO, id="0", mkstream=True)
        except redis.ResponseError as erro:
            if "BUSYGROUP" not in str(erro):  # BUSYGROUP = o grupo já existe, tudo certo
                raise

    def ciclo(self, ponto: str = ">") -> int:
        """Lê um lote e grava os avisos. `>` = eventos novos; `0` = pendentes de uma leitura que não terminou."""
        resposta = self._redis.xreadgroup(
            config.GRUPO, config.CONSUMIDOR, {config.STREAM_EVENTOS: ponto}, count=20, block=2000,
        )
        lidos = 0
        for _, mensagens in resposta or []:
            for evento_id, campos in mensagens:
                with self._sessao() as db:
                    processar(db, evento_id, campos)
                self._redis.xack(config.STREAM_EVENTOS, config.GRUPO, evento_id)  # só confirma depois de gravar
                lidos += 1
        return lidos

    def run(self) -> None:
        while not self._parar.is_set():
            try:
                self._garantir_grupo()
                while self.ciclo("0"):  # primeiro termina o que ficou pendente de antes
                    pass
                while not self._parar.is_set():
                    self.ciclo(">")
            except Exception as erro:  # Redis fora do ar ou erro ao gravar: nunca derruba o serviço
                log.warning("Consumidor com problema (%s: %s). Nova tentativa em 3 s.", type(erro).__name__, erro)
                self._parar.wait(3)
