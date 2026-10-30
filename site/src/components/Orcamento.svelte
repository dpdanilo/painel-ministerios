<script>
  import { rota, trocarParams } from "../lib/estado.svelte.js";
  import { linhas, somar, agrupar, acumuladoMensal } from "../lib/orcamento.js";
  import { brlCompacto, brl, pct, capitalizar, data as fmtData } from "../lib/formato.js";
  import BotaoCsv from "./BotaoCsv.svelte";
  import Fonte from "./Fonte.svelte";
  import ExecucaoMensal from "./ExecucaoMensal.svelte";

  let { m } = $props();
  let orc = $derived(m.orcamento);

  let filtro = $derived({ uo: rota.params.uo || "", prog: rota.params.prog || "" });
  let semOE = $derived(rota.params.oe === "0");
  let oe = $derived(new Set(semOE ? orc?.operacoes_especiais ?? [] : []));
  let destaque = $derived(rota.params.acao || "");
  let base = $derived(linhas(orc, filtro).filter((l) => !oe.has(l.programa)));
  let tot = $derived(somar(base));
  let programas = $derived(agrupar(linhas(orc, { uo: filtro.uo }).filter((l) => !oe.has(l.programa)), "programa"));
  let acoes = $derived(agrupar(base, "acao"));
  let maxProg = $derived(Math.max(1, ...programas.map((p) => Math.max(p.dotacao_atual, p.empenhado))));
  // A série mensal publicada é por programa (soma todas as UOs).
  let serie = $derived(acumuladoMensal(orc, { prog: filtro.prog, excluir: oe }));
  let programaDaAcao = $derived(Object.fromEntries(orc ? orc.linhas.map((l) => [l[2], l[1]]) : []));

  $effect(() => {
    if (destaque) requestAnimationFrame(() => document.getElementById(`acao-${destaque}`)?.scrollIntoView({ block: "center" }));
  });

  const colunasCsv = [
    { chave: "codigo", titulo: "Ação" }, { chave: "nome", titulo: "Nome" }, { chave: "programa", titulo: "Programa" },
    { chave: "dotacao_inicial", titulo: "Dotação inicial (R$)" }, { chave: "dotacao_atual", titulo: "Dotação atual (R$)" },
    { chave: "empenhado", titulo: "Empenhado (R$)" }, { chave: "liquidado", titulo: "Liquidado (R$)" },
    { chave: "pago", titulo: "Pago (R$)" }, { chave: "empenhado_emendas", titulo: "Empenhado por emendas (R$)" },
  ];
  const linhasCsv = () => acoes.map((a) => ({ ...a, nome: orc.acoes[a.codigo], programa: programaDaAcao[a.codigo] }));
</script>

