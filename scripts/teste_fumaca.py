"""Teste de fumaça: percorre o sistema inteiro pelo gateway (precisa do `docker compose up` rodando).

Uso:  python scripts/teste_fumaca.py [http://localhost:8000]
Só usa a biblioteca padrão do Python. Termina com código 1 se alguma verificação falhar.
"""
import json
import sys
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
SENHA = "Helpdesk2026"
falhas = 0


def chamar(metodo, caminho, corpo=None, token=None):
    cab = {"Content-Type": "application/json"}
    if token:
        cab["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE + caminho, method=metodo, headers=cab, data=json.dumps(corpo).encode() if corpo is not None else None)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def verificar(descricao, obtido, esperado):
    global falhas
    ok = obtido == esperado
    falhas += not ok
    print(("  ok  " if ok else " ERRO ") + descricao + ("" if ok else f"  (esperado {esperado}, veio {obtido})"))


def entrar(email):
    status, dados = chamar("POST", "/auth/login", {"email": email, "senha": SENHA})
    verificar(f"login de {email}", status, 200)
    return dados.get("access_token")


print("Serviços:")
status, saude = chamar("GET", "/saude")
verificar("gateway responde /saude", status, 200)
verificar("todos os serviços no ar", saude.get("status"), "ok")

print("Segurança:")
verificar("chamados sem token -> 401", chamar("GET", "/chamados")[0], 401)
verificar("equipamentos sem token -> 401", chamar("GET", "/ativos")[0], 401)
verificar("token falso -> 401", chamar("GET", "/chamados", token="falso")[0], 401)

carla, ana = entrar("carla@empresa.com"), entrar("ana@empresa.com")
status, lista_ana = chamar("GET", "/chamados", token=ana)
verificar("Ana só vê os próprios chamados", {c["solicitante_id"] for c in lista_ana}, {lista_ana[0]["solicitante_id"]})
verificar("Ana não vê o chamado do Bruno (#2) -> 404", chamar("GET", "/chamados/2", token=ana)[0], 404)
verificar("Ana não atribui chamados -> 403", chamar("PATCH", "/chamados/1/atribuir", {"tecnico_id": 4}, ana)[0], 403)

print("Fluxo completo (técnica Carla):")
status, ativos = chamar("GET", "/ativos", token=carla)
verificar("lista de equipamentos", status, 200)
status, chamado = chamar("POST", "/chamados", {"titulo": "Teste de fumaça", "descricao": "Criado pelo script", "prioridade": "alta", "ativo_id": ativos[0]["id"]}, carla)
verificar("abrir chamado com equipamento", status, 201)
cid = chamado.get("id")
status, c = chamar("PATCH", f"/chamados/{cid}/atribuir", {"tecnico_id": 4}, carla)
verificar("atribuir -> em atendimento", (status, c.get("status")), (200, "em_atendimento"))
status, c = chamar("PATCH", f"/chamados/{cid}/status", {"status": "resolvido"}, carla)
verificar("resolver", (status, c.get("status")), (200, "resolvido"))
status, c = chamar("PATCH", f"/chamados/{cid}/status", {"status": "fechado"}, carla)
verificar("fechar", (status, c.get("status")), (200, "fechado"))
status, painel = chamar("GET", "/chamados/painel", token=carla)
verificar("painel", status, 200)

print("Falha do Inventário (rode `docker compose stop inventario` antes para ver o 503):")
status, _ = chamar("GET", "/saude")
status, resp = chamar("POST", "/chamados", {"titulo": "Com equipamento", "descricao": "Teste", "prioridade": "baixa", "ativo_id": 1}, carla)
print(f"  info  abrir com equipamento -> {status} {resp.get('detail', '')}")

print("\nRESULTADO:", "tudo certo" if not falhas else f"{falhas} verificação(ões) falharam")
sys.exit(1 if falhas else 0)
