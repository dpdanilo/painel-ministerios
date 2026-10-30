<script>
  import { carregarIndice } from "../lib/dados.js";
  import { href, rota, trocarParams } from "../lib/estado.svelte.js";
  import { brlCompacto, num, pct, data as fmtData, normalizar, partidoSigla, partidoDetalhe, duracao, mesAno } from "../lib/formato.js";
  import { CATEGORIAS, METRICAS, somarGoverno, execucao, ordenar, porPartido, rotatividadeGoverno, SEM_CANDIDATURA } from "../lib/governo.js";
  import LinhaMinistros from "../components/LinhaMinistros.svelte";
  import MapaExecutivo from "../components/MapaExecutivo.svelte";
  import BotaoCsv from "../components/BotaoCsv.svelte";

  let idx = $state(null);
  let erro = $state(null);
  carregarIndice().then((d) => (idx = d), (e) => (erro = e));

  let metrica = $derived(METRICAS.find((m) => m.id === rota.params.metrica) ?? METRICAS[0]);
  let categoria = $derived(rota.params.cat || "");
  let filtro = $state("");
  let ordem = $state({ col: "orc_sem_oe", desc: true });
  let selecionados = $state(new Set());

  const COLUNAS = [
    { id: "nome", nome: "Órgão", chave: (m) => m.nome },
    { id: "secretarias", nome: "Órgãos finalísticos", chave: (m) => m.n_secretarias, num: true },
    { id: "unidades", nome: "Unidades", chave: (m) => m.n_unidades, num: true },
    { id: "cargos", nome: "Cargos", chave: (m) => m.n_cargos, num: true },
    { id: "orc_sem_oe", nome: "Orçamento*", chave: (m) => m.orcamento_sem_oe?.dotacao_atual ?? null, num: true, brl: true },
    { id: "exec", nome: "% pago*", chave: execucao, num: true },
    { id: "orc", nome: "Orçamento total", chave: (m) => m.orcamento?.dotacao_atual ?? null, num: true, brl: true },
  ];

  let todos = $derived(idx?.ministerios ?? []);
  let doFiltro = $derived(todos.filter((m) => (!categoria || m.categoria === categoria)
    && (!filtro || normalizar(`${m.nome} ${m.sigla} ${m.ministro?.nome ?? ""}`).includes(normalizar(filtro)))));
  let lista = $derived(ordenar(doFiltro, COLUNAS.find((c) => c.id === ordem.col).chave, ordem.desc));
  let tot = $derived(somarGoverno(todos.filter((m) => !categoria || m.categoria === categoria)));
  let partidos = $derived(porPartido(todos.filter((m) => !categoria || m.categoria === categoria)));
  let maxPartido = $derived(Math.max(1, ...partidos.map((p) => p.n)));
  let maxOrcPartido = $derived(Math.max(1, ...partidos.map((p) => p.orcamento)));
  let rot = $derived(rotatividadeGoverno(todos.filter((m) => !categoria || m.categoria === categoria)));
  let mesSiape = $derived(idx?.fontes.siape?.data_referencia?.slice(0, 7));
  let contagem = $derived(Object.fromEntries(Object.keys(CATEGORIAS).map((c) => [c, todos.filter((m) => m.categoria === c).length])));

  function ordenarPor(col) {
    ordem = { col, desc: ordem.col === col ? !ordem.desc : col !== "nome" };
  }
  function alternarSel(id) {
    const s = new Set(selecionados);
    s.has(id) ? s.delete(id) : s.size < 6 && s.add(id);
    selecionados = s;
  }
  const colunasCsv = [
    { chave: "sigla", titulo: "Sigla" }, { chave: "nome", titulo: "Órgão" }, { chave: "cat", titulo: "Categoria" },
    { chave: "ministro", titulo: "Titular" }, { chave: "partido", titulo: "Partido do titular (última candidatura, TSE)" }, { chave: "n_secretarias", titulo: "Órgãos finalísticos (1º nível)" },
    { chave: "n_unidades", titulo: "Unidades" }, { chave: "n_cargos", titulo: "Cargos e funções" },
    { chave: "dot", titulo: "Dotação atual (R$)" }, { chave: "pago", titulo: "Pago (R$)" },
    { chave: "dot_sem", titulo: "Dotação atual sem operações especiais (R$)" }, { chave: "pago_sem", titulo: "Pago sem operações especiais (R$)" },
  ];
  const linhasCsv = () => lista.map((m) => ({
    ...m, cat: CATEGORIAS[m.categoria]?.nome, ministro: m.ministro?.nome, partido: partidoSigla(m.ministro?.partido),
    dot: m.orcamento?.dotacao_atual, pago: m.orcamento?.pago, dot_sem: m.orcamento_sem_oe?.dotacao_atual, pago_sem: m.orcamento_sem_oe?.pago,
  }));
</script>

