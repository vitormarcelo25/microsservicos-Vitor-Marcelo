"""Cria os usuários de exemplo quando o banco está vazio (só para aula).

Todos têm a mesma senha (SENHA_EXEMPLO). Em produção, rode com DADOS_EXEMPLO=0.
A ordem importa: os outros serviços criam chamados de exemplo apontando para estes ids
(1 admin, 2 ana, 3 bruno, 4 carla, 5 diego).
"""
import os

from sqlalchemy.orm import Session

from app.usuarios import servico as usuarios
from app.usuarios.esquemas import UsuarioCriar

SENHA = os.getenv("SENHA_EXEMPLO", "Helpdesk2026")


def carregar(db: Session) -> None:
    if usuarios.listar(db):
        return
    for nome, email, perfil in [
        ("Admin TI", "admin@empresa.com", "admin"),
        ("Ana Souza", "ana@empresa.com", "solicitante"),
        ("Bruno Lima", "bruno@empresa.com", "solicitante"),
        ("Carla Dias", "carla@empresa.com", "tecnico"),
        ("Diego Rocha", "diego@empresa.com", "tecnico"),
    ]:
        usuarios.criar(db, UsuarioCriar(nome=nome, email=email, perfil=perfil, senha=SENHA))
