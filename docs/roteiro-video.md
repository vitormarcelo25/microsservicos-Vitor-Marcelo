# Roteiro do vídeo (4 a 6 minutos)

Grave a tela com a sua voz; não precisa de edição. Publique como **não listado** no YouTube (ou no Drive com
acesso por link) e cole o link no topo do `README.md`. Fale com as suas palavras: o texto abaixo é só um guia.

Antes de gravar: `docker compose down -v` (para mostrar tudo subindo do zero) e deixe o terminal e o navegador visíveis.

| # | Tempo | O que mostrar | O que dizer |
|---|---|---|---|
| 1 | 0:00–0:50 | O diagrama Mermaid do README | Os 3 serviços + gateway; quem chama quem (HTTP) e o que é evento (Chamados → Redis → Notificações); um banco por serviço |
| 2 | 0:50–1:30 | `docker compose up --build`, depois (outro terminal) `docker compose ps` | Todos _healthy_; só o gateway tem porta publicada (`127.0.0.1:8000->8000`) |
| 3 | 1:30–2:50 | http://localhost:8000: entrar como **carla@empresa.com** (senha `Helpdesk2026`), abrir chamado com equipamento, atribuir, resolver, fechar | Tudo passa pelo gateway; no topo, os 4 serviços verdes; mostre a notificação chegando |
| 4 | 2:50–3:30 | `curl -i http://localhost:8000/chamados` (401); entrar como **ana@empresa.com** e tentar `GET /chamados/2` (404, é do Bruno) | Cada serviço confere o token; solicitante só vê o que é seu. Dá para usar `python scripts/teste_fumaca.py` |
| 5 | 3:30–4:00 | `docker volume ls` (ou `docker compose config --volumes`) | Um volume por banco; só o serviço dono monta cada um; as FKs entre serviços deixaram de existir |
| 6 | 4:00–5:00 | `docker compose stop inventario`; na tela: lista de chamados e usuários seguem OK, o Inventário fica vermelho; abrir chamado **com** equipamento → erro 503 claro; abrir **sem** equipamento funciona; `docker compose start inventario` | Timeout + disjuntor: falha rápida, sem travar |
| 7 | 5:00–5:40 | O README, seção "O que mudou em relação ao monólito" | Melhor: deploy independente, falha isolada. Mais difícil: rede, consistência sem FK, mais peças, perfil no token |
| 8 | 5:40–6:00 | `docker compose stop notificacoes`, abrir um chamado (funciona), `docker compose start notificacoes` (o aviso aparece); depois `cd chamados && pytest -q` | Eventos esperam na fila; testes rodando por serviço (bônus) |

Comandos úteis para o passo 4 (Git Bash, macOS ou Linux):

```bash
curl -i http://localhost:8000/chamados                       # sem token -> 401
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" \
  -d '{"email":"ana@empresa.com","senha":"Helpdesk2026"}' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
curl -i http://localhost:8000/chamados/2 -H "Authorization: Bearer $TOKEN"   # chamado do Bruno -> 404
```
