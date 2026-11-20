"""Domínio do serviço de Chamados: abrir, atribuir, acompanhar e resolver chamados.

Este serviço não conhece os bancos de usuários e de inventário: ele chama os outros
serviços por HTTP (`app/clientes.py`) e avisa o resto do sistema por eventos (`app/eventos.py`).
"""
