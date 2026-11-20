"""Configurações do serviço de Usuários, lidas das variáveis de ambiente."""
import os

from app.segredo import carregar_segredo

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./usuarios.db")

# Este serviço é o único que EMITE tokens, então é o único que pode criar o segredo.
JWT_SEGREDO = carregar_segredo(gerar=True)
JWT_ALGORITMO = "HS256"
JWT_EMISSOR = "helpdesk-ti"
TOKEN_MINUTOS = int(os.getenv("TOKEN_MINUTOS", "60"))

# Proteção contra tentativas de adivinhar senhas
LOGIN_MAX_FALHAS = int(os.getenv("LOGIN_MAX_FALHAS", "5"))
LOGIN_JANELA_SEGUNDOS = int(os.getenv("LOGIN_JANELA_SEGUNDOS", "300"))

TAMANHO_MAXIMO_REQUISICAO = 64 * 1024
DOCS_ATIVA = os.getenv("DOCS", "0") == "1"
