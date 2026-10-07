"""Gera a mensagem "Agenda do dia" (HTML do Teams) que o robô posta no Prometheus às 7h45 dos dias úteis.

  python robot/digest.py      grava private/digest.html e imprime o HTML

Seções (só aparecem se tiverem itens):
  1. Leads novos desde o último dia útil
  2. Sem dono: alguém precisa assumir
  3. Contatos de hoje + atrasados, por dono (cobrança)
  4. Parados além do SLA do estágio, por dono (cobrança)
  5. Reuniões do próximo dia útil (confirmar hoje)

A primeira linha sempre começa com 🤖 para o robô saber que a mensagem é dele e não reprocessar.
"""
from datetime import date, timedelta
from html import escape

from lib import ROOT, load

DASH = "https://veigalaw.github.io/dashcomercial/"
ABERTOS = {"engajado", "material", "agendando", "reuniao_marcada", "reuniao_feita", "proposta", "negociacao", "nutrir"}
# Máximo de dias sem toque por estágio (mesma tabela do Playbook no dash)
SLA = {"engajado": 2, "material": 7, "agendando": 5, "reuniao_feita": 3, "proposta": 7, "negociacao": 5}
DOW = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
MAX_PARADOS = 3  # por dono, para a mensagem não virar um muro


def dia_util_anterior(d: date) -> date:
    d -= timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def proximo_dia_util(d: date) -> date:
    d += timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def tag(l):
    return "SINAPSE" if l["projeto"] == "SINAPSE" else "RM"


def criado_em(l):
    return l.get("criado_em")


def item_agenda(l, hoje):
    atraso = ""
    if l["proxima_data"] < hoje.isoformat():
        atraso = f" <b>⚠️ atrasado {(hoje - date.fromisoformat(l['proxima_data'])).days}d</b>"
    hora = f"{l['proxima_hora']} · " if l.get("proxima_hora") else ""
    return f"<li>{hora}<b>{escape(l['empresa'])}</b> ({escape(l['nome'])}) [{tag(l)}]: {escape(l.get('proximo_passo') or 'definir próximo passo')}{atraso}</li>"


def por_dono(leads, render):
    donos = sorted({l["responsavel"] for l in leads}, key=lambda d: (d == "Sem dono", d))
    out = []
    for d in donos:
        itens = [l for l in leads if l["responsavel"] == d]
        out.append(f"<p><b>{escape(d)}</b> ({len(itens)})</p><ul>{''.join(render(l) for l in itens)}</ul>")
    return "".join(out)


def main():
    db = load()
    hoje = date.today()
    hoje_s = hoje.isoformat()
    desde = dia_util_anterior(hoje).isoformat()
    abertos = [l for l in db["leads"] if l["estagio"] in ABERTOS]

    novos = [l for l in db["leads"] if (criado_em(l) or "") >= desde]
    sem_dono = [l for l in abertos if l["responsavel"] == "Sem dono"]
    devidos = sorted([l for l in abertos if l.get("proxima_data") and l["proxima_data"] <= hoje_s and l["responsavel"] != "Sem dono"],
                     key=lambda l: (l["proxima_data"], l.get("proxima_hora") or "99"))
    ids_devidos = {l["id"] for l in devidos}

    def idle(l):
        return (hoje - date.fromisoformat(l["ultimo_toque"])).days if l.get("ultimo_toque") else 0

    parados = [l for l in abertos if l["estagio"] in SLA and idle(l) > SLA[l["estagio"]]
               and l["id"] not in ids_devidos and l["responsavel"] != "Sem dono"]
    parados.sort(key=lambda l: -idle(l))
    parados_top = []
    for d in {l["responsavel"] for l in parados}:
        parados_top += [l for l in parados if l["responsavel"] == d][:MAX_PARADOS]
    amanha = proximo_dia_util(hoje).isoformat()
    reunioes = [l for l in abertos if l["estagio"] == "reuniao_marcada" and l.get("proxima_data") == amanha]

    p = [f"<p>🤖 <b>Agenda comercial de hoje ({DOW[hoje.weekday()]} {hoje:%d/%m})</b></p>"]

    # Resumo do que aconteceu desde o último dia útil (o feed é escrito pelo robô em cada rodada)
    ganhos = [l for l in db["leads"] if l["estagio"] == "ganho" and (l.get("estagio_desde") or "") >= desde]
    feed = [f for f in db.get("feed", []) if (f.get("data") or "") >= desde]
    revisar = [f for f in feed if f.get("texto", "").startswith("[revisar]")]
    movs = [f for f in feed if f not in revisar]
    if ganhos:
        p.append("<p>🏆 <b>Fechados</b></p><ul>" + "".join(
            f"<li><b>{escape(l['empresa'])}</b> [{tag(l)}] ({escape(l['responsavel'])})</li>" for l in ganhos) + "</ul>")
    if movs:
        p.append(f"<p>📈 <b>O que andou desde {date.fromisoformat(desde):%d/%m}</b></p><ul>" + "".join(
            f"<li>{escape(f['texto'])}</li>" for f in movs[:12]) + "</ul>")
    if revisar:
        p.append("<p>❓ <b>Ficou sem entender (respondam aqui)</b></p><ul>" + "".join(
            f"<li>{escape(f['texto'].replace('[revisar]', '').strip())}</li>" for f in revisar) + "</ul>")
    if novos:
        p.append(f"<p>🆕 <b>Leads novos</b> ({len(novos)})</p><ul>" + "".join(
            f"<li><b>{escape(l['empresa'])}</b> ({escape(l['nome'])}) [{tag(l)}]: {escape((l.get('o_que_respondeu') or l.get('situacao_inicial') or '')[:140])}</li>"
            for l in novos) + "</ul>")
    if sem_dono:
        p.append(f"<p>🙋 <b>Sem dono: quem assume?</b> Responda aqui com <i>EMPRESA | dono: Nome</i></p><ul>" + "".join(
            f"<li><b>{escape(l['empresa'])}</b> ({escape(l['nome'])}) [{tag(l)}], {escape(l['estagio'].replace('_', ' '))}, respondeu em {escape(l.get('respondeu_em') or '?')}</li>"
            for l in sem_dono) + "</ul>")
    if devidos:
        p.append("<p>📅 <b>Contatos de hoje e atrasados</b></p>" + por_dono(devidos, lambda l: item_agenda(l, hoje)))
    else:
        p.append("<p>📅 Nenhum contato vencendo hoje. 👏</p>")
    if parados_top:
        p.append("<p>🧊 <b>Parados além do prazo do estágio: dar um toque ou mover para Nutrir/Perdido</b></p>" + por_dono(
            parados_top, lambda l: f"<li><b>{escape(l['empresa'])}</b> [{tag(l)}]: {idle(l)} dias sem toque ({escape(l['estagio'].replace('_', ' '))})</li>"))
    if reunioes:
        p.append("<p>🤝 <b>Reuniões do próximo dia útil (confirmar hoje)</b></p><ul>" + "".join(item_agenda(l, hoje) for l in reunioes) + "</ul>")
    p.append(f'<p>Painel: <a href="{DASH}">{DASH}</a> · Atualize aqui no formato EMPRESA | contato | o que aconteceu | próximo passo | data</p>')

    html = "\n".join(p)
    (ROOT / "private").mkdir(exist_ok=True)
    (ROOT / "private" / "digest.html").write_text(html, encoding="utf-8")
    print(html)


if __name__ == "__main__":
    main()