{#if !orc}
  <section class="cartao">
    {#if m.categoria === "presidencia"}
      <p>O orçamento deste órgão não é separado: fica consolidado na unidade orçamentária 20101, “Presidência da República”, junto com os demais órgãos da Presidência.</p>
    {:else}
      <p>Orçamento ainda não coletado para este órgão.</p>
    {/if}
  </section>
{:else}
  <div class="filtros">
    <label>Unidade orçamentária
      <select value={filtro.uo} onchange={(e) => trocarParams({ uo: e.currentTarget.value })}>
        <option value="">Todas ({Object.keys(orc.uos).length})</option>
        {#each Object.entries(orc.uos) as [c, u] (c)}<option value={c}>{c} – {capitalizar(u.nome)}</option>{/each}
      </select>
    </label>
    <label>Programa
      <select value={filtro.prog} onchange={(e) => trocarParams({ prog: e.currentTarget.value, acao: null })}>
        <option value="">Todos</option>
        {#each Object.entries(orc.programas) as [c, n] (c)}<option value={c}>{c} – {capitalizar(n)}</option>{/each}
      </select>
    </label>
    {#if orc.operacoes_especiais?.length}
      <label class="caixa"><input type="checkbox" checked={semOE} onchange={(e) => trocarParams({ oe: e.currentTarget.checked ? "0" : null, prog: null })} />
        <span>Sem operações especiais <span class="mudo">(dívida, transferências, sentenças)</span></span></label>
    {/if}
    {#if filtro.uo || filtro.prog}
      <button type="button" class="botao" onclick={() => trocarParams({ uo: null, prog: null, acao: null })}>Limpar filtros</button>
    {/if}
  </div>

  <div class="tiles">
    <div class="tile hero"><div class="rot">Dotação atual {orc.exercicio}</div><div class="val num">{brlCompacto(tot.dotacao_atual)}</div><div class="det">inicial (LOA): {brlCompacto(tot.dotacao_inicial)}</div></div>
    <div class="tile"><div class="rot">Empenhado</div><div class="val num">{brlCompacto(tot.empenhado)}</div><div class="det">{pct(tot.empenhado, tot.dotacao_atual)} da dotação</div></div>
    <div class="tile"><div class="rot">Liquidado</div><div class="val num">{brlCompacto(tot.liquidado)}</div><div class="det">{pct(tot.liquidado, tot.dotacao_atual)} da dotação</div></div>
    <div class="tile"><div class="rot">Pago</div><div class="val num">{brlCompacto(tot.pago)}</div><div class="det">{pct(tot.pago, tot.dotacao_atual)} da dotação</div></div>
    <div class="tile"><div class="rot">Empenhado via emendas</div><div class="val num">{brlCompacto(tot.empenhado_emendas)}</div><div class="det">{pct(tot.empenhado_emendas, tot.empenhado)} do empenhado</div></div>
  </div>
  <p class="mudo nota">Dotação = quanto a lei autoriza gastar. Empenhado = valor reservado em contrato ou convênio. Liquidado = entrega verificada. Pago = dinheiro que saiu. Fundos como FGTS, FAR e FDS financiam boa parte da habitação fora deste orçamento.</p>

  <section class="cartao" aria-labelledby="t-prog">
    <h2 id="t-prog">Execução por programa</h2>
    <div class="legenda" aria-hidden="true">
      <span><i style="background: var(--etapa-1)"></i>Dotação atual</span>
      <span><i style="background: var(--etapa-2)"></i>Empenhado</span>
      <span><i style="background: var(--etapa-3)"></i>Pago</span>
    </div>
    <ul class="programas">
      {#each programas as p (p.codigo)}
        <li class:ativo={filtro.prog === p.codigo}>
          <button type="button" onclick={() => trocarParams({ prog: filtro.prog === p.codigo ? null : p.codigo, acao: null })}
            aria-pressed={filtro.prog === p.codigo}
            title={`Dotação ${brl(p.dotacao_atual)} · Empenhado ${brl(p.empenhado)} · Pago ${brl(p.pago)}`}>
            <span class="rotulo"><span class="mudo num">{p.codigo}</span> {capitalizar(orc.programas[p.codigo])}</span>
            <span class="barra" aria-hidden="true">
              <span style="width: {(100 * p.dotacao_atual) / maxProg}%; background: var(--etapa-1)"></span>
              <span style="width: {(100 * p.empenhado) / maxProg}%; background: var(--etapa-2)"></span>
              <span style="width: {(100 * p.pago) / maxProg}%; background: var(--etapa-3)"></span>
            </span>
            <span class="valores num">{brlCompacto(p.pago)} pagos de {brlCompacto(p.dotacao_atual)} <span class="mudo">({pct(p.pago, p.dotacao_atual)})</span></span>
          </button>
        </li>
      {/each}
    </ul>
    <p class="mudo pequeno">Clique num programa para filtrar a página.</p>
  </section>

  <section class="cartao" aria-labelledby="t-mes">
    <h2 id="t-mes">Execução acumulada no ano{filtro.prog ? ` – programa ${filtro.prog}` : ""}</h2>
    {#if filtro.uo}<p class="mudo pequeno">A série mensal soma todas as UOs do ministério.</p>{/if}
    <ExecucaoMensal {serie} dotacao={filtro.uo ? null : tot.dotacao_atual} />
  </section>

  <section class="cartao" aria-labelledby="t-acoes">
    <div class="titulo-linha">
      <h2 id="t-acoes">Ações orçamentárias ({acoes.length})</h2>
      <BotaoCsv arquivo={`${m.id}-orcamento-${orc.exercicio}${filtro.prog ? "-" + filtro.prog : ""}.csv`} colunas={colunasCsv} linhas={linhasCsv} />
    </div>
    <div class="tabela-rolagem">
      <table>
        <thead>
          <tr><th>Ação</th><th class="num">Dotação atual</th><th class="num">Empenhado</th><th class="num">Liquidado</th><th class="num">Pago</th><th class="num">% pago</th></tr>
        </thead>
        <tbody>
          {#each acoes as a (a.codigo)}
            <tr id={`acao-${a.codigo}`} class:destaque={destaque === a.codigo}>
              <td><span class="mudo num">{a.codigo}</span> {capitalizar(orc.acoes[a.codigo])}</td>
              <td class="num">{brlCompacto(a.dotacao_atual)}</td>
              <td class="num">{brlCompacto(a.empenhado)}</td>
              <td class="num">{brlCompacto(a.liquidado)}</td>
              <td class="num">{brlCompacto(a.pago)}</td>
              <td class="num">{pct(a.pago, a.dotacao_atual)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
    <Fonte fonte={m.fontes.orcamento} rotuloData="Dados de" />
    <p class="mudo pequeno">Extração de {fmtData(orc.data_extracao)}. Empenhado, liquidado e pago somam os lançamentos mensais do ano; a dotação vem do arquivo anual.</p>
  </section>
{/if}

<style>
  .nota { font-size: 0.82rem; margin: 10px 0 16px; max-width: 880px; }
  .caixa { display: flex !important; flex: 0 1 auto !important; align-items: center; gap: 8px; min-height: 38px; font-size: 0.88rem !important; }
  .caixa input { width: 18px; height: 18px; accent-color: var(--marca); }
  .cartao { margin-top: 16px; }
  .titulo-linha { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 8px; margin-bottom: 8px; }
  .titulo-linha h2 { margin: 0; }
  .legenda { display: flex; flex-wrap: wrap; gap: 14px; font-size: 0.82rem; color: var(--sec); margin-bottom: 10px; }
  .legenda i { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 6px; vertical-align: -1px; }
  .programas { list-style: none; margin: 0; padding: 0; display: grid; gap: 4px; }
  .programas button { width: 100%; background: none; border: 1.5px solid transparent; border-radius: 10px; padding: 8px 10px; cursor: pointer; text-align: left; display: grid; gap: 4px; }
  .programas button:hover { background: var(--cartao-2); }
  .programas li.ativo button { border-color: var(--marca); }
  .rotulo { font-size: 0.9rem; font-weight: 600; }
  .barra { position: relative; height: 14px; display: block; }
  .barra span { position: absolute; left: 0; top: 0; bottom: 0; border-radius: 0 4px 4px 0; min-width: 2px; }
  .barra span:nth-child(2) { top: 2px; bottom: 2px; }
  .barra span:nth-child(3) { top: 4px; bottom: 4px; }
  .valores { font-size: 0.82rem; color: var(--sec); }
  tr.destaque td { background: var(--cartao-2); box-shadow: inset 0 -2px 0 var(--marca); }
  .pequeno { font-size: 0.8rem; margin: 8px 0 0; }
</style>
