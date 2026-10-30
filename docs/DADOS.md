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

### `agregados/comparacao.json` (carregado só na tela de comparação, ~75 KB)
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
| `ocupantes[]` | `pessoa, nome, cargo, unidade, papel, de, ate, partido, fonte, verificado_em` |
| `orcamento` | `colunas` + `linhas` (matriz), `mensal` (mês × programa), dicionários `uos`, `programas`, `acoes` |
| `politicas[]`, `eventos[]`, `normas{}` | da curadoria (sem os vínculos pendentes) |
| `competencias[]` | competências do ministério (SIORG) |
| `fontes{estrutura, orcamento, ocupantes, politicas}` | o que cada bloco do site mostra como fonte e data |

### `ministerios/<id>-competencias.json` (carregado ao abrir o detalhe de uma unidade)
`{cod_siorg: [competências]}`. Fica separado porque é a parte mais pesada nos ministérios grandes.
