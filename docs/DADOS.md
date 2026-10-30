# Dicionário de dados

Três camadas:

1. **Bruto** (`data/bruto/`, fora do git): respostas das fontes como vieram.
2. **Normalizado** (`data/normalizado/*.csv`, no git) e **curadoria** (`data/curadoria/*.yaml`, no git).
3. **Publicado** (`site/public/data/*.json`, gerado no build): só o que o site lê.

Convenções: datas ISO `AAAA-MM-DD`; valores em reais com 2 casas; `valido_ate` vazio = vigente.
Códigos oficiais (SIORG, UO, programa, ação) são sempre texto, para não perder zeros à esquerda.

## Fontes

| `fonte_id` | Fonte | Acesso | Frequência |
|---|---|---|---|
| `siorg` | SIORG – API de Estrutura Organizacional (MGI) | `estruturaorganizacional.dados.gov.br/doc`, sem chave | mensal |
| `transparencia-orcamento-<ano>` | Portal da Transparência (CGU): "Orçamento da Despesa" (anual) + "Despesas – Execução" (mensal) | downloads CSV em `dadosabertos-download.cgu.gov.br`, sem chave | semanal |
| `siape` | Portal da Transparência (CGU): "Servidores – SIAPE", arquivo Cadastro | download mensal, sem chave (~80 MB/mês) | mensal (~2 meses de atraso) |
| `tse` | TSE: candidaturas 2018, 2020, 2022, 2024 e 2026 (`consulta_cand`) | download, sem chave | mensal |
| `transparencia-orcamento-historico` | Portal da Transparência: "Orçamento da Despesa" de 2014 até o ano passado | download, sem chave | mensal (ajustes de fechamento) |
| `ipca` | IBGE: IPCA número-índice (SIDRA, tabela 1737) | API pública | mensal |
| curadoria | gov.br dos ministérios, legislação (Planalto/LexML), DOU | leitura humana | sob demanda |

Endpoints SIORG usados:
- `/estrutura-organizacional/completa?codigoUnidade=<órgão>&retornarOrgaoEntidadeVinculados=SIM`: árvore, competências, ato normativo de cada unidade.
- `/cargo-funcao/alocados-estrutura`: quantitativo de cargos/funções por unidade (o governo todo; filtrado por órgão).
- Não usado: `/instancias/consulta-unidade` traz as instâncias de cargo, mas `nomeTitular` vem sempre vazio.

## `data/normalizado/`

### `fonte_metadado.csv`
| campo | origem / significado |
|---|---|
| `fonte_id` | identificador da fonte |
| `nome`, `url` | descrição e endereço |
| `data_referencia` | SIORG: data da versão mais recente das unidades; Transparência: data do arquivo mais novo |
| `coletado_em` | data em que o **conteúdo mudou** pela última vez (coleta sem novidade não altera) |
| `hash` | SHA-256 do conteúdo normalizado (sem cabeçalhos voláteis da API) |

### `unidade.csv`: árvore organizacional (versionada)
| campo | origem |
|---|---|
| `cod_siorg` | SIORG `codigoUnidade` |
| `cod_pai` | SIORG `codigoUnidadePai` (vazio na raiz = o ministério) |
| `ministerio_id` | curadoria (`ministerios.yaml`) |
| `sigla`, `nome` | SIORG |
| `tipo` | SIORG `codigoTipoUnidade`: `orgao`, `unidade-administrativa`, `unidade-colegiada`, `entidade` |
| `categoria` | SIORG `codigoCategoriaUnidade` (6 Assistência Direta e Imediata, 8 Específico Singular, 7 Colegiado, 39 Vinculado…) |
| `bloco` | **derivado**: `assistencia` / `singular` / `descentralizada` / `pesquisa` / `forcas` / `colegiado` / `vinculada`. Vem da categoria da unidade de 1º nível (tabela em `etl/siorg.py`); as de níveis abaixo herdam; colegiados e entidades são classificados pelo tipo |
| `atividade` | SIORG `areaAtuacao`: Finalística → `fim`, Suporte → `meio` |
| `profundidade` | **derivado**: 0 = ministério, 1 = secretarias e assessorias, 2 = departamentos… |
| `competencia` | SIORG `competencia` (texto do decreto, art. do Anexo I) |
| `ato_tipo`, `ato_numero`, `ato_vigencia`, `ato_url` | SIORG `atoNormativo`: último ato que alterou a unidade (link para o DOU) |
| `versao_siorg` | SIORG `versaoConsulta` |
| `valido_de` | SIORG `dataInicialVersaoConsulta` na primeira vez; depois, a data da mudança detectada |
| `valido_ate` | preenchido pelo ETL quando a unidade muda ou some do SIORG |

