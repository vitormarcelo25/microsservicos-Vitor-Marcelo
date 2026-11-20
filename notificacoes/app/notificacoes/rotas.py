from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencias import Pessoa, usuario_atual
from app.database import get_db
from app.notificacoes import servico
from app.notificacoes.esquemas import NotificacaoSaida

router = APIRouter(prefix="/notificacoes", tags=["Notificações"])


@router.get("", response_model=list[NotificacaoSaida])
def minhas_notificacoes(usuario: Pessoa = Depends(usuario_atual), db: Session = Depends(get_db)):
    """Cada usuário vê só as próprias notificações."""
    return servico.listar(db, usuario.id)
