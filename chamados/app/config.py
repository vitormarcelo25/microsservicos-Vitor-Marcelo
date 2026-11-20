"""Configurações do serviço de Chamados, lidas das variáveis de ambiente."""
import os

from app.segredo import carregar_segredo

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./chamados.db")

# Só confere tokens: o segredo vem do .env (ou do volume compartilhado criado pelo serviço de Usuários)
JWT_SEGREDO = carregar_segredo()
JWT_ALGORITMO = "HS256"
JWT_EMISSOR = "helpdesk-ti"

# Endereços dos outros serviços (dentro do Docker Compose, o nome do serviço é o endereço)
USUARIOS_URL = os.getenv("USUARIOS_URL", "http://usuarios:8000").rstrip("/")
INVENTARIO_URL = os.getenv("INVENTARIO_URL", "http://inventario:8000").rstrip("/")

# Tempo limite das chamadas entre serviços (segundos): melhor falhar rápido do que travar
CLIENTE_TIMEOUT = float(os.getenv("CLIENTE_TIMEOUT", "2"))
CLIENTE_TIMEOUT_CONEXAO = float(os.getenv("CLIENTE_TIMEOUT_CONEXAO", "1"))

# Disjuntor: depois de N falhas seguidas, para de tentar por alguns segundos
DISJUNTOR_FALHAS = int(os.getenv("DISJUNTOR_FALHAS", "3"))
DISJUNTOR_ESPERA = float(os.getenv("DISJUNTOR_ESPERA", "10"))

# Fila de eventos (Redis Streams)
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
STREAM_EVENTOS = os.getenv("STREAM_EVENTOS", "helpdesk.eventos")

TAMANHO_MAXIMO_REQUISICAO = 64 * 1024
DOCS_ATIVA = os.getenv("DOCS", "0") == "1"
