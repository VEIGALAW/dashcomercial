# Briefing de design: Dash Comercial Veiga

## O que é

Painel do pipeline comercial da Veiga Partners (direito tributário). É usado todo dia por 4 pessoas (Rafael, Lucas, Aline, Ricardo), no desktop e no celular, para responder rápido:

1. **Quem eu preciso contatar hoje e o que falar?** (aba Semana, a principal)
2. **Em que pé está cada lead?** (Pipeline e Todos os leads)
3. **O comercial está andando?** (Métricas)

Duas frentes convivem e precisam ser diferenciadas de relance:
- **Rainmaker**: prospecção de clientes (CFOs e controllers de empresas).
- **SINAPSE**: parcerias com escritórios de contabilidade, advocacia e gestoras, com subfrente (contábil, jurídico, patrimonial).

## Objetivo do redesign

Deixar o painel **sofisticado, elegante, objetivo e didático**, com cara de produto premium de escritório de advocacia (não de planilha). Prioridades, nesta ordem:

1. Hierarquia clara: o que vence hoje e o que está atrasado salta aos olhos; o resto fica calmo.
2. Leitura rápida dos cards: empresa → próximo passo → dono → estágio/alerta.
3. Didático: quem abre pela primeira vez entende os estágios e as etiquetas sem explicação.
4. Bonito nos dois temas (claro e escuro) e no celular (largura de 375px, sem rolagem horizontal da página).

Identidade: a do brandbook Veiga Partners (nov/2023), já aplicada no `index.html`: marca monocromática, branco e tons de cinza (#EBEBEB, #E2E2E2, #CECECE, #9D9D9D, #3C3C3C, preto só no logo e em detalhes), Helvetica Neue com Arial como fonte de sistema, grafismo de módulos "+" em espaços vazios. O logo está embutido em vetor no próprio `index.html` (símbolo `#vp-logo`). Cores só para estado: vermelho (atrasado) e âmbar (parado).

## Como ver com dados (sem senha)

- Online: https://veigalaw.github.io/dashcomercial/?demo=1
- Local: na pasta do repo, `python -m http.server 8765` e abrir http://localhost:8765/?demo=1

O modo demo carrega `data/demo.json`, com **dados fictícios** na mesma estrutura e no mesmo volume da base real (52 leads).

## Arquivos

| Arquivo | O que é |
|---|---|
| `index.html` | O dash inteiro: HTML + CSS + JS num arquivo só. **É o único arquivo a redesenhar.** |
| `data/demo.json` | Dados fictícios para o design. |
| `data/leads.enc.json` | Dados reais, criptografados. Não mexer. |
| `robot/` | Robô que atualiza os dados. Não mexer. |

## Telas atuais

- **Tela de senha** (`#lock`).
- **Cabeçalho**: título, "Atualizado em", filtro de frente (Todos/Rainmaker/SINAPSE), filtro de dono, busca, tema, sair. Abas: Semana, Pipeline, Todos os leads, Métricas, Movimentos, Playbook.
- **KPIs** clicáveis (filtram a lista): ativos, atrasados, contatos hoje, contatos na semana, propostas na mesa, parados além do SLA, sem dono.
- **Semana**: coluna "Atrasados" + dias seg–sex (sáb/dom só se tiver item), cards por lead, navegação entre semanas.
- **Pipeline**: kanban por estágio com critério de entrada e SLA no topo de cada coluna.
- **Todos os leads**: tabela ordenável.
- **Métricas**: dinheiro na mesa (pipeline, ponderado, crédito), resultado (ganhos, perdidos, taxa, ciclo), funil de conversão, tempo médio no estágio, tabela por dono, ativos por frente, motivos de perda.
- **Movimentos**: linha do tempo.
- **Playbook**: regras de prospecção, tabela de estágios, cadência, qualificação, ritual, formato de mensagem.
- **Painel lateral do lead** (abre ao clicar em qualquer card ou linha): próximo passo, contatos (e-mail, WhatsApp, LinkedIn), valores, histórico em linha do tempo, e o formulário **Registrar movimento**, que gera a mensagem para colar no Teams.

## Regras que NÃO podem quebrar

1. **Arquivo único** `index.html`, sem etapa de build. Bibliotecas externas só de `cdnjs.cloudflare.com`, `cdn.jsdelivr.net`, `unpkg.com`; fontes só do Google Fonts. Nada de analytics, rastreamento ou envio de dados para fora.
2. **Criptografia e acesso**: manter a lógica de `decrypt()` / `unlock()` (WebCrypto, PBKDF2-SHA256 + AES-256-GCM, lendo `data/leads.enc.json`), o "lembrar neste computador" (localStorage `dash.pw`), o botão Sair e o modo `?demo=1`.
3. **Dados**: não mudar nomes de campos nem as chaves de estágio (`engajado, material, agendando, reuniao_marcada, reuniao_feita, proposta, negociacao, ganho, nutrir, perdido`). O robô grava nesse formato.
4. **Mensagem do "Registrar movimento"**: manter exatamente o formato gerado por `composerMsg()` (`EMPRESA | contato | o que aconteceu | próximo passo | dd/mm hh:mm #estagio`), porque o robô lê esse texto.
5. **Regras de negócio** (datas, atrasado, parado/SLA, probabilidades, cálculos das métricas): podem mudar de visual, não de cálculo.
6. `<meta name="robots" content="noindex, nofollow">` continua.
7. Acessível: contraste AA nos dois temas, foco visível, alvos de toque de pelo menos 40px no celular.

## Campos de um lead

```
id, nome, empresa, cargo, projeto ("Rainmaker" | "SINAPSE"), subfrente,
estagio, estagio_desde, trilha [{estagio, data}],
responsavel ("Rafael" | "Lucas" | "Aline" | "Ricardo" | "Sem dono"), repassar (bool),
email [..], telefone, linkedin, canal,
respondeu_em, o_que_respondeu,
proximo_passo, proxima_data (AAAA-MM-DD), proxima_hora (HH:MM), proxima_auto (bool: data veio da cadência),
ultimo_toque, valor_honorarios (R$), credito_estimado (R$), motivo_perda,
historico [{data, autor, texto, fonte}], criado_em
```

Topo do JSON: `publicado_em`, `atualizado_em`, `equipe`, `feed [{data, autor, texto}]`, `prometheus {chat_id, ultima_msg}`, `leads [...]`.

## Entrega

Um novo `index.html` substituindo o atual. Testar em `?demo=1` (claro, escuro, 375px e 1440px) antes de entregar.
