# Segurança

A versão em microsserviços mantém todas as proteções do monólito e adiciona as que só fazem
sentido quando existe uma rede entre os serviços.

## O que está protegido

| Risco | Proteção |
|---|---|
| Acesso sem login | **Todo serviço** confere o token JWT (`Authorization: Bearer ...`) antes de responder; o gateway não é a única barreira. Só `/auth/login`, `/saude` e a tela são públicos. |
| Segredo no código | `JWT_SEGREDO` vem do `.env` (fora do Git) ou de um volume compartilhado só entre os serviços, criado pelo serviço de Usuários na primeira subida. Não existe segredo em nenhum arquivo versionado. |
| Token falsificado | HS256 com algoritmo, emissor e campos obrigatórios fixos (`exp`, `iat`, `sub`, `iss`, `perfil`); tokens `alg: none`, vencidos, adulterados, de outro segredo ou com perfil inventado são recusados **em cada serviço** (há testes em todos). |
| Senhas vazadas do banco | Hash **scrypt** com sal aleatório; só o serviço de Usuários tem acesso a elas. |
| Adivinhar senhas | Bloqueio após 5 tentativas erradas, por e-mail **e endereço real do cliente** (o gateway informa o endereço em `X-Forwarded-For`, descartando o que o cliente enviar). |
| Ver ou mexer no que não é seu | Permissões por perfil mantidas: o solicitante só vê os próprios chamados e notificações (404 para o dos outros); só técnicos e administradores atribuem e resolvem; só administradores criam usuários. O perfil vem do token assinado. |
| Agir em nome de outra pessoa | O solicitante e o autor do comentário vêm do token, não do corpo. Campos extras são recusados (422). |
| Chamar outro serviço sem permissão | O serviço de Chamados **repassa o token da própria pessoa** ao consultar Usuários e Inventário; nunca usa uma credencial "de sistema" mais poderosa. |
| Serviços e bancos expostos | **Só o gateway publica porta** (`127.0.0.1:8000`). Serviços, Redis e bancos ficam numa rede Docker `internal`: sem acesso de fora e sem saída para a internet. Cada banco é um volume montado só pelo seu serviço. |
| Falha em cascata | Timeout em toda chamada entre serviços, disjuntor (circuit breaker) e respostas 503/504 claras, sem vazar detalhes internos. |
| Encaminhamento malicioso | O gateway só repassa cabeçalhos de uma lista permitida, recusa `..` no caminho e só conhece as rotas de cada serviço. |
| XSS, clickjacking, tamanho de corpo, SQL injection | Iguais ao monólito: CSP e demais cabeçalhos no gateway, limite de 64 KB em gateway e serviços, SQLAlchemy com parâmetros. |
| Contêineres | Usuário sem privilégios, sistema de arquivos somente leitura, `cap_drop: ALL`, `no-new-privileges`. |
| Dependências vulneráveis | Versões fixas, `pip-audit` por serviço no GitHub Actions e Dependabot semanal. |

## Limitações conhecidas (decisões conscientes)

- **O perfil fica no token** (válido por 60 min). Se alguém for rebaixado ou desativado, os serviços que só
  conferem o token (Inventário, Chamados, Notificações) só percebem quando ele expirar. No monólito, cada
  requisição consultava o banco. Alternativas: token curto + refresh, ou consultar o serviço de Usuários a cada chamada.
- A comunicação interna é HTTP sem criptografia. Em produção, use mTLS (ou uma malha de serviço) e HTTPS na frente do gateway.
- O segredo JWT é simétrico: todo serviço que o conhece poderia emitir tokens. Com chave assimétrica (RS256),
  só Usuários guardaria a chave privada.
- Se o Redis cair, os eventos publicados nesse intervalo são perdidos (o chamado é salvo mesmo assim).
  O padrão *outbox* resolveria isso.
- As contas de exemplo têm senha conhecida: em produção, `DADOS_EXEMPLO=0`.

## Antes de usar em produção

- Defina `JWT_SEGREDO` com pelo menos 32 caracteres aleatórios e rode com `DADOS_EXEMPLO=0`.
- Coloque o gateway atrás de HTTPS.
- Troque o SQLite por PostgreSQL (um por serviço) com backup, e o Redis por uma instância gerenciada.

## Como relatar um problema

Encontrou uma falha? Não abra uma issue pública: envie os detalhes diretamente ao autor.
