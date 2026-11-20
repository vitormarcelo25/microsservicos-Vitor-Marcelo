"""Regras do serviço de Notificações."""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.notificacoes.modelos import Notificacao

TIPOS = {"ChamadoAberto", "ChamadoAtribuido", "ChamadoResolvido"}


def notificar(db: Session, tipo: str, destinatario_id: int, mensagem: str,
              evento_id: str | None = None, criada_em: datetime | None = None) -> Notificacao | None:
    """Registra um aviso. No mundo real, aqui seria enviado um e-mail ou SMS.

    Devolve None se o evento já tinha sido registrado (entrega repetida da fila).
    """
    aviso = Notificacao(
        evento_id=evento_id, tipo=tipo, destinatario_id=destinatario_id, mensagem=mensagem,
        criada_em=criada_em or datetime.now(),
    )
    db.add(aviso)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return None
    db.refresh(aviso)
    return aviso


def listar(db: Session, destinatario_id: int | None = None) -> list[Notificacao]:
    consulta = select(Notificacao).order_by(Notificacao.id)
    if destinatario_id:
        consulta = consulta.where(Notificacao.destinatario_id == destinatario_id)
    return list(db.scalars(consulta))
