# Fontes de Dados sobre Ministérios — Guia de Uso

> Contexto para construção de um painel. Complementa `estrutura-ministerios-referencia.md`.
> Lista as fontes por tipo de informação, a forma de acesso e como integrá-las.
> Endpoints e regras de acesso mudam: sempre confirme na documentação oficial antes de codificar.

---

## 1. Visão geral

| Tipo de dado | Fonte principal | Acesso | Automação |
|---|---|---|---|
| Estrutura organizacional e cargos | SIORG (MGI) | API REST pública + CSV | Alta |
| Estrutura + pessoal consolidado | Raio-X da APF (MGI) | Painel + CSV | Média |
| Titulares, competências descritivas | Sites gov.br dos ministérios | HTML | Baixa (manual) |
| Legislação (leis, decretos) | LexML / Câmara / Planalto | API SRU / HTML / PDF | Média |
| Atos infralegais (portarias, nomeações) | Diário Oficial da União | HTML / XML (INLABS) | Média |
| Despesas e execução | Portal da Transparência (CGU) | API REST com chave | Alta |
| Dotação orçamentária (LOA) | SIOP / Painel do Orçamento (MPO) | Painel + exportação | Média |
| Séries históricas e emendas | Siga Brasil (Senado) | Painel + exportação | Média |
| Dados fiscais do Tesouro | Tesouro Transparente | Dados abertos (CKAN) | Alta |
| Atuação parlamentar | APIs da Câmara e do Senado | API REST pública | Alta |
| Controle externo | TCU | Pesquisa web / dados abertos | Baixa–Média |
| Catálogo geral | dados.gov.br | Portal + API | Média |

---

## 2. Estrutura organizacional

### 2.1 SIORG — fonte oficial (prioridade 1)
- **O que é:** sistema do MGI com a estrutura formal de órgãos da administração direta, autárquica e fundacional, incluindo cargos e funções por unidade.
- **Documentação:** https://api.siorg.economia.gov.br
- **Base da API:** https://estruturaorganizacional.dados.gov.br
- **Endpoints citados em fontes públicas:**
  - `/doc/estrutura-organizacional/resumida` — árvore resumida a partir de uma unidade (parâmetro de código da unidade)
  - `estrutura-organizacional/completa` — estrutura completa (também publicada como dataset mensal no dados.gov.br)
- **Datasets no dados.gov.br:** "Siorg - Estrutura Organizacional Completa" (atualização mensal) e "Siorg - distribuição dos cargos e funções".
- **Como usar:**
  1. Descubra o código SIORG do ministério (consulte a árvore a partir do Poder Executivo ou busque pelo nome).
  2. Busque a estrutura a partir desse código e monte a árvore pelos vínculos pai → filho.
  3. Classifique cada unidade nos 4 blocos (assistência direta, singulares, colegiados, vinculadas) usando o tipo/natureza informados.
  4. Cruze com o dataset de cargos para obter níveis CCE/FCE por unidade.
- **Cuidados:** reflete a estrutura formal (decreto + regimento); pode haver defasagem logo após um decreto novo.

### 2.2 Raio-X da Administração Pública Federal (MGI)
- Painel gerencial da Secretaria de Gestão e Inovação com download em CSV.
- Dicionário de dados: https://repositorio.dados.gov.br/seges/raio-x/dicionario-de-dados.odt
- **Uso:** dados de pessoal agregados por órgão; útil para indicadores (servidores, cargos, distribuição meio x fim).
- **Cuidado:** os dados abertos vêm mais desagregados que o painel; use o campo de órgão indicado no dicionário para bater com os números exibidos.

### 2.3 Sites dos ministérios (gov.br/[sigla])
- Seção "Institucional" ou "Composição": estrutura, competências, base jurídica, "Quem é Quem", perfis profissionais dos cargos.
- Exemplo: https://www.gov.br/cidades/pt-br/
- **Uso:** nomes de titulares e textos descritivos (não disponíveis no SIORG de forma estruturada).
- **Cuidado:** HTML sem padrão entre órgãos; prefira coleta manual ou semiautomática com revisão.

---

## 3. Legislação

### 3.1 LexML (prioridade para automação)
- Portal: https://www.lexml.gov.br
- Interface de busca SRU (consultas por tipo, número, data, órgão).
- **Uso:** localizar o decreto de estrutura vigente de cada ministério e a lei de organização (Lei 14.600/2023).

### 3.2 Portal de legislação da Câmara
- Versões "norma atualizada" em HTML/PDF (ex.: `www2.camara.leg.br/legin/fed/decret/...`).
- **Uso:** texto consolidado com alterações; boa alternativa quando o Planalto bloqueia acesso.

### 3.3 Planalto
- https://www.planalto.gov.br/ccivil_03/
- Texto oficial de referência.
- **Cuidado:** bloqueia requisições automatizadas. Use apenas para consulta manual/validação.

