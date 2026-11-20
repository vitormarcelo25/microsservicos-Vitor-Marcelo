"""Configurações do serviço de Inventário, lidas das variáveis de ambiente."""
import os

from app.segredo import carregar_segredo

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./inventario.db")

# Só confere tokens: o segredo vem do .env (ou do volume compartilhado criado pelo serviço de Usuários)
JWT_SEGREDO = carregar_segredo()
JWT_ALGORITMO = "HS256"
JWT_EMISSOR = "helpdesk-ti"

TAMANHO_MAXIMO_REQUISICAO = 64 * 1024
DOCS_ATIVA = os.getenv("DOCS", "0") == "1"
