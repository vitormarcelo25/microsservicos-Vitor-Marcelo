"""Dependências do FastAPI para exigir login e perfil, a partir do token."""
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth import tokens

esquema = HTTPBearer(auto_error=False)

NAO_AUTENTICADO = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Faça login para continuar.",
    headers={"WWW-Authenticate": "Bearer"},
)


@dataclass(frozen=True)
class Pessoa:
    """Quem está fazendo a requisição, segundo o token.

    O token também é guardado: serviços que chamam outros serviços o repassam adiante.
    """
    id: int
    perfil: str
    token: str


def usuario_atual(credenciais: HTTPAuthorizationCredentials | None = Depends(esquema)) -> Pessoa:
    if credenciais is None or credenciais.scheme.lower() != "bearer":
        raise NAO_AUTENTICADO
    try:
        usuario_id, perfil = tokens.ler(credenciais.credentials)
    except tokens.TokenInvalido:
        raise NAO_AUTENTICADO
    return Pessoa(id=usuario_id, perfil=perfil, token=credenciais.credentials)


def exigir_perfil(*perfis: str):
    """Libera a rota só para os perfis informados."""
    def verificar(usuario: Pessoa = Depends(usuario_atual)) -> Pessoa:
        if usuario.perfil not in perfis:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Você não tem permissão para esta ação.")
        return usuario
    return verificar
