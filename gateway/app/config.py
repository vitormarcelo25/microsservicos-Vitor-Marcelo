"""Configurações do API Gateway, lidas das variáveis de ambiente.

O gateway NÃO conhece o segredo dos tokens: quem confere o token é cada serviço.
Ele só encaminha a requisição (com o cabeçalho Authorization) para o serviço certo.
"""
import os

SERVICOS = {
    "usuarios": os.getenv("USUARIOS_URL", "http://usuarios:8000").rstrip("/"),
    "inventario": os.getenv("INVENTARIO_URL", "http://inventario:8000").rstrip("/"),
    "chamados": os.getenv("CHAMADOS_URL", "http://chamados:8000").rstrip("/"),
    "notificacoes": os.getenv("NOTIFICACOES_URL", "http://notificacoes:8000").rstrip("/"),
}

# Primeiro pedaço do caminho -> serviço que cuida dele
ROTAS = {
    "auth": "usuarios",
    "usuarios": "usuarios",
    "ativos": "inventario",
    "chamados": "chamados",
    "notificacoes": "notificacoes",
}

NOMES = {"usuarios": "Usuários", "inventario": "Inventário", "chamados": "Chamados", "notificacoes": "Notificações"}

# Tempo limite ao falar com um serviço (segundos)
TIMEOUT = float(os.getenv("GATEWAY_TIMEOUT", "8"))
TIMEOUT_CONEXAO = float(os.getenv("GATEWAY_TIMEOUT_CONEXAO", "2"))
TIMEOUT_SAUDE = float(os.getenv("GATEWAY_TIMEOUT_SAUDE", "1.5"))

TAMANHO_MAXIMO_REQUISICAO = 64 * 1024
