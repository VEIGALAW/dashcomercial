"""Valida private/leads.json, preenche próximas datas pela cadência e publica data/leads.enc.json.

Uso:  python robot/build.py            (só gera o arquivo criptografado)
      python robot/build.py --push     (gera, commita e dá push)

O arquivo publicado é AES-256-GCM com chave derivada da senha do time (PBKDF2-SHA256).
A senha fica em private/.senha, que nunca vai para o GitHub.
"""
import base64, json, os, subprocess, sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "private" / "leads.json"
KEY = ROOT / "private" / ".senha"
OUT = ROOT / "data" / "leads.enc.json"
ITER = 310_000

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
    "reuniao_marcada": [0],          # confirmar na véspera (tratado na UI)
    "reuniao_feita": [1, 3],         # recap em 24h, proposta em até 3 dias úteis
    "proposta": [2, 5, 10, 17],
    "negociacao": [3],
    "nutrir": [30],
}


def add_uteis(d: date, n: int) -> date:
    while n > 0:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d


def proximo_toque(lead, hoje: date) -> str:
    base = date.fromisoformat(lead.get("ultimo_toque") or hoje.isoformat())
    passos = CADENCIA.get(lead["estagio"], [3])
    toques_desde = sum(1 for h in lead.get("historico", [])
                       if h.get("data") and h["data"] >= lead.get("estagio_desde", "0000") and h.get("autor") != "Lead")
    n = passos[min(max(toques_desde - 1, 0), len(passos) - 1)]
    d = add_uteis(base, n)
    return max(d, hoje if hoje.weekday() < 5 else add_uteis(hoje, 1)).isoformat()


def validar(db):
    erros = []
    ids = set()
    for l in db["leads"]:
        lid = l.get("id")
        if not lid or lid in ids:
            erros.append(f"id ausente ou repetido: {lid}")
        ids.add(lid)
        if l.get("estagio") not in ESTAGIOS:
            erros.append(f"{lid}: estágio inválido {l.get('estagio')}")
        if l.get("projeto") not in PROJETOS:
            erros.append(f"{lid}: projeto inválido {l.get('projeto')}")
        for campo in ("proxima_data", "ultimo_toque"):
            v = l.get(campo)
            if v:
                try:
                    date.fromisoformat(v)
                except ValueError:
                    erros.append(f"{lid}: {campo} fora do formato AAAA-MM-DD: {v}")
    if erros:
        sys.exit("leads.json inválido:\n  " + "\n  ".join(erros))


def criptografar(payload: bytes, senha: str) -> dict:
    salt, iv = os.urandom(16), os.urandom(12)
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITER)
    chave = kdf.derive(senha.encode())
    ct = AESGCM(chave).encrypt(iv, payload, None)
    b64 = lambda b: base64.b64encode(b).decode()
    return {"v": 1, "kdf": "PBKDF2-SHA256", "iter": ITER, "salt": b64(salt), "iv": b64(iv), "ct": b64(ct)}


def main():
    db = json.loads(SRC.read_text(encoding="utf-8"))
    validar(db)
    hoje = date.today()
    preenchidos = 0
    for l in db["leads"]:
        l.setdefault("estagio_desde", l.get("ultimo_toque"))
        if l["estagio"] in FECHADOS:
            l["proxima_data"] = None
        elif not l.get("proxima_data"):
            l["proxima_data"] = proximo_toque(l, hoje)
            l["proxima_auto"] = True
            preenchidos += 1
    db["publicado_em"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    SRC.write_text(json.dumps(db, ensure_ascii=False, indent=1), encoding="utf-8")

    senha = KEY.read_text(encoding="utf-8").strip()
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(criptografar(json.dumps(db, ensure_ascii=False).encode(), senha)), encoding="utf-8")
    print(f"{len(db['leads'])} leads publicados em {OUT.relative_to(ROOT)} ({preenchidos} datas pela cadência)")

    if "--push" in sys.argv:
        msg = f"dados: sync {datetime.now():%Y-%m-%d %H:%M}"
        run = lambda *a: subprocess.run(a, cwd=ROOT, check=True)
        run("git", "add", "data/leads.enc.json")
        if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode:
            run("git", "commit", "-m", msg)
            run("git", "push")
        else:
            print("sem mudanças para publicar")


if __name__ == "__main__":
    main()
