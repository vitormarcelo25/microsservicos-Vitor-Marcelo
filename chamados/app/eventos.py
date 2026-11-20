"""Publicação de eventos de chamados em uma fila (Redis Streams).

No monólito, isto era `notificacoes.notificar(db, ...)`. Agora o serviço de Chamados só
**conta o que aconteceu** (ChamadoAberto, ChamadoAtribuido, ChamadoResolvido) e segue em frente;
quem quiser reagir (o serviço de Notificações) lê a fila no seu tempo.

Se o Redis estiver fora do ar, o chamado continua sendo salvo: o evento é perdido e fica no log.
(Para não perder nenhum evento, o próximo passo seria o padrão "outbox": gravar o evento no
próprio banco de chamados e publicá-lo depois.)
"""
import logging
from datetime import datetime, timezone

import redis

from app import config

log = logging.getLogger("chamados.eventos")

_redis = redis.Redis.from_url(
    config.REDIS_URL, decode_responses=True, socket_connect_timeout=1, socket_timeout=1,
)


def publicar(tipo: str, chamado_id: int, destinatario_id: int, mensagem: str) -> bool:
    """Põe o evento na fila. Devolve False (sem lançar erro) se não conseguiu."""
    evento = {
        "tipo": tipo,
        "chamado_id": chamado_id,
        "destinatario_id": destinatario_id,
        "mensagem": mensagem,
        "ocorrido_em": datetime.now(timezone.utc).isoformat(),
    }
    try:
        _redis.xadd(config.STREAM_EVENTOS, evento, maxlen=10_000, approximate=True)
        return True
    except redis.RedisError as erro:
        log.warning("Evento %s do chamado %s não foi publicado: %s", tipo, chamado_id, erro)
        return False
