"""Carrega o segredo que assina os tokens JWT (nunca fica no código).

Ordem de busca:
1. variável de ambiente ``JWT_SEGREDO`` (vinda do ``.env``);
2. arquivo ``JWT_SEGREDO_ARQUIVO`` (por padrão ``/segredos/jwt_segredo``), num volume
   compartilhado só entre os serviços. Quem emite os tokens (serviço de Usuários)
   cria o arquivo na primeira subida, para ``docker compose up`` funcionar sem ajustes.
"""
import os
import secrets
from pathlib import Path

TAMANHO_MINIMO = 32


def carregar_segredo(gerar: bool = False) -> str:
    segredo = os.getenv("JWT_SEGREDO", "")
    if segredo:
        if len(segredo) < TAMANHO_MINIMO:
            raise RuntimeError(f"JWT_SEGREDO precisa ter pelo menos {TAMANHO_MINIMO} caracteres.")
        return segredo

    arquivo = Path(os.getenv("JWT_SEGREDO_ARQUIVO", "/segredos/jwt_segredo"))
    if arquivo.is_file():
        segredo = arquivo.read_text().strip()
        if len(segredo) >= TAMANHO_MINIMO:
            return segredo

    if gerar:
        segredo = secrets.token_urlsafe(48)
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        temporario = arquivo.with_suffix(".tmp")
        temporario.write_text(segredo)
        os.chmod(temporario, 0o600)
        temporario.replace(arquivo)  # troca atômica: ninguém lê o arquivo pela metade
        return segredo

    raise RuntimeError(
        "JWT_SEGREDO não definido. Defina no .env (mínimo 32 caracteres) ou suba o serviço de Usuários, "
        "que cria o segredo compartilhado."
    )
