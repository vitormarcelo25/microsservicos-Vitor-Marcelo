"""Cria chamados de exemplo quando o banco está vazio (só para aula).

Os chamados apontam para usuários e equipamentos pelos ids que os outros serviços criam
nos seus próprios dados de exemplo: 2 = Ana, 3 = Bruno, 4 = Carla (técnica); equipamentos 1 e 2.
Nenhum banco de outro serviço é consultado: são só números.
"""
from datetime import datetime

from sqlalchemy.orm import Session

from app.chamados import repositorio, servico
from app.chamados.modelos import Chamado

ANA, BRUNO, CARLA = 2, 3, 4


def carregar(db: Session) -> None:
    if repositorio.listar(db):
        return

    def novo(titulo, descricao, prioridade, solicitante_id, ativo_id=None) -> Chamado:
        agora = datetime.now()
        chamado = repositorio.salvar(db, Chamado(
            titulo=titulo, descricao=descricao, prioridade=prioridade, status="aberto",
            solicitante_id=solicitante_id, ativo_id=ativo_id, criado_em=agora,
            prazo_sla=servico.calcular_prazo(prioridade, agora),
        ))
        servico.avisar_abertura(chamado)
        return chamado

    c1 = novo("Computador não liga", "Apertei o botão e nada acontece.", "alta", ANA, ativo_id=1)
    novo("Impressora atolando papel", "Atola a cada 3 folhas.", "media", BRUNO, ativo_id=2)
    novo("Acesso ao sistema de RH", "Preciso de acesso para a nova estagiária.", "baixa", BRUNO)

    c1.tecnico_id, c1.status = CARLA, "em_atendimento"
    repositorio.salvar(db, c1)
    servico.avisar_atribuicao(c1)
