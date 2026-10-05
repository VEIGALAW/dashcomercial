# Robô Prometheus → Dash Comercial

Roda 2x por dia, como tarefa agendada no Claude desktop:
- **7h45 (seg a sex):** sincroniza e depois posta a agenda do dia no Prometheus.
- **19h (todo dia):** só sincroniza.

Pode rodar em qualquer PC que tenha o repo clonado, o Claude desktop com o conector Microsoft 365 e a senha em `private/.senha`. A base publicada no GitHub (criptografada) é a fonte da verdade: a execução sempre começa puxando ela.

## Arquivos

| Arquivo | O que é | Vai pro GitHub? |
|---|---|---|
| `private/leads.json` | Base em texto aberto, regenerada a partir do publicado em cada rodada | **Não** |
| `private/.senha` | Senha do time | **Não** |
| `data/leads.enc.json` | Base criptografada (fonte da verdade, é o que o dash lê) | Sim |
| `robot/build.py` | `--pull` puxa e decripta; sem flag valida, aplica a cadência e criptografa; `--push` publica | Sim |
| `robot/monitor_import.py` | Traz respostas positivas novas do Monitor de Leads (Rainmaker + SINAPSE) | Sim |
| `robot/digest.py` | Monta a mensagem "Agenda do dia" | Sim |

## Passo a passo de cada execução (rodar comandos na pasta do repo)

1. **Puxar:** `python robot/build.py --pull`
2. **Ler o estado:** abrir `private/leads.json`; pegar `prometheus.chat_id`, `prometheus.ultima_msg` e `outlook.ultima_leitura` (se não existir, usar `prometheus.ultima_msg`).
3. **Prometheus (Teams):** ferramenta `list-chat-messages` do ms365 (`top` 50, decrescente, paginar até passar de `ultima_msg`).
   - Ignorar `messageType` diferente de `message`.
   - **Ignorar mensagens cujo texto comece com 🤖**: são do próprio robô.
   - Converter HTML em texto. Se a mensagem responde a outra (`<attachment id=...>` com id numérico), buscar a original para ter contexto. Anexo de arquivo (BP, proposta) = documento enviado/compartilhado.
4. **Outlook (caixa do Rafael):** `list-mail-messages` com `$filter=receivedDateTime ge <outlook.ultima_leitura>` (e `list-mail-folder-messages` na pasta `sentitems` filtrando por `sentDateTime`, para os enviados). Só interessam e-mails trocados com endereços ou domínios de leads da base (ou de empresas citadas nela). Para cada um: e-mail **recebido** do lead = lead respondeu (registrar o que disse, `autor: "Lead"`); e-mail **enviado** = toque nosso. Ler só `subject`, `from`, `toRecipients`, `bodyPreview`. Não abrir anexos.
5. **Agenda (calendário do Rafael):** `get-calendar-view` de hoje até +21 dias. Evento com participante de domínio/e-mail de lead, ou com o nome da empresa no assunto → `estagio = reuniao_marcada`, `proxima_data` e `proxima_hora` = início do evento, `proximo_passo = "Reunião: <assunto>"`. Evento que já passou (de ontem para trás, desde a última leitura) com lead em `reuniao_marcada` → `reuniao_feita` e apagar `proxima_data` para a cadência pedir o recap.
   - Atenção ao domínio: o e-mail do participante pode ser de outra pessoa da empresa do lead (ex.: `@ezortea.com.br` = Estrutural Zortéa).
   - Reunião com participante **externo** (fora de `veiga.law` / `veiga.partners`) que não casa com nenhum lead e parece comercial (diagnóstico, créditos, oportunidades, "<EMPRESA> <> VEIGA") → **não** criar lead; registrar no `feed` como `[revisar] Reunião com <empresa> em dd/mm sem lead no dash`, uma vez por evento (guardar o id do evento em `agenda_avisados`). Ignorar entrevistas de vaga, fornecedores, aulas e reuniões internas.
