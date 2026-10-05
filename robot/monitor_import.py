"""Traz para o dash as respostas positivas que o Rainmaker e o SINAPSE gravam no Monitor de Leads.

  python robot/monitor_import.py           mostra o que entraria (não grava)
  python robot/monitor_import.py --apply   grava em private/leads.json

Lê a aba "Monitor de Leads" (leads quentes). Lead que já existe no dash não é duplicado.
Leads da aba "Reabordar" não entram (são recusas/neutros).
"""
import re, sys
from datetime import date, datetime
from pathlib import Path

import openpyxl
from lib import find_lead, load, norm, save, slug

MONITOR = Path(r"C:\Users\RafaelCanesso\Desktop\Monitor_Leads_Rainmaker_NEW.xlsx")
DESDE = "2026-09-01"  # respostas mais antigas já foram triadas no levantamento de 05/10


def data_br(v):
    if isinstance(v, datetime):
        return v.date().isoformat()
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", str(v or ""))
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None


def main(apply: bool):
    db = load()
    vistos = set(db.setdefault("monitor_importados", []))
    wb = openpyxl.load_workbook(MONITOR, read_only=True, data_only=True)
    rows = list(wb["Monitor de Leads"].iter_rows(values_only=True))
    hdr = next(i for i, r in enumerate(rows) if r and r[0] == "Temperatura")
    novos = []
    for r in rows[hdr + 1:]:
        temp, nome, empresa, cargo, canal, quando, resp = (list(r) + [None] * 7)[:7]
        if not nome or not empresa:
            continue
        chave = norm(f"{empresa} {nome}")
        d = data_br(quando)
        if chave in vistos or not d or d < DESDE:
            continue
        resp = str(resp or "")
        emails = re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", resp)
        existente = find_lead(db, empresa, nome, emails[0] if emails else "")
        vistos.add(chave)
        if existente:
            continue
        sinapse = "[SINAPSE]" in resp
        lead = {
            "id": slug(f"{empresa}-{nome}"), "nome": str(nome), "empresa": str(empresa), "cargo": str(cargo or ""),
            "projeto": "SINAPSE" if sinapse else "Rainmaker", "subfrente": "",
            "estagio": "engajado", "responsavel": "Sem dono", "repassar": False,
            "email": emails, "telefone": "", "linkedin": "",
            "canal": "E-mail" if emails else "LinkedIn",
            "respondeu_em": d, "o_que_respondeu": resp.replace("[SINAPSE]", "").strip(),
            "situacao_inicial": f"Entrou pelo Monitor de Leads ({temp})",
            "proximo_passo": "Responder em até 1 dia útil e definir dono.",
            "proxima_data": None, "proxima_hora": "",
            "ultimo_toque": d, "estagio_desde": d, "criado_em": date.today().isoformat(),
            "historico": [{"data": d, "autor": "Lead", "texto": f"Respondeu via {canal}: {resp}", "fonte": "Monitor de Leads"}],
        }
        novos.append(lead)
    for l in novos:
        print(f"+ {l['projeto']:9} {l['empresa']} — {l['nome']} ({l['respondeu_em']})")
    print(f"{len(novos)} leads novos do Monitor")
    if apply:
        db["leads"] += novos
        db["monitor_importados"] = sorted(vistos)
        if novos:
            db.setdefault("feed", []).insert(0, {"data": date.today().isoformat(), "autor": "Robô",
                                                 "texto": f"{len(novos)} leads novos do Monitor de Leads: " + ", ".join(l["empresa"] for l in novos)})
        save(db)


if __name__ == "__main__":
    main("--apply" in sys.argv)