### `cargo.csv`: quantitativo de cargos (versionado)
| campo | origem |
|---|---|
| `cod_unidade`, `ministerio_id` | SIORG `codigoUnidade` / curadoria |
| `tipo` | SIORG `siglaCargo`: `CCE`, `FCE`, `MEST` (Ministro de Estado)… |
| `categoria`, `nivel` | SIORG `categoriaCargo`, `nivelCargo`. Categoria 1 = direção, 2 = assessoramento, 3 = gerência de projetos, 4 = coordenação técnica. "CCE 1.17" = categoria 1, nível 17 |
| `denominacao` | SIORG `denominacaoCargo` |
| `mobilidade` | SIORG: `FX` fixo na unidade, `DD` distribuível |
| `quantidade` | soma de `total` |
| `valido_de`, `valido_ate` | data da coleta em que o quantitativo apareceu/mudou |

### `orcamento.csv`: por exercício × UO × programa × ação
| campo | origem |
|---|---|
| `exercicio`, `cod_orgao_superior`, `cod_orgao`, `cod_uo`, `cod_programa`, `cod_acao` | arquivo anual (Orçamento da Despesa) |
| `dotacao_inicial` | anual, `ORÇAMENTO INICIAL` (LOA aprovada) |
| `dotacao_atual` | anual, `ORÇAMENTO ATUALIZADO` (após créditos e remanejamentos) |
| `empenhado`, `liquidado`, `pago` | **soma dos arquivos mensais** de execução do ano |
| `rp_pago` | mensal, restos a pagar de anos anteriores pagos no ano (não entra no "pago") |
| `empenhado_emendas` | mensal, empenhado em linhas com autor de emenda informado |
| `empenhado_orcdesp` | anual, `ORÇAMENTO EMPENHADO`. Usado só para conferir a soma mensal (tolerância de 2%) |
| `data_extracao` | data do arquivo mais recente usado |

A execução é filtrada pela **UO**, não pelo órgão da unidade gestora. Assim entram despesas do
ministério executadas por outros órgãos (descentralização).

### `ocupacao.csv`: mandatos de direção (desde jan/2023)
Uma linha por pessoa × função × unidade, juntando meses consecutivos do cadastro do SIAPE.

| campo | origem |
|---|---|
| `pessoa_id` | hash de nome + 6 dígitos visíveis do CPF (o CPF não fica no repositório) |
| `nome` | SIAPE `NOME` |
| `ministerio_id` | SIAPE `COD_ORG_EXERCICIO` → ministério (por nome ou `orgaos_siape.yaml`); unidades com nome de ministério prevalecem; órgãos da Presidência separados pelo nome da unidade |
| `funcao`, `nivel` | `MEST` (99) para Ministro de Estado; `CCE 1.xx`/`FCE 1.xx` a partir de SIAPE `SIGLA_FUNCAO` (CCX/FEX) e `NIVEL_FUNCAO` |
| `cargo` | SIAPE `ATIVIDADE` (ex.: "Secretario(a)") |
| `cod_uorg`, `uorg` | unidade de exercício no SIAPE (nome cortado em 40 caracteres) |
| `cod_siorg` | **derivado**: unidade do SIORG com o mesmo nome no mesmo ministério (vazio se ambíguo ou não encontrado) |
| `inicio` | SIAPE `DATA_INGRESSO_CARGOFUNCAO` do 1º mês do mandato |
| `primeiro_mes`, `ultimo_mes` | meses (AAAAMM) em que o mandato aparece no SIAPE |
| `fim_aprox` | 1º mês em que a pessoa já não aparece naquela função/unidade (vazio = segue no cargo) |

### `pessoa.csv`
`pessoa_id, nome`.

### `candidatura.csv`: candidaturas dos dirigentes no TSE
`pessoa_id, ano, partido, nome_partido, cargo, uf, municipio, situacao_candidatura, resultado`. Cruzamento por nome +
6 dígitos centrais do CPF (TSE `NR_CPF_CANDIDATO` × SIAPE `CPF` mascarado).