<div class="conteudo">
  <section class="intro">
    <h1>Como o Governo Federal se organiza</h1>
    <p class="sec">Ministérios e órgãos com status de ministério: estrutura, cargos e orçamento, a partir dos dados oficiais do SIORG e do Portal da Transparência.</p>
  </section>

  {#if erro}
    <p role="alert">{erro.message}</p>
  {:else if !idx}
    <p class="mudo" role="status">Carregando…</p>
  {:else}
    <div class="filtros">
      <div class="segmentado" role="group" aria-label="Tipo de órgão">
        <button type="button" aria-pressed={!categoria} onclick={() => trocarParams({ cat: null })}>Todos ({todos.length})</button>
        {#each Object.entries(CATEGORIAS) as [id, c] (id)}
          <button type="button" aria-pressed={categoria === id} onclick={() => trocarParams({ cat: id })}>{c.nome} ({contagem[id]})</button>
        {/each}
      </div>
    </div>

    <div class="tiles">
      <div class="tile hero"><div class="rot">Órgãos com status de ministério</div><div class="val num">{tot.n}</div></div>
      <div class="tile"><div class="rot">Unidades</div><div class="val num">{num(tot.unidades)}</div><div class="det">secretarias, departamentos, coordenações…</div></div>
      <div class="tile"><div class="rot">Cargos e funções</div><div class="val num">{num(tot.cargos)}</div><div class="det">CCE, FCE e Ministros</div></div>
      <div class="tile"><div class="rot">Orçamento {idx.exercicio}*</div><div class="val num">{brlCompacto(tot.dotacao_sem_oe)}</div><div class="det">{pct(tot.pago_sem_oe, tot.dotacao_sem_oe)} pago · total com op. especiais: {brlCompacto(tot.dotacao)}</div></div>
    </div>
    <p class="mudo nota">* Sem operações especiais: dívida pública, transferências constitucionais a estados e municípios, sentenças judiciais e outros encargos. Essas despesas são enormes (só a dívida passa de R$ 3 tri) e esconderiam as diferenças entre ministérios.</p>

    <section class="cartao" aria-labelledby="t-mapa">
      <div class="cab-secao">
        <h2 id="t-mapa">Mapa do Executivo</h2>
        <div class="segmentado" role="group" aria-label="Medida do mapa">
          {#each METRICAS as mt (mt.id)}
            <button type="button" aria-pressed={metrica.id === mt.id} title={mt.dica} onclick={() => trocarParams({ metrica: mt.id })}>{mt.nome}</button>
          {/each}
        </div>
      </div>
      <p class="sec pequeno">{metrica.dica}. Cada retângulo é proporcional ao valor. Clique para abrir o órgão.</p>
      <MapaExecutivo ministerios={doFiltro} {metrica} />
    </section>

    <section class="cartao" aria-labelledby="t-lista">
      <div class="cab-secao">
        <h2 id="t-lista">Todos os órgãos</h2>
        <div class="acoes-lista">
          <a class="botao" class:desligado={selecionados.size < 2} aria-disabled={selecionados.size < 2}
            href={selecionados.size >= 2 ? href(["comparar"], { m: [...selecionados].join(",") }) : undefined}>
            Comparar selecionados ({selecionados.size})
          </a>
          <BotaoCsv arquivo={`orgaos-${idx.exercicio}.csv`} colunas={colunasCsv} linhas={linhasCsv} />
        </div>
      </div>
      <div class="filtros">
        <label>Filtrar
          <input type="search" bind:value={filtro} placeholder="Nome, sigla ou titular" />
        </label>
      </div>
      <p class="mudo pequeno">Marque de 2 a 6 órgãos para comparar. Clique no título de uma coluna para ordenar. Órgãos finalísticos = secretarias e demais órgãos específicos singulares do 1º nível.</p>
      <div class="tabela-rolagem">
        <table>
          <thead>
            <tr>
              <th><span class="sr-only">Selecionar</span></th>
              {#each COLUNAS as c (c.id)}
                <th class:num={c.num} aria-sort={ordem.col === c.id ? (ordem.desc ? "descending" : "ascending") : undefined}>
                  <button type="button" class="ord" onclick={() => ordenarPor(c.id)}>{c.nome}{ordem.col === c.id ? (ordem.desc ? " ↓" : " ↑") : ""}</button>
                </th>
              {/each}
            </tr>
          </thead>
          <tbody>
            {#each lista as m (m.id)}
              <tr>
                <td><input type="checkbox" checked={selecionados.has(m.id)} onchange={() => alternarSel(m.id)}
                  disabled={!selecionados.has(m.id) && selecionados.size >= 6} aria-label={`Comparar ${m.sigla}`} /></td>
                <td>
                  <a href={href(["m", m.id, "estrutura"])}><strong>{m.sigla}</strong></a> <span class="sec">{m.nome}</span>
                  {#if m.ministro}<div class="mudo pequeno">{m.ministro.nome} · <span title={partidoDetalhe(m.ministro.partido)}>{partidoSigla(m.ministro.partido) ?? "sem candidatura"}</span></div>{/if}
                </td>
                <td class="num">{m.n_secretarias}</td>
                <td class="num">{num(m.n_unidades)}</td>
                <td class="num">{num(m.n_cargos)}</td>
                <td class="num">{m.orcamento_sem_oe ? brlCompacto(m.orcamento_sem_oe.dotacao_atual) : "—"}</td>
                <td class="num">{execucao(m) == null ? "—" : pct(execucao(m), 1)}</td>
                <td class="num mudo">{m.orcamento ? brlCompacto(m.orcamento.dotacao_atual) : "na Presidência"}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </section>

    <section class="cartao" aria-labelledby="t-partidos">
      <h2 id="t-partidos">Ministérios por partido</h2>
      <p class="sec pequeno">Partido de cada titular na sua candidatura mais recente registrada no TSE (2018 a 2026). “Sem candidatura” reúne quem nunca disputou eleição nesse período (em geral, quadros técnicos); não quer dizer que não tenha partido.</p>
      <div class="tabela-rolagem">
        <table class="partidos">
          <thead><tr><th>Partido</th><th>Órgãos</th><th class="barra-col"><span class="sr-only">Gráfico</span></th><th class="num">Orçamento*</th><th class="num">Cargos</th></tr></thead>
          <tbody>
            {#each partidos as p (p.sigla)}
              <tr class:sem={p.sigla === SEM_CANDIDATURA}>
                <th scope="row">{p.sigla}</th>
                <td class="num">{p.n}</td>
                <td class="barra-col">
                  <span class="barra" style="width: {(100 * p.n) / maxPartido}%"></span>
                  <span class="orgaos mudo">{p.orgaos.join(", ")}</span>
                </td>
                <td class="num">{brlCompacto(p.orcamento)}</td>
                <td class="num">{num(p.cargos)}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
      <p class="mudo pequeno">* Orçamento sem operações especiais dos órgãos que o partido comanda. Órgãos da Presidência entram na contagem, mas sem orçamento próprio.</p>
    </section>

    <section class="cartao" aria-labelledby="t-rot">
      <h2 id="t-rot">Quem comandou cada ministério desde 2023</h2>
      <div class="tiles">
        <div class="tile"><div class="rot">Trocas de ministro</div><div class="val num">{rot.trocas}</div><div class="det">{rot.mandatos} mandatos desde jan/2023</div></div>
        <div class="tile"><div class="rot">Tempo médio de ministro</div><div class="val">{duracao(rot.meses_medio)}</div><div class="det">inclui quem ainda está no cargo</div></div>
        <div class="tile"><div class="rot">Trocas de secretário</div><div class="val num">{num(rot.trocas_secretarios)}</div><div class="det">cargos CCE/FCE 1.17 e 1.18</div></div>
        <div class="tile"><div class="rot">Tempo médio de secretário</div><div class="val">{duracao(rot.meses_medio_secretario)}</div></div>
      </div>
      {#if mesSiape}
        <div class="espaco"><LinhaMinistros ministerios={doFiltro} fim={mesSiape} /></div>
        <p class="mudo pequeno">Fonte: cadastro mensal de servidores (SIAPE, Portal da Transparência), dados até {mesAno(mesSiape)}. O início é a data de ingresso no cargo; a saída é aproximada (1º mês em que a pessoa já não aparece). Partidos: TSE.</p>
      {/if}
    </section>

    <div>
      <section class="cartao">
        <h2>Fontes e atualização</h2>
        <ul class="fontes">
          {#each Object.entries(idx.fontes) as [id, f] (id)}
            <li><a href={f.url} target="_blank" rel="noopener">{f.nome}</a>{#if f.data_referencia}<span class="mudo"> · dados de {fmtData(f.data_referencia)}</span>{/if}</li>
          {/each}
        </ul>
        <p class="mudo pequeno">Página gerada em {fmtData(idx.gerado_em)}. Dados que dependem de leitura humana aparecem marcados como <span class="chip">curado</span>.</p>
      </section>
    </div>
  {/if}
</div>

<style>
  .intro { margin: 8px 0 20px; max-width: 760px; }
  .intro h1 { font-size: clamp(1.5rem, 4vw, 2.1rem); margin: 0 0 8px; }
  .intro p { margin: 0; font-size: 1.02rem; }
  .nota { font-size: 0.8rem; margin: 10px 0 16px; max-width: 900px; }
  .cartao { margin-top: 16px; }
  .pequeno { font-size: 0.8rem; margin: 2px 0 10px; }
  .acoes-lista { display: flex; flex-wrap: wrap; gap: 8px; }
  .desligado { opacity: 0.5; pointer-events: none; }
  td .pequeno { margin: 2px 0 0; }
  .fontes { margin: 0; padding-left: 20px; }
  .fontes li { margin-bottom: 6px; }
  input[type="checkbox"] { width: 18px; height: 18px; accent-color: var(--marca); }
  .partidos th[scope="row"] { font-weight: 700; text-transform: none; letter-spacing: 0; font-size: 0.9rem; color: var(--texto); white-space: nowrap; }
  .partidos .barra-col { width: 60%; min-width: 160px; }
  .partidos .barra { display: block; height: 12px; background: var(--series-1); border-radius: 0 4px 4px 0; min-width: 2px; }
  .partidos tr.sem .barra { background: var(--eixo); }
  .partidos .orgaos { display: block; font-size: 0.75rem; margin-top: 3px; }
  .espaco { margin-top: 16px; }
</style>
