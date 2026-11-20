from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Notificacao(Base):
    __tablename__ = "notificacoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Id do evento na fila. Único: se o mesmo evento chegar duas vezes, o aviso não é duplicado.
    evento_id: Mapped[str | None] = mapped_column(String(40), unique=True, nullable=True)
    tipo: Mapped[str] = mapped_column(String(40))
    destinatario_id: Mapped[int]  # vive no serviço de Usuários: sem chave estrangeira
    mensagem: Mapped[str] = mapped_column(String(300))
    criada_em: Mapped[datetime] = mapped_column(DateTime)
