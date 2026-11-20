"""Configurações do serviço de Notificações, lidas das variáveis de ambiente."""
import os

from app.segredo import carregar_segredo

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./notificacoes.db")

# Só confere tokens: o segredo vem do .env (ou do volume compartilhado criado pelo serviço de Usuários)
JWT_SEGREDO = carregar_segredo()
JWT_ALGORITMO = "HS256"
JWT_EMISSOR = "helpdesk-ti"

# Fila de eventos (Redis Streams). O grupo de consumidores guarda "até onde já li":
# se este serviço cair, os eventos esperam na fila e são lidos quando ele voltar.
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
STREAM_EVENTOS = os.getenv("STREAM_EVENTOS", "helpdesk.eventos")
GRUPO = os.getenv("GRUPO_CONSUMIDORES", "notificacoes")
CONSUMIDOR = os.getenv("NOME_CONSUMIDOR", "notificacoes-1")
CONSUMIDOR_ATIVO = os.getenv("CONSUMIDOR_ATIVO", "1") == "1"

TAMANHO_MAXIMO_REQUISICAO = 64 * 1024
DOCS_ATIVA = os.getenv("DOCS", "0") == "1"
