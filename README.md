# Dash Comercial · Veiga

Pipeline comercial do time (Rainmaker + SINAPSE): agenda semanal de follow-ups, kanban por estágio, todos os leads, métricas, movimentos e playbook.

**Acesso:** https://veigalaw.github.io/dashcomercial/ (pede a senha do time uma vez por computador).

## Como funciona

- Os dados ficam em `data/leads.enc.json`, criptografados com AES-256-GCM. O repo é público, mas sem a senha ninguém lê nome, contato ou histórico dos leads.
- O robô (tarefas agendadas no Claude desktop) roda às **7h45 (dias úteis)** e às **19h (todo dia)**:
  - lê o grupo **Prometheus** no Teams, o Outlook e a agenda do Rafael, e o **Monitor de Leads** (respostas do Rainmaker e do SINAPSE);
  - atualiza estágios, donos, próximos contatos e histórico; preenche datas pela cadência padrão quando ninguém marcou;
  - às 7h45 posta no Prometheus a agenda do dia de cada pessoa.
  Detalhes em [`robot/ROBO.md`](robot/ROBO.md).
- Se o robô ficar mais de 14h sem publicar, o dash mostra um aviso no topo.

## Rodar o robô em outro PC (backup)

1. `gh repo clone VEIGALAW/dashcomercial` e `pip install cryptography openpyxl`
2. Criar `private/.senha` com a senha do time.
3. `python robot/build.py --pull` baixa a base atual. A partir daí, qualquer Claude desktop com o conector Microsoft 365 roda as instruções de `robot/ROBO.md`.

## Trocar a senha

1. Editar `private/.senha` com a nova senha (em todos os PCs que rodam o robô).
2. `python robot/build.py --push`
3. Avisar o time. Cada pessoa clica em **Sair** no dash e entra com a nova senha.
