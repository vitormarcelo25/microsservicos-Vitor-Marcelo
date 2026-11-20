# Roteiro do vídeo (4 a 6 minutos): o que eu modifiquei e melhorei

O professor pediu um vídeo **narrado**, mostrando o que eu mudei em relação ao monólito e o que melhorou.
Então a ideia é sempre: **mostrar na tela → dizer "antes era assim, agora é assim, e por quê"**.

Grave a tela com a sua voz; não precisa de edição. Publique como **não listado** no YouTube (ou no Drive com
acesso por link) e cole o link no topo do `README.md`. Fale com as suas palavras: o texto abaixo é só um guia.

**Antes de gravar:** `docker compose down -v`, terminal e navegador visíveis, README aberto na seção
"O que mudou em relação ao monólito" e o repositório do monólito aberto numa aba (para comparar).

## Roteiro

| # | Tempo | O que mostrar | O que dizer (antes → agora → por quê) |
|---|---|---|---|
| 1 | 0:00–0:30 | Pasta do projeto + diagrama Mermaid do README | Apresente-se. **Antes:** um programa só, um banco só. **Agora:** gateway + 4 serviços (Usuários, Inventário, Chamados, Notificações), cada um com seu Dockerfile, testes e banco. |
| 2 | 0:30–1:10 | `git log --oneline` | Mostre que a separação foi **incremental**: Usuários → Inventário → Chamados → Notificações → Gateway → compose. Explique por que começou por Usuários (não depende de ninguém). |
| 3 | 1:10–1:50 | `docker compose up --build`, depois `docker compose ps` | Tudo sobe com um comando, sem configurar nada (o segredo JWT é criado sozinho). Só o gateway publica porta (`127.0.0.1:8000`); os outros ficam na rede interna. |
| 4 | 1:50–2:40 | Abra `chamados/app/clientes.py` e compare com o trecho `# vira chamada HTTP` do monólito | **Mudança principal:** onde o monólito chamava uma função, agora é uma chamada HTTP com timeout (2 s) e disjuntor (3 falhas → abre por 10 s). Mostre o código. |
| 5 | 2:40–3:20 | Abra `chamados/app/eventos.py` e o `docker-compose.yml` (volumes) | **Banco por serviço:** as FKs entre serviços viraram números sem FK, e a consistência passou a ser do código. **Notificações por evento** (Redis Streams): o chamado não espera o aviso. |
| 6 | 3:20–4:20 | http://localhost:8000, entrar como **carla@empresa.com** (`Helpdesk2026`): abrir chamado com equipamento, atribuir, resolver, fechar | Funciona igual ao monólito (mesmas regras de SLA e status). Mostre a **melhoria na tela**: os 4 serviços verdes no topo e a notificação chegando. |
| 7 | 4:20–5:10 | `docker compose stop inventario`: usuários e chamados seguem OK; abrir chamado **com** equipamento → 503 claro; **sem** equipamento funciona; `docker compose start inventario` | **Melhoria de resiliência:** no monólito, um problema derrubava tudo. Agora a falha é isolada e rápida (não trava). |
| 8 | 5:10–5:40 | `curl -i http://localhost:8000/chamados` (401); como **ana@empresa.com**, `GET /chamados/2` (404, é do Bruno); depois `python scripts/teste_fumaca.py` | **Segurança em camadas:** cada serviço confere o token sozinho, o gateway não é a única barreira; o token da pessoa é repassado entre serviços. |
| 9 | 5:40–6:00 | `cd chamados && pytest -q` e o README ("Ficou melhor / Ficou mais difícil") | Testes por serviço + CI. Feche com o **trade-off honesto**: ganhei deploy independente e falha isolada; perdi simplicidade (rede, consistência sem FK, mais peças). |

Se passar de 6 minutos, corte o passo 8 (deixe só o `teste_fumaca.py` rodando) ou encurte o passo 2.

## Checklist do que dizer (é isso que o professor quer ouvir)

- [ ] O que era o monólito e quais pontos marcados com `# vira chamada HTTP` / `# vira evento` eu transformei.
- [ ] Por que escolhi **HTTP** para Usuários/Inventário e **evento** para Notificações.
- [ ] Como funciona o **timeout + disjuntor** e o que o usuário vê quando um serviço cai.
- [ ] O que mudou no banco (um por serviço, sem FK entre serviços) e o custo disso.
- [ ] O que melhorou **e** o que ficou mais difícil (os dois lados).
- [ ] O que eu faria depois (ex.: padrão *outbox*, PostgreSQL por serviço, RS256).

## Comandos úteis para o passo 8 (Git Bash, macOS ou Linux)

```bash
curl -i http://localhost:8000/chamados                       # sem token -> 401
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" \
  -d '{"email":"ana@empresa.com","senha":"Helpdesk2026"}' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
curl -i http://localhost:8000/chamados/2 -H "Authorization: Bearer $TOKEN"   # chamado do Bruno -> 404
```

No PowerShell, rode o `teste_fumaca.py` no lugar do `curl` (ele cobre o mesmo fluxo).