6. **Monitor de Leads:** `python robot/monitor_import.py --apply` (respostas positivas novas do Rainmaker e do SINAPSE entram como `engajado`, sem dono).
7. **Aplicar os movimentos** (de 3, 4 e 5) na base, casando por empresa, nome ou e-mail (sem acento e sem caixa). Uma mensagem pode citar vários leads.
   - Lead existente: acrescentar em `historico` `{data, autor, texto, fonte}` (fonte = "Prometheus", "Outlook" ou "Agenda"), atualizar `ultimo_toque` = data do movimento. Se o estágio mudar, atualizar `estagio` e `estagio_desde` (data do movimento).
   - Lead novo: criar com `id` = slug(empresa-nome), `projeto` (Rainmaker por padrão; SINAPSE se for escritório de contabilidade/advocacia/gestora buscando parceria, ou se a mensagem disser SINAPSE), `subfrente` (contábil/jurídico/patrimonial) quando SINAPSE, contatos que aparecerem, `responsavel` = quem postou (ou o dono citado), `historico` com o movimento.
   - **Formato curto** (o dash gera esse formato no botão "Copiar mensagem"): `EMPRESA | contato | o que aconteceu | próximo passo | dd/mm [hh:mm] [#estagio]`.
     - `#engajado #material #agendando #reuniao_marcada #reuniao_feita #proposta #negociacao #ganho #nutrir #perdido` definem o estágio.
     - `#perdido EMPRESA | motivo` → `estagio=perdido`, `motivo_perda`.
     - `#novo ...` → lead novo.
     - `EMPRESA | valor R$ 120 mil de honorários / crédito R$ 3 mi` → `valor_honorarios = 120000`, `credito_estimado = 3000000` (números, em reais).
     - `EMPRESA | dono: Aline` → `responsavel = "Aline"`, `repassar = false`.
   - **Próximo passo e data:** se o movimento disser data ("amanhã", "quinta", "08/10", "dia 12 às 15h"), gravar `proxima_data` (AAAA-MM-DD), `proxima_hora` (HH:MM), `proximo_passo`, e apagar `proxima_auto`. Se o estágio mudou e ninguém deu data, apagar `proxima_data` para o `build.py` recalcular pela cadência.
   - Dono: quem assume ("deixa comigo", "vou ligar") vira `responsavel`, com `repassar=false`.
8. **Mapa de estágios** quando a mensagem não tiver #tag:
   - respondeu com interesse → `engajado`
   - material/apresentação/tese enviada → `material`
   - aceitou conversar, falta data / "em análise para agendamento" → `agendando`
   - reunião com data → `reuniao_marcada`; reunião aconteceu → `reuniao_feita`
   - BP/proposta/termo de parceria enviado → `proposta`
   - discutindo preço, minuta, assinatura → `negociacao`
   - assinou → `ganho`; disse não / sem fit → `perdido`; sem timing → `nutrir`
   - Nunca regredir estágio sem motivo explícito.
9. **Feed:** inserir no topo de `feed` um item por movimento relevante `{data, autor, texto}` em uma linha. Máximo 200 itens.
10. **Marcadores:** `prometheus.ultima_msg` = `createdDateTime` da mensagem mais nova lida; `outlook.ultima_leitura` = agora (UTC ISO); `atualizado_em` = agora.
11. **Publicar:** `python robot/build.py --push`. Se a validação falhar, corrigir o JSON e rodar de novo.
12. **Só na rodada da manhã:** `python robot/digest.py` e postar o HTML de `private/digest.html` no chat Prometheus com `send-chat-message` (`contentType: html`). Uma única mensagem. Nada mais é enviado.

## Modo nuvem (rotina do claude.ai)

Quando rodar na nuvem (checkout limpo do repo, sem o PC do Rafael):

- Antes de tudo: `pip install -q cryptography openpyxl` e `export DASH_SENHA=...` (a senha vem no prompt da rotina; nunca gravar em arquivo versionado nem exibir).
- As ferramentas são as do **conector Microsoft 365 do claude.ai** (nomes diferentes do ms365 local): mensagens do chat Prometheus (buscar/listar mensagens do chat com o id de `prometheus.chat_id`), busca de e-mails do Outlook, busca na agenda do Outlook e envio de mensagem em chat do Teams. Use o que o conector oferecer para cada passo; a lógica dos passos é a mesma.
- **Privacidade:** a busca de mensagens do conector varre todos os chats. Considere **somente** mensagens cujo `chatId` seja exatamente o `prometheus.chat_id`; ignore e não cite no resumo nada de outros chats.
- **Pular o passo 6** (Monitor de Leads): o arquivo está só no PC do Rafael. A tarefa local faz essa parte quando o PC estiver ligado.
- Agenda do dia (passo 12) só na rodada das 7h45 de dia útil, e só se ainda não houver no chat uma mensagem de hoje começando com 🤖 "Agenda comercial de hoje" (o PC pode já ter postado).
- `git push` direto na `main`. Se o push for recusado por permissão, não criar branch nem PR: só relatar o erro no resumo final.

## Regras

- O robô só **lê** Teams, Outlook e agenda. A única coisa que ele escreve é a agenda do dia (passo 12). Nunca responder e-mail, aceitar convite, reagir ou mandar outra mensagem.
- Nunca apagar lead. Para tirar do pipeline: `perdido`.
- Não inventar contato nem valor. Só gravar o que está escrito.
- Movimento ambíguo (não dá para saber qual lead): só no `feed`, com prefixo "[revisar]".
- Datas AAAA-MM-DD, fuso de São Paulo.
- Nunca exibir a senha de `private/.senha` nem dados de leads fora do repo.
