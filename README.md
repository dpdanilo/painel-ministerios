# Estrutura dos Ministérios

Painel da estrutura do Poder Executivo Federal: secretarias, departamentos, cargos, ocupantes,
competências, orçamento e políticas públicas de cada ministério, a partir de dados oficiais.

**Site:** https://dpdanilo.github.io/painel-ministerios/

Hoje o painel cobre o Ministério das Cidades (fase 1). As próximas fases estão em
[docs/DECISOES.md](docs/DECISOES.md#roteiro).

## Como funciona

```
SIORG (API) ─┐                                   ┌─ site/public/data/*.json ─ Vite ─ GitHub Pages
Transparência ┼─ etl/ (Python) ─ data/normalizado ┤
(downloads)  ─┘        ▲                          └─ validação (erros barram a publicação)
              data/curadoria/*.yaml (manual, com fonte em cada linha)
```

- O navegador **nunca** chama as APIs do governo: os dados são coletados no GitHub Actions e publicados como arquivos estáticos.
- `data/normalizado/` fica no git. Cada atualização vira um commit com o diff do que mudou.
- O GitHub Actions atualiza sozinho: orçamento toda segunda e estrutura (SIORG) todo dia 3. Só faz commit e deploy se algo mudou.
- Falhas de coleta e pontos de curadoria abrem uma *issue* automaticamente.

## Rodar localmente

Requisitos: Python 3.12+ e Node 22+.

```bash
python -m venv .venv
.venv/Scripts/activate          # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt

python -m etl atualizar         # baixa SIORG + orçamento do ano (~80 MB, vai para data/bruto/)
python -m etl validar           # confere curadoria e dados
python -m etl publicar          # gera site/public/data/
python -m pytest -q             # testes do ETL

cd site
npm install
npm run dev                     # http://localhost:5173/painel-ministerios/
npm test && npm run build       # testes do front-end e build de produção
```

Outros comandos: `python -m etl coletar siorg`, `python -m etl normalizar orcamento --exercicio 2025`.

## Secrets do GitHub

**Nenhum é necessário hoje.** O orçamento vem dos downloads abertos do Portal da Transparência,
que não exigem chave. A API do Portal (com chave) só será usada se precisarmos de consultas que
os downloads não cobrem (ex.: convênios por município).

Se precisar da chave:
1. Acesse https://portaldatransparencia.gov.br/api-de-dados/cadastrar-email e entre com sua conta gov.br.
2. A chave chega por e-mail.
3. No terminal, dentro desta pasta: `gh secret set TRANSPARENCIA_API_KEY` e cole a chave quando pedir
   (ou pelo site: Settings → Secrets and variables → Actions → New repository secret).
   Nunca coloque a chave em arquivo do repositório.

## Atualizar a curadoria

Os dados que não existem em fonte estruturada ficam em `data/curadoria/`, em YAML editável
(dá para editar direto no site do GitHub, pelo ícone de lápis):

| Arquivo | O que guarda |
|---|---|
| `ministerios.yaml` | identidade de cada ministério e suas versões (nome, sigla, códigos, vigência, normas) |
| `correspondencia_siorg_orcamento.yaml` | qual unidade orçamentária (UO) corresponde a qual unidade do SIORG |
| `ocupacoes.yaml` / `pessoas.yaml` | quem ocupa cada cargo, com datas; filiação partidária com vigência |
| `politicas_publicas.yaml` | nome conhecido da política ↔ ações/programas do orçamento, com justificativa |
| `eventos_institucionais.yaml` | criações, extinções, fusões e recriações de ministérios |
| `normas.yaml` | leis, decretos e MPs citados |
| `totais_referencia.yaml` | totais publicados por terceiros, para conferir o orçamento coletado |

Regras:
- **Toda linha precisa de `fonte`.** O validador recusa linha sem fonte.
- Datas em `AAAA-MM-DD`. `null` quando não se sabe: **não preencha por estimativa**.
- Para registrar uma troca de ministro, feche a ocupação atual com `valido_ate` e acrescente a nova
  com `valido_de` (as datas do ato no DOU). O validador acusa titulares com períodos sobrepostos.
- Depois de editar: `python -m etl validar`. No GitHub, o push já roda a validação e republica o site.

Para colocar um novo ministério no painel: acrescente-o em `ministerios.yaml` com `no_painel: true`,
`cod_siorg` e `orgao_orcamentario`, e as correspondências de UO. A próxima coleta traz o resto.

## Documentação

- [docs/DADOS.md](docs/DADOS.md): dicionário de dados e origem de cada campo
- [docs/DECISOES.md](docs/DECISOES.md): decisões técnicas, limitações conhecidas e roteiro
- [docs/fontes-dados-ministerios.md](docs/fontes-dados-ministerios.md) e
  [docs/estrutura-ministerios-referencia.md](docs/estrutura-ministerios-referencia.md): material de referência
