# Estrutura dos Ministérios

Painel da estrutura do Poder Executivo Federal: secretarias, departamentos, cargos, ocupantes,
competências, orçamento e políticas públicas de cada ministério, a partir de dados oficiais.

**Site:** https://dpdanilo.github.io/painel-ministerios/

Cobre os 31 ministérios e os 7 órgãos com status de ministério (Casa Civil, Secretaria-Geral, SRI, Secom,
GSI, AGU e CGU), com visão de governo e comparação. As próximas fases estão em
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
- O GitHub Actions atualiza sozinho: orçamento toda segunda, estrutura (SIORG) todo dia 3 e ocupantes
  (SIAPE) + partidos (TSE) todo dia 12, orçamento de anos anteriores + IPCA todo dia 20 e o Diário Oficial
  (nomeações, exonerações e decretos de estrutura) todo dia às 07h30. Só faz commit e deploy se algo mudou.
- Falhas de coleta e pontos de curadoria abrem uma *issue* automaticamente. Troca de ministro, nomeação para
  cargo de Natureza Especial e decreto de estrutura publicados no DOU abrem a issue "DOU <data>: atos para revisão".

## Rodar localmente

Requisitos: Python 3.12+ e Node 22+.

```bash
python -m venv .venv
.venv/Scripts/activate          # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt

python -m etl atualizar         # baixa SIORG, orçamento, SIAPE e TSE (na 1ª vez, ~4 GB: 44 meses do SIAPE)
python -m etl validar           # confere curadoria e dados
python -m etl publicar          # gera site/public/data/
python -m pytest -q             # testes do ETL

cd site
npm install
npm run dev                     # http://localhost:5173/painel-ministerios/
npm test && npm run build       # testes do front-end e build de produção
```

Outros comandos: `python -m etl coletar siorg`, `python -m etl normalizar orcamento --exercicio 2025`,
`python -m etl correspondencias` (sugere a ligação UO ↔ SIORG para unidades orçamentárias novas; também roda
sozinho a cada atualização do orçamento).

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
| `ocupacoes.yaml` | acréscimos manuais de ocupantes (a fonte principal é o SIAPE, automática) |
| `pessoas.yaml` | filiação partidária informada à mão (prevalece sobre o TSE) |
| `orgaos_siape.yaml` | órgão do SIAPE ↔ ministério, quando o nome não bate automaticamente |
| `politicas_publicas.yaml` | nome conhecido da política ↔ ações/programas do orçamento, com justificativa |
| `eventos_institucionais.yaml` | criações, extinções, fusões, desmembramentos e recriações desde 2003, cada um com a norma |
| `normas.yaml` | leis, decretos e MPs citados |
| `totais_referencia.yaml` | totais publicados por terceiros, para conferir o orçamento coletado |

Regras:
- **Toda linha precisa de `fonte`.** O validador recusa linha sem fonte.
- Datas em `AAAA-MM-DD`. `null` quando não se sabe: **não preencha por estimativa**.
- Trocas de ministro e secretário entram sozinhas pelo SIAPE, com ~2 meses de atraso. Para mostrar antes
  uma nomeação já publicada no DOU, acrescente-a em `ocupacoes.yaml` com a fonte. Ela some quando o SIAPE a trouxer.
- Depois de editar: `python -m etl validar`. No GitHub, o push já roda a validação e republica o site.

Para colocar um novo ministério no painel: acrescente-o em `ministerios.yaml` com `no_painel: true`,
`categoria`, `cod_siorg` e `orgao_orcamentario`. A próxima coleta traz o resto, e as correspondências de UO
são sugeridas automaticamente (`metodo: automatico_nome`). Revise as que ficarem com `cod_siorg: null`
e troque o método para `manual` quando corrigir uma linha.

## Documentação

- [docs/DADOS.md](docs/DADOS.md): dicionário de dados e origem de cada campo
- [docs/DECISOES.md](docs/DECISOES.md): decisões técnicas, limitações conhecidas e roteiro
- [docs/fontes-dados-ministerios.md](docs/fontes-dados-ministerios.md) e
  [docs/estrutura-ministerios-referencia.md](docs/estrutura-ministerios-referencia.md): material de referência
