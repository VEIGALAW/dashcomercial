# Dash Comercial · Veiga

Pipeline comercial do time (Rainmaker + SINAPSE): agenda semanal de follow-ups, kanban por estágio, todos os leads, movimentos e playbook.

**Acesso:** https://veigalaw.github.io/dashcomercial/ (pede a senha do time uma vez por computador).

## Como funciona

- Os dados ficam em `data/leads.enc.json`, criptografados com AES-256-GCM. O repo é público, mas sem a senha ninguém lê nome, contato ou histórico dos leads.
- A base mestre (`private/leads.json`) e a senha (`private/.senha`) ficam só no PC do Rafael e nunca sobem para o GitHub.
- Um robô (tarefa agendada no Claude desktop, todo dia às 19h) lê o grupo **Prometheus** no Teams, atualiza a base e publica. Detalhes em [`robot/ROBO.md`](robot/ROBO.md).

## Trocar a senha

1. Editar `private/.senha` com a nova senha.
2. `python robot/build.py --push`
3. Avisar o time. Cada pessoa clica em **Sair** no dash e entra com a nova senha.
