# Dash Comercial · Veiga

Pipeline comercial do time (Rainmaker + SINAPSE): agenda semanal de follow-ups, kanban por estágio, todos os leads, métricas, movimentos e playbook.

**Acesso:** https://veigalaw.github.io/dashcomercial/ (pede a senha do time uma vez por computador).

## Como funciona

- Os dados ficam em `data/leads.enc.json`, criptografados com AES-256-GCM. O repo é público, mas sem a senha ninguém lê nome, contato ou histórico dos leads.
- O robô roda **na nuvem** (rotina "Robô Dash Comercial (nuvem)" em claude.ai/code/routines, conector Microsoft 365), às **7h45 e 19h45 todo dia**, sem depender de nenhum PC ligado:
  - lê o grupo **Prometheus** no Teams, o Outlook e a agenda do Rafael;
  - atualiza estágios, donos, próximos contatos e histórico; preenche datas pela cadência padrão quando ninguém marcou;
  - às 7h45 dos dias úteis posta no Prometheus a agenda do dia de cada pessoa.
- No PC do Rafael fica só uma tarefa (19h) que traz as respostas novas do **Monitor de Leads** (Rainmaker + SINAPSE), porque esse arquivo só existe no Desktop dele.
- Detalhes em [`robot/ROBO.md`](robot/ROBO.md).
- Se o robô ficar mais de 14h sem publicar, o dash mostra um aviso no topo.

## Rodar o robô em outro PC (backup)

1. `gh repo clone VEIGALAW/dashcomercial` e `pip install cryptography openpyxl`
2. Criar `private/.senha` com a senha do time.
3. `python robot/build.py --pull` baixa a base atual. A partir daí, qualquer Claude desktop com o conector Microsoft 365 roda as instruções de `robot/ROBO.md`.

## Trocar a senha

1. Editar `private/.senha` com a nova senha (em todos os PCs que rodam o robô).
2. `python robot/build.py --push`
3. Avisar o time. Cada pessoa clica em **Sair** no dash e entra com a nova senha.
