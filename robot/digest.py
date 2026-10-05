"""Gera a mensagem "Agenda do dia" (HTML do Teams) com os contatos de hoje e os atrasados, por dono.

  python robot/digest.py      grava private/digest.html e imprime o HTML

A primeira linha sempre começa com 🤖 para o robô saber que a mensagem é dele e não reprocessar.
"""
from datetime import date, timedelta
from html import escape

from lib import ROOT, load

DASH = "https://veigalaw.github.io/dashcomercial/"
ABERTOS = {"engajado", "material", "agendando", "reuniao_marcada", "reuniao_feita", "proposta", "negociacao", "nutrir"}
DOW = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]


def linha(l, hoje):
    atraso = ""
    if l["proxima_data"] < hoje.isoformat():
        dias = (hoje - date.fromisoformat(l["proxima_data"])).days
        atraso = f" <b>⚠️ atrasado {dias}d</b>"
    hora = f"{l['proxima_hora']} · " if l.get("proxima_hora") else ""
    tag = "SINAPSE" if l["projeto"] == "SINAPSE" else "RM"
    return f"<li>{hora}<b>{escape(l['empresa'])}</b> ({escape(l['nome'])}) [{tag}]: {escape(l.get('proximo_passo') or 'definir próximo passo')}{atraso}</li>"


def main():
    db = load()
    hoje = date.today()
    amanha = hoje + timedelta(days=3 if hoje.weekday() == 4 else 1)
    abertos = [l for l in db["leads"] if l["estagio"] in ABERTOS and l.get("proxima_data")]
    devidos = [l for l in abertos if l["proxima_data"] <= hoje.isoformat()]
    reunioes_amanha = [l for l in abertos if l["estagio"] == "reuniao_marcada" and l["proxima_data"] == amanha.isoformat()]

    donos = sorted({l["responsavel"] for l in devidos}, key=lambda d: (d == "Sem dono", d))
    partes = [f"<p>🤖 <b>Agenda comercial de hoje ({DOW[hoje.weekday()]} {hoje:%d/%m})</b></p>"]
    if not devidos:
        partes.append("<p>Nenhum contato vencendo hoje. 👏</p>")
    for d in donos:
        itens = sorted([l for l in devidos if l["responsavel"] == d], key=lambda l: (l["proxima_data"], l.get("proxima_hora") or "99"))
        partes.append(f"<p><b>{escape(d)}</b> ({len(itens)})</p><ul>{''.join(linha(l, hoje) for l in itens)}</ul>")
    if reunioes_amanha:
        partes.append("<p><b>Reuniões amanhã (confirmar hoje):</b></p><ul>" +
                      "".join(linha(l, hoje) for l in reunioes_amanha) + "</ul>")
    partes.append(f'<p>Painel completo: <a href="{DASH}">{DASH}</a> · Atualize o grupo no formato EMPRESA | contato | o que aconteceu | próximo passo | data</p>')
    html = "\n".join(partes)
    (ROOT / "private" / "digest.html").write_text(html, encoding="utf-8")
    print(html)


if __name__ == "__main__":
    main()
