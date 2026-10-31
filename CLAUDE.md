# Estrutura dos Ministérios — memória do projeto

Respostas sempre em **português do Brasil**, em linguagem simples. O dono não é programador: explique o que mudou e o que ele precisa fazer, sem jargão.
Ao abrir a sessão, leia também o `STATUS.md` (onde paramos). Ao terminar, rode `/salvar`.

## O que é
Painel estático da estrutura do Poder Executivo Federal: 31 ministérios + 7 órgãos com status de ministério, com estrutura (SIORG), ocupantes (SIAPE), partidos (TSE), orçamento (Portal da Transparência), políticas públicas e série histórica desde 2003.
Site: https://dpdanilo.github.io/painel-ministerios/ · Repositório: `dpdanilo/painel-ministerios` (público).

## Arquitetura
```
SIORG · Transparência · SIAPE · TSE · IPCA ─► etl/ (Python) ─► data/normalizado (no git) ─► etl publicar ─► site/public/data/*.json ─► Vite/Svelte ─► GitHub Pages
                                    ▲
                     data/curadoria/*.yaml (manual, toda linha com fonte)
```
- O navegador **nunca** chama APIs do governo. A coleta roda no GitHub Actions.
- `etl/`: um módulo por fonte (`siorg.py`, `orcamento.py`, `servidores.py`, `tse.py`, `historico.py`), mais `correspondencia.py` (UO ↔ SIORG), `versionamento.py` (vigência por comparação de snapshots), `validar.py` e `publicar.py`.
- `site/src/`: `App.svelte`, `components/` (uma tela por componente) e `lib/` (lógica pura, testada em `lib.test.js`). Estado da tela na URL (`#/m/<id>/<aba>?...`).
- `.github/workflows/atualizar.yml`: orçamento às segundas; SIORG no dia 3; SIAPE e TSE no dia 12; anos anteriores e IPCA no dia 20. Só faz commit (`Dados: ...`) se o hash mudou. Falhas e pontos de curadoria abrem issue.
- `.github/workflows/publicar.yml`: testes + build + deploy (reutilizável, chamado pelo atualizar).

## Comandos
```bash
.venv/Scripts/activate
python -m etl atualizar      # coleta tudo (1ª vez ~4 GB do SIAPE)
python -m etl validar
python -m etl publicar
python -m pytest -q
cd site && npm run dev       # http://localhost:5173/painel-ministerios/
cd site && npm test && npm run build
```

## Regras
- **Toda linha de curadoria precisa de `fonte`.** Data desconhecida = `null`; **nunca preencher por estimativa**.
- Decisões técnicas, limitações e roteiro ficam em `docs/DECISOES.md`, com uma seção por fase. Dicionário de dados em `docs/DADOS.md`.
- O vermelho da marca (`#d21212`) só na interface, nunca numa série de dados. Paleta dos gráficos validada para daltonismo.
- Nenhum secret é necessário. Se precisar da chave do Portal: `gh secret set TRANSPARENCIA_API_KEY`, nunca em arquivo.
- Commit e push só com a confirmação do dono.

## Integrações
Este projeto se conecta a outros. Contratos em `../_hub/INTEGRACOES.md`:
- **C3:** a página inicial do `vira-2026` tem um botão para o site deste painel. Se o endereço mudar, avise o hub.
- Usa a mesma fonte do TSE (`consulta_cand`) que o Painel Eleitoral, mas com cópia própria (`data/bruto/tse`).
- Mesma identidade visual do `vira-2026` (vermelho, Montserrat/Public Sans).
Convenções comuns: `../_hub/CONVENCOES.md`.