### `orcamento_historico.csv`: anos encerrados, desde 2014
`exercicio, cod_orgao_superior, cod_programa, nome_programa, operacao_especial, dotacao_inicial, dotacao_atual, empenhado, pago`.
`pago` = "ORÇAMENTO REALIZADO" do arquivo anual. `operacao_especial` = programa 0901–0913 (pelo código, porque em 2023 o
Portal publicou os nomes de programa como "Sem informação"). Liquidado não existe nesse arquivo.

### `ipca.csv`
`mes, indice`: número-índice mensal do IPCA (base dez/1993 = 100).

### `orcamento_mensal.csv`
`exercicio, mes, cod_uo, cod_programa, cod_acao, empenhado, liquidado, pago`: valores **do mês** (não acumulados).

### `uo.csv`, `programa.csv`, `acao.csv`
Nomes oficiais por exercício (o mesmo código pode mudar de nome a cada PPA).

## `data/curadoria/`
Descrição de cada arquivo no [README](../README.md#atualizar-a-curadoria). Campos comuns:
`fonte` (obrigatório), `valido_de` / `valido_ate`, `nota`.

## JSON publicado

### `index.json` (carregado na abertura, ~20 KB, ~4 KB com gzip)
`gerado_em`, `exercicio`, `fontes{}`, `eventos[]`, `ministerios[]`, com `id, sigla, nome, categoria, ministro{nome, partido},
n_unidades, n_secretarias` (órgãos singulares do 1º nível) `, n_cargos, pct_fim, orcamento{…}` e `orcamento_sem_oe{…}`
(mesmos campos, sem os programas de operações especiais).

Também no `index.json`: `serie_ministerios` (`[data, total, ministérios, Presidência, outros]` em cada data de mudança),
`eventos[]` com `nomes{origem, destino}` (nome de cada órgão antes/depois do evento), `normas{}`,
`ipca{referencia, fatores{ano: multiplicador}}` e `orcamento_anual_total` (`[ano, dotação sem OE, pago sem OE, dotação, pago]`).

### `agregados/comparacao.json` (carregado só na tela de comparação, ~120 KB)
Por ministério: `unidades_por_bloco{}`, `cargos_por_nivel{"CCE 1.17": n…}`, `mensal` e `mensal_sem_oe`
(`[mes, empenhado, liquidado, pago]` acumulados), `principais_programas[]` (5 maiores sem operações especiais),
`politicas[]`, `ocupantes[]` (titulares).

### `ministerios/<id>.json` (carregado ao abrir o ministério; de 45 KB a 1 MB, até ~150 KB com gzip)
| chave | conteúdo |
|---|---|
| `unidades[]` | `c` código, `p` pai, `s` sigla, `n` nome, `b` bloco, `a` atividade, `t` tipo, `d` profundidade, `ato{}` |
| `categoria` | `ministerio`, `presidencia` ou `orgao` |
| `orcamento.operacoes_especiais[]` | códigos de programa cujo nome começa com "OPERACOES ESPECIAIS" |
| `cargos{cod: [[tipo, categoria, nivel, denominacao, qtd, mobilidade]]}` | só versões vigentes |
| `ocupantes[]` | mandatos de Ministro e de 1.15 para cima: `pessoa, nome, funcao, nivel, cargo, uorg, unidade` (SIORG, se identificada), `papel, de, ate` (`AAAA-MM` aproximado, nulo = atual), `partido{sigla, ano, cargo, uf, resultado, fonte}` |
| `orcamento` | `colunas` + `linhas` (matriz), `mensal` (mês × programa), dicionários `uos`, `programas`, `acoes` |
| `politicas[]`, `eventos[]`, `normas{}` | da curadoria (sem os vínculos pendentes) |
| `competencias[]` | competências do ministério (SIORG) |
| `historia[]` | nomes do órgão desde 2003: `nome, de, ate, categoria, norma` |
| `orcamento_anual[]` | `[ano, dot_ini, dot_atual, empenhado, pago, dot_atual_sem_oe, pago_sem_oe]` do órgão orçamentário, de 2014 ao ano corrente |
| `fontes{estrutura, orcamento, ocupantes, politicas}` | o que cada bloco do site mostra como fonte e data |

### `ministerios/<id>-competencias.json` (carregado ao abrir o detalhe de uma unidade)
`{cod_siorg: [competências]}`. Fica separado porque é a parte mais pesada nos ministérios grandes.
