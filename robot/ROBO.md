# Robô Prometheus → Dash Comercial

Roda 1x por dia (tarefa agendada no Claude desktop, 19h). Lê o grupo **Prometheus** no Teams e atualiza o dash.

## Arquivos

| Arquivo | O que é | Vai pro GitHub? |
|---|---|---|
| `private/leads.json` | Base mestre em texto aberto (fonte da verdade) | **Não** |
| `private/.senha` | Senha do time (criptografa os dados) | **Não** |
| `data/leads.enc.json` | Base criptografada que o dash lê | Sim |
| `robot/build.py` | Valida, aplica a cadência, criptografa e publica | Sim |

## Passo a passo de cada execução

1. **Ler o estado.** Abrir `private/leads.json`. Pegar `prometheus.chat_id` e `prometheus.ultima_msg`.
2. **Buscar mensagens novas** do chat com a ferramenta `list-chat-messages` do ms365 (`top` 50, ordem decrescente; paginar até passar de `ultima_msg`). Ignorar `messageType` diferente de `message`. Converter o HTML do corpo em texto. Se a mensagem citar outra (`<attachment id=...>` de reply), buscar a original para ter contexto. Anexos de arquivo (BP, proposta) contam como "documento enviado/compartilhado".
3. **Interpretar cada mensagem** e mapear para leads existentes (casar por empresa, nome ou e-mail; ignorar acentos e caixa). Uma mensagem pode citar vários leads.
   - Movimento em lead existente: acrescentar em `historico` `{data, autor, texto, fonte:"Prometheus"}`, atualizar `ultimo_toque` = data da mensagem, e se o movimento mudar o estágio, atualizar `estagio` e `estagio_desde`.
   - Lead novo (empresa que não existe na base): criar com `id` = slug(empresa-nome), `projeto` (Rainmaker por padrão; SINAPSE se for escritório de contabilidade/advocacia/gestora buscando parceria ou se a mensagem disser SINAPSE), `subfrente` (contábil / jurídico / patrimonial) quando SINAPSE, dados de contato que aparecerem, `responsavel` = quem postou (ou quem foi citado como dono).
   - Formato curto aceito: `EMPRESA | contato | o que aconteceu | próximo passo | data`, `#ganho`, `#perdido`, `#novo`, `#nutrir`.
   - **Próximo passo e data:** se a mensagem disser data ("amanhã", "quinta", "08/10", "dia 12 às 15h"), gravar `proxima_data` (AAAA-MM-DD) e `proxima_hora` (HH:MM) e `proximo_passo`, e apagar `proxima_auto`. Se o estágio mudou e ninguém deu data, apagar `proxima_data` para o `build.py` recalcular pela cadência.
   - Dono: se alguém assumir ("deixa comigo", "vou ligar"), trocar `responsavel` e `repassar=false`.
4. **Mapa de estágios** (`estagio`):
   - respondeu com interesse → `engajado`
   - material / apresentação / tese enviada → `material`
   - aceitou conversar, falta data / "em análise para agendamento" → `agendando`
   - reunião com data marcada → `reuniao_marcada` (proxima_data = dia da reunião)
   - reunião aconteceu → `reuniao_feita`
   - BP / proposta / termo de parceria enviado → `proposta`
   - discutindo preço, minuta, assinatura → `negociacao`
   - assinou → `ganho`; disse não / sem fit → `perdido`; sem timing → `nutrir`
   - Nunca regredir o estágio sem motivo explícito na mensagem.
5. **Feed:** acrescentar no topo de `feed` um item por mensagem relevante: `{data, autor, texto}` em uma linha (ex.: "Aline: BP enviada para Rumo Química e Algar"). Manter no máximo 200 itens.
6. Atualizar `prometheus.ultima_msg` com o `createdDateTime` da mensagem mais nova lida e `atualizado_em` com o horário atual (UTC, ISO).
7. **Publicar:** `python robot/build.py --push` (na pasta do repo). Se falhar a validação, corrigir o JSON e rodar de novo.
8. **Não** postar nada no Teams nem mandar e-mail. O robô só lê.

## Regras

- Nunca apagar lead. Para tirar do pipeline, mover para `perdido`.
- Não inventar dados de contato. Só gravar o que estiver escrito.
- Mensagem ambígua (não dá para saber qual lead): registrar só no `feed` com o prefixo "[revisar]".
- Datas sempre AAAA-MM-DD. Fuso horário de São Paulo.
- Commit só do `data/leads.enc.json` (o `build.py --push` já faz isso).
