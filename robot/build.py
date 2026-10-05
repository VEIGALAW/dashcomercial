"""Base do dash: puxar, validar, aplicar cadência, criptografar e publicar.

  python robot/build.py --pull     git pull + decripta data/leads.enc.json em private/leads.json
                                   (só sobrescreve se a versão publicada for mais nova que a local)
  python robot/build.py            valida, preenche datas pela cadência e gera data/leads.enc.json
  python robot/build.py --push     idem + commit + push

A versão publicada (criptografada) é a fonte da verdade: qualquer PC com a senha em
private/.senha consegue rodar o robô.
"""
import json, subprocess, sys
from datetime import date, datetime, timedelta, timezone

from lib import OUT, ROOT, SRC, decrypt, encrypt, load, save, senha

ESTAGIOS = ["engajado", "material", "agendando", "reuniao_marcada", "reuniao_feita",
            "proposta", "negociacao", "ganho", "nutrir", "perdido"]
FECHADOS = {"ganho", "perdido"}
PROJETOS = {"Rainmaker", "SINAPSE"}

# Cadência padrão (dias úteis depois do último toque) para o próximo contato quando ninguém marcou data.
# Mesma tabela do Playbook no dash.
CADENCIA = {
    "engajado": [1],                 # speed-to-lead: responder em até 1 dia útil
    "material": [2, 5, 10, 17, 30],  # sequência de follow-up depois do material
    "agendando": [2, 4, 7],
    "reuniao_marcada": [0],
    "reuniao_feita": [1, 3],         # recap em 24h, proposta em até 3 dias úteis
    "proposta": [2, 5, 10, 17],
    "negociacao": [3],
    "nutrir": [30],
}

git = lambda *a, **kw: subprocess.run(["git", *a], cwd=ROOT, **kw)


def add_uteis(d: date, n: int) -> date:
    while n > 0:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d


def proximo_toque(lead, hoje: date) -> str:
    base = date.fromisoformat(lead.get("ultimo_toque") or hoje.isoformat())
    passos = CADENCIA.get(lead["estagio"], [3])
    desde = lead.get("estagio_desde") or "0000"
    toques = sum(1 for h in lead.get("historico", []) if (h.get("data") or "") >= desde and h.get("autor") != "Lead")
    n = passos[min(max(toques - 1, 0), len(passos) - 1)]
    d = add_uteis(base, n)
    piso = hoje if hoje.weekday() < 5 else add_uteis(hoje, 1)
    return max(d, piso).isoformat()


def validar(db):
    erros, ids = [], set()
    for l in db["leads"]:
        lid = l.get("id")
        if not lid or lid in ids:
            erros.append(f"id ausente ou repetido: {lid}")
        ids.add(lid)
        if l.get("estagio") not in ESTAGIOS:
            erros.append(f"{lid}: estágio inválido {l.get('estagio')}")
        if l.get("projeto") not in PROJETOS:
            erros.append(f"{lid}: projeto inválido {l.get('projeto')}")
        for campo in ("proxima_data", "ultimo_toque", "estagio_desde"):
            v = l.get(campo)
            if v:
                try:
                    date.fromisoformat(v)
                except ValueError:
                    erros.append(f"{lid}: {campo} fora do formato AAAA-MM-DD: {v}")
        for campo in ("valor_honorarios", "credito_estimado"):
            v = l.get(campo)
            if v is not None and not isinstance(v, (int, float)):
                erros.append(f"{lid}: {campo} deve ser número (R$), veio {v!r}")
    if erros:
        sys.exit("leads.json inválido:\n  " + "\n  ".join(erros))


def trilha(l, hoje: str):
    """Registra cada mudança de estágio (para métricas de conversão e tempo por estágio)."""
    t = l.setdefault("trilha", [])
    if not t or t[-1]["estagio"] != l["estagio"]:
        # o robô grava estagio_desde com a data da mensagem; se não gravou, vale hoje
        desde = l.get("estagio_desde") or ""
        quando = desde if (not t or desde > t[-1]["data"]) else hoje
        t.append({"estagio": l["estagio"], "data": quando or hoje})
        l["estagio_desde"] = quando or hoje


def pull():
    git("pull", "--rebase", "--autostash", "-q", check=True)
    remoto = decrypt(json.loads(OUT.read_text(encoding="utf-8")), senha())
    local = load() if SRC.exists() else {}
    if local.get("publicado_em", "") > remoto.get("publicado_em", ""):
        print(f"local ({local['publicado_em']}) é mais novo que o publicado ({remoto.get('publicado_em')}): mantido o local")
        return
    save(remoto)
    print(f"base atualizada a partir do publicado em {remoto.get('publicado_em')} ({len(remoto['leads'])} leads)")


def build(push: bool):
    db = load()
    validar(db)
    hoje = date.today()
    preenchidos = 0
    for l in db["leads"]:
        l.setdefault("estagio_desde", l.get("ultimo_toque"))
        trilha(l, hoje.isoformat())
        if l["estagio"] in FECHADOS:
            l["proxima_data"] = None
        elif not l.get("proxima_data"):
            l["proxima_data"] = proximo_toque(l, hoje)
            l["proxima_auto"] = True
            preenchidos += 1
    db["publicado_em"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    save(db)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(encrypt(json.dumps(db, ensure_ascii=False).encode(), senha())), encoding="utf-8")
    print(f"{len(db['leads'])} leads publicados em {OUT.relative_to(ROOT)} ({preenchidos} datas pela cadência)")

    if push:
        git("add", "data/leads.enc.json", check=True)
        git("commit", "-q", "-m", f"dados: sync {datetime.now():%Y-%m-%d %H:%M}", check=True)
        if git("push", "-q").returncode:
            # alguém publicou no meio do caminho: rebase e tenta de novo (o arquivo é inteiro nosso)
            git("pull", "--rebase", "-X", "theirs", "-q", check=True)
            git("push", "-q", check=True)
        print("publicado no GitHub")


if __name__ == "__main__":
    pull() if "--pull" in sys.argv else build("--push" in sys.argv)