### 3.4 Diário Oficial da União
- https://www.in.gov.br — busca de portarias, regimentos internos, nomeações.
- INLABS (https://inlabs.in.gov.br) — download do DOU em XML, mediante cadastro.
- **Uso:** atualizar titulares e detectar mudanças de estrutura (regimentos internos são publicados aqui).

### Regras de leitura
- Estrutura regimental: procure "Aprova a Estrutura Regimental e o Quadro Demonstrativo dos Cargos..." + nome do ministério.
- O decreto mais recente revoga o anterior; confira a data de vigência (frequentemente diferente da publicação).
- Competências: art. 1º do Anexo I. Estrutura: art. 2º do Anexo I. Cargos: Anexo II.

---

## 4. Orçamento e execução

### 4.1 Portal da Transparência — API (CGU)
- Documentação (Swagger): https://api.portaldatransparencia.gov.br
- **Acesso:** chave gratuita obtida por cadastro de e-mail; enviada no header `chave-api-dados`.
- **Dados:** despesas por órgão, convênios e transferências, servidores, contratos.
- **Cuidados:** há limite de requisições por minuto (consulte a documentação); implemente cache e retentativas; respostas paginadas.

### 4.2 SIOP e Painel do Orçamento Federal (MPO)
- https://www.siop.planejamento.gov.br (acesso público ao painel)
- **Dados:** dotação inicial, dotação atual, empenhado, liquidado, pago — por órgão, unidade orçamentária, programa e ação.
- **Uso:** exportar consultas em planilha/CSV e carregar no painel.
- **Chave de cruzamento:** código do órgão orçamentário / unidade orçamentária (UO). Confirme o código de cada ministério no próprio SIOP.

### 4.3 Siga Brasil (Senado)
- Painéis da Consultoria de Orçamentos do Senado com exportação.
- **Uso:** séries históricas, emendas parlamentares, comparações entre anos.
- Boletins de execução da CONORF trazem resumos por ministério.

### 4.4 Tesouro Transparente
- https://www.tesourotransparente.gov.br — portal de dados abertos (CKAN).
- **Uso:** resultado fiscal, execução financeira, transferências.

### 4.5 Câmara — Orçamento da União
- https://www2.camara.leg.br/orcamento-da-uniao
- LOA, PLOA e o "Raio-X do Orçamento" (PDF com totais por ministério).
- **Uso:** validação de totais da LOA.

### Regras de leitura do orçamento
- Diferencie **PLOA** (proposta) de **LOA** (aprovada) e de **dotação atual** (após créditos e bloqueios).
- Contingenciamentos e bloqueios alteram o valor disponível ao longo do ano.
- Fundos (FGTS, FAR, FDS etc.) podem não aparecer integralmente no orçamento do órgão.
- Sempre registre a data de extração dos dados.

---

## 5. Atuação parlamentar

### 5.1 API de Dados Abertos da Câmara
- https://dadosabertos.camara.leg.br/api/v2/
- Pública, sem chave. Proposições, requerimentos de informação, eventos (audiências e convocações de ministros).

### 5.2 Dados Abertos do Senado
- https://legis.senado.leg.br/dadosabertos/
- Pública, sem chave. Matérias, votações, comissões.

---

## 6. Controle e prestação de contas

- **TCU:** pesquisa de acórdãos e auditorias por órgão (portal do TCU) e conjuntos de dados abertos do tribunal.
- **Relatórios de Gestão:** no site de cada ministério, em "Transparência e Prestação de Contas" (PDF anual).
- **PPA 2024–2027:** programas e metas por ministério (MPO).

---

## 7. Catálogo geral — dados.gov.br
- https://dados.gov.br
- Reúne datasets de quase todas as fontes acima (SIORG, Raio-X, Tesouro etc.).
- Possui API de catálogo (verifique se exige token na versão atual).

---

## 8. Orientações de integração para o painel

### Arquitetura sugerida
1. **Coleta (ETL):** scripts por fonte, executados periodicamente, gravando dados brutos com data de extração.
2. **Normalização:** tabelas padronizadas (órgãos, unidades, cargos, orçamento, normas).
3. **Painel:** lê apenas os dados normalizados, nunca as APIs diretamente.

### Chaves de cruzamento
| Entidade | Chave | Fonte |
|---|---|---|
| Unidade organizacional | Código SIORG | SIORG |
| Órgão orçamentário / UO | Código do órgão / UO | SIOP, Portal da Transparência |
| Norma | Tipo + número + ano | LexML, Câmara |

Não existe chave única entre SIORG e orçamento: mantenha uma **tabela de correspondência** manual (código SIORG ↔ código do órgão orçamentário) para cada ministério.

### Frequência de atualização sugerida
| Dado | Frequência |
|---|---|
| Estrutura (SIORG) | Mensal |
| Execução orçamentária | Semanal ou mensal |
| LOA / dotação | Anual + após créditos/decretos de programação |
| Legislação / DOU | Semanal (para detectar novos decretos) |
| Titulares | Sob demanda / mensal |

### Boas práticas
- Guarde a chave da API do Portal da Transparência em variável de ambiente, nunca no código.
- Implemente cache local e respeite limites de requisição.
- Mostre no painel a fonte e a data de atualização de cada indicador.
- Trate a estrutura como versionada: um novo decreto muda a árvore; guarde snapshots por data.
- Valide totais orçamentários contra o Raio-X da Câmara ou o painel do SIOP.
- Não faça scraping automatizado do Planalto (bloqueio); use LexML ou Câmara.

### Modelo de dados mínimo (sugestão)
```json
{
  "orgao": {"codigo_siorg": "string", "sigla": "string", "nome": "string", "codigo_orcamentario": "string"},
  "unidade": {"codigo_siorg": "string", "codigo_pai": "string", "nome": "string", "bloco": "assistencia|singular|colegiado|vinculada", "tipo_atividade": "meio|fim"},
  "cargo": {"codigo_unidade": "string", "tipo": "CCE|FCE", "nivel": "string", "quantidade": 0},
  "orcamento": {"codigo_orcamentario": "string", "ano": 0, "dotacao_inicial": 0, "dotacao_atual": 0, "empenhado": 0, "liquidado": 0, "pago": 0, "data_extracao": "YYYY-MM-DD"},
  "norma": {"tipo": "Lei|Decreto|Portaria", "numero": "string", "ano": 0, "assunto": "string", "vigencia": "YYYY-MM-DD", "url": "string"}
}
```
