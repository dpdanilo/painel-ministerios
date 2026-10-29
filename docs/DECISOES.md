# Decisões técnicas

Registro das escolhas feitas, com o motivo. Datas em ordem cronológica.

## 2026-10-29 · Fase 1 (MVP: Ministério das Cidades)

### Arquitetura
- **Site 100% estático no GitHub Pages; coleta no GitHub Actions.** As APIs do governo têm CORS,
  limites e, em alguns casos, chave. Nada disso pode ficar no navegador.
- **Repositório próprio (`painel-ministerios`)**, linkado por um botão na página inicial do
  `vira-2026`. Assim os painéis existentes não são afetados e cada projeto tem seu próprio deploy e cron.
- **Três camadas de dados** (bruto → normalizado → publicado). O normalizado fica no git: o diff de
  cada commit automático mostra exatamente o que mudou no governo, e o hash detecta mudanças sem
  depender de datas.

### Fontes
- **Orçamento pelos downloads abertos do Portal da Transparência, não pela API com chave.** O arquivo
  anual "Orçamento da Despesa" traz dotação inicial e atualizada; os mensais "Despesas – Execução" trazem
  empenhado, liquidado e pago (e autor de emenda). Nenhum secret é necessário. Conferência: a dotação inicial
  do MCID em 2026 (R$ 16,58 bi) bate com o Raio-X da Câmara (R$ 16,6 bi), e a soma mensal do empenhado
  fica a menos de 1% do valor do arquivo anual.
- **SIOP/Painel do Orçamento não foi usado no MVP.** Os dados equivalentes vêm do Portal, e o SIOP exige
  exportação manual.
- **Ocupantes por curadoria a partir do "Quem é Quem" do gov.br.** O serviço `/instancias` do SIORG
  devolve os postos, mas sem o nome do titular. As datas de nomeação ficam `null` até serem conferidas
  no DOU, e o site mostra "não verificado". Não preenchemos datas por estimativa.
- **Bloco de cada unidade derivado da categoria SIORG do 1º nível** (6 → assistência direta, 8 → singular),
  com herança para baixo. Exemplo: a "Coordenação-Geral de Orçamento e Gestão" da SNP tem categoria 6, mas
  pertence a um órgão singular.
- **Planalto não é acessado por robô** (bloqueia). As normas têm link para consulta humana.

### Modelo de dados (refinamentos sobre o prompt)
- `cargo` guarda **quantidades por unidade e nível**, não postos individuais, porque é o que SIORG e decretos publicam.
  `ocupacao` aponta para **unidade + papel** (titular/adjunto/substituto).
- Vigência (`valido_de`/`valido_ate`) gerada por **comparação de snapshots** (`etl/versionamento.py`): mudança
  fecha a versão anterior e abre outra; o histórico se acumula a cada coleta mensal.
- Orçamento versionado por **exercício + data de extração** (as linhas do exercício são substituídas a cada coleta).
- `evento_institucional` usa listas `origem`/`destino` para representar fusões N:N.
- `politica_publica.vinculos` exige justificativa e fonte; vínculos plausíveis mas não confirmados ficam
  em `pendentes`, aparecem no validador e não aparecem no site. Exemplos: Novo PAC pelo marcador "PA";
  ações 00TI e 00VE no MCMV.

### Formato publicado
- **JSON, não Parquet + DuckDB-WASM.** O DuckDB-WASM sozinho passa de 6 MB, e o volume previsto
  (~40 ministérios × poucas centenas de ações × anos) cabe em poucos MB de JSON. Reavaliar na fase 4 se a
  série histórica crescer muito.
- `index.json` (~1 KB) na abertura e um arquivo por ministério sob demanda. Chaves curtas só nas unidades,
  que são a parte volumosa. O GitHub Pages já serve gzip.
- Linhas só com restos a pagar de anos anteriores (sem dotação nem execução no ano) não são publicadas.

### Front-end
- **Vite + Svelte 5.** Gera um bundle pequeno: carga inicial de ~40 KB (gzip) + 1 KB de dados.
- **ECharts só onde é preciso (gráfico mensal) e carregado sob demanda** (~176 KB gzip), com import modular
  para tree-shaking. Barras e organograma são HTML/CSS: mais leves, acessíveis e legíveis no celular.
- Organograma como **árvore recolhível** (role="tree") em vez de diagrama: funciona com teclado,
  leitor de tela e tela pequena. Diagramas (sunburst/treemap) ficam para a visão de governo (fase 2).
- Paleta dos gráficos validada para daltonismo e contraste (azul/laranja/verde-água, modos claro e escuro).
  O verde-água fica abaixo de 3:1 no tema claro, por isso o gráfico tem legenda com valores e opção "ver como tabela".
  O vermelho da marca é usado só na interface, nunca para série de dados.
- Identidade visual (vermelho, Montserrat/Public Sans) igual à do `vira-2026`.
- Estado na URL (`#/m/mcid/orcamento?prog=2320&uo=56101`): toda visão é compartilhável.
- CSV exportado com `;`, vírgula decimal e BOM: abre direto no Excel em português.

### Automação
- `atualizar.yml`: orçamento toda segunda, SIORG todo dia 3. Commit e deploy só se o hash mudou.
  O push feito pelo `GITHUB_TOKEN` não dispara outros workflows, por isso o deploy é chamado como workflow reutilizável.
- Falha de coleta → issue "Falha na atualização: <fonte>". Avisos do validador, incluindo dado mais velho que
  o limite (Transparência: 21 dias) → issue "Curadoria: pontos para revisão". Issues não se duplicam: a existente é atualizada.

### Limitações conhecidas
- O **MCMV é financiado em grande parte por fundos fora da LOA do órgão** (FGTS, FAR, FDS). O orçamento mostrado é só a parcela da União. O site avisa.
- A série mensal publicada é por programa e soma todas as UOs. Com filtro de UO, o gráfico mensal não é filtrado (o site avisa).
- `valido_de` das unidades na primeira coleta é a data da **última versão** no SIORG, não a da criação da unidade.
- Quantitativo de cargos no SIORG: 426 no MCID. Ainda não foi conferido contra o Anexo II do Decreto 12.553/2025.
- `npm audit`: 2 alertas de baixa severidade em `deepmerge` (dependência do plugin Svelte, só no build, sem correção disponível). Não chegam ao site publicado.

## Roteiro
1. ~~MVP: Ministério das Cidades~~ (esta fase)
2. Todos os ministérios atuais (31 órgãos no SIORG), visão de governo (sunburst/treemap) e comparação
3. Ocupantes de todos os ministérios, partidos e histórico (curadoria + DOU/INLABS)
4. Série histórica desde 2003: eventos institucionais e orçamento de anos anteriores
5. Automação completa: DOU diário, issues de curadoria por nomeação/exoneração
