"""Chamadas HTTP do serviço de Chamados aos serviços de Usuários e de Inventário.

No monólito, isto era `usuarios.obter_tecnico(db, id)` e `inventario.obter(db, id)`:
chamadas de função que nunca falhavam por causa da rede. Agora existe a rede no meio, então:

* toda chamada tem **timeout** (não trava esperando);
* o **token da pessoa é repassado** (o outro serviço confere de novo);
* um **disjuntor** (circuit breaker) para de tentar por alguns segundos depois de falhas
  seguidas, para responder rápido em vez de esperar o timeout a cada requisição;
* se o outro serviço não responde, o erro vira `ServicoIndisponivel` (a API responde 503).
"""
import logging
import threading
import time

import httpx

from app import config
from app.erros import NaoEncontrado, RegraDeNegocio, ServicoIndisponivel

log = logging.getLogger("chamados.clientes")


class Disjuntor:
    """Fechado = deixa passar. Aberto = recusa de imediato até acabar a espera."""

    def __init__(self, falhas_max: int, espera: float):
        self.falhas_max = falhas_max
        self.espera = espera
        self._falhas = 0
        self._aberto_ate: float | None = None
        self._trava = threading.Lock()

    @property
    def aberto(self) -> bool:
        with self._trava:
            return self._aberto_ate is not None and time.monotonic() < self._aberto_ate

    def permite(self) -> bool:
        with self._trava:
            if self._aberto_ate is None:
                return True
            if time.monotonic() < self._aberto_ate:
                return False
            # Acabou a espera: libera uma tentativa. Se falhar de novo, reabre na hora.
            self._aberto_ate = None
            self._falhas = self.falhas_max - 1
            return True

    def sucesso(self) -> None:
        with self._trava:
            self._falhas = 0
            self._aberto_ate = None

    def falha(self) -> None:
        with self._trava:
            self._falhas += 1
            if self._falhas >= self.falhas_max:
                self._aberto_ate = time.monotonic() + self.espera


_http = httpx.Client(timeout=httpx.Timeout(config.CLIENTE_TIMEOUT, connect=config.CLIENTE_TIMEOUT_CONEXAO))
_disjuntores = {
    "Usuários": Disjuntor(config.DISJUNTOR_FALHAS, config.DISJUNTOR_ESPERA),
    "Inventário": Disjuntor(config.DISJUNTOR_FALHAS, config.DISJUNTOR_ESPERA),
}


def reiniciar_disjuntores() -> None:
    for d in _disjuntores.values():
        d.sucesso()


def _consultar(servico: str, url: str, token: str) -> httpx.Response:
    """GET em outro serviço, repassando o token. Só devolve respostas 2xx e 404."""
    disjuntor = _disjuntores[servico]
    if not disjuntor.permite():
        raise ServicoIndisponivel(servico)
    try:
        resposta = _http.get(url, headers={"Authorization": f"Bearer {token}"})
    except httpx.HTTPError as erro:  # timeout, conexão recusada, nome não encontrado...
        disjuntor.falha()
        log.warning("Serviço de %s sem resposta (%s): %s", servico, type(erro).__name__, url)
        raise ServicoIndisponivel(servico) from erro

    if resposta.status_code >= 500:
        disjuntor.falha()
        log.warning("Serviço de %s respondeu %s: %s", servico, resposta.status_code, url)
        raise ServicoIndisponivel(servico)
    disjuntor.sucesso()  # o serviço respondeu: está no ar, mesmo que a resposta seja um erro de negócio
    if resposta.status_code in (401, 403):
        # Não deveria acontecer (repassamos um token válido): provável segredo diferente entre serviços
        log.error("Serviço de %s recusou o token repassado (%s): %s", servico, resposta.status_code, url)
        raise ServicoIndisponivel(servico)
    return resposta


def obter_ativo(ativo_id: int, token: str) -> dict:
    resposta = _consultar("Inventário", f"{config.INVENTARIO_URL}/ativos/{ativo_id}", token)
    if resposta.status_code == 404:
        raise NaoEncontrado(f"Ativo {ativo_id} não encontrado.")
    if resposta.status_code != 200:
        raise ServicoIndisponivel("Inventário")
    return resposta.json()


def obter_tecnico(usuario_id: int, token: str) -> dict:
    resposta = _consultar("Usuários", f"{config.USUARIOS_URL}/usuarios/{usuario_id}", token)
    if resposta.status_code == 404:
        raise NaoEncontrado(f"Usuário {usuario_id} não encontrado.")
    if resposta.status_code != 200:
        raise ServicoIndisponivel("Usuários")
    usuario = resposta.json()
    if usuario.get("perfil") != "tecnico":
        raise RegraDeNegocio(f"Usuário {usuario_id} não é técnico.")
    return usuario
