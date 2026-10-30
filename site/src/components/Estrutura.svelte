<script>
  import { SvelteSet } from "svelte/reactivity";
  import { rota, trocarParams } from "../lib/estado.svelte.js";
  import { BLOCOS, HIERARQUIA, caminho, cargosPorNivel } from "../lib/estrutura.js";
  import { num, pct } from "../lib/formato.js";
  import NoArvore from "./NoArvore.svelte";
  import DetalheUnidade from "./DetalheUnidade.svelte";
  import Fonte from "./Fonte.svelte";

  let { m, idx } = $props();

  const abertos = new SvelteSet();
  let selecionada = $derived(rota.params.u && idx.porCodigo.has(rota.params.u) ? rota.params.u : null);

  // Ao chegar por link/busca, abre o caminho até a unidade.
  $effect(() => {
    if (selecionada) for (const u of caminho(idx, selecionada).slice(0, -1)) abertos.add(u.c);
  });

  let nivel1 = $derived(idx.filhos.get(idx.raiz.c) || []);
  let porBloco = $derived(BLOCOS.map((b) => ({ ...b, unidades: nivel1.filter((u) => u.b === b.id) })).filter((b) => b.unidades.length));

  let totalCargos = $derived(Object.values(m.cargos).flat().reduce((s, c) => s + c[4], 0));
  let fim = $derived(m.unidades.filter((u) => u.a === "fim").length);
  let secretarias = $derived(nivel1.filter((u) => u.b === "singular").length);

  // Cargos de direção e assessoramento (CCE/FCE) por nível, do maior para o menor.
  let linhasNivel = $derived.by(() => {
    const porNivel = new Map();
    for (const [k, q] of cargosPorNivel(m)) {
      if (!/^(CCE|FCE) 1\./.test(k)) continue;
      const n = Number(k.split(".")[1]);
      const v = porNivel.get(n) || { n, CCE: 0, FCE: 0 };
      v[k.slice(0, 3)] += q;
      porNivel.set(n, v);
    }
    return [...porNivel.values()].sort((a, b) => b.n - a.n);
  });
  let maxNivel = $derived(Math.max(1, ...linhasNivel.map((v) => v.CCE + v.FCE)));

  function selecionar(cod) {
    trocarParams({ u: cod });
    if (matchMedia("(max-width: 899px)").matches) {
      requestAnimationFrame(() => document.getElementById("detalhe")?.scrollIntoView({ behavior: "smooth", block: "start" }));
    }
  }
  function alternar(cod) {
    abertos.has(cod) ? abertos.delete(cod) : abertos.add(cod);
  }
  function abrirTudo(valor) {
    if (!valor) return abertos.clear();
    for (const u of m.unidades) if (idx.filhos.has(u.c)) abertos.add(u.c);
  }
</script>

<div class="tiles">
  <div class="tile hero"><div class="rot">Órgãos finalísticos</div><div class="val num">{secretarias}</div><div class="det">secretarias e órgãos singulares do 1º nível</div></div>
  <div class="tile"><div class="rot">Unidades na estrutura</div><div class="val num">{num(m.unidades.length)}</div><div class="det">incluindo colegiados e vinculadas</div></div>
  <div class="tile"><div class="rot">Cargos e funções</div><div class="val num">{num(totalCargos)}</div><div class="det">CCE, FCE e Ministro</div></div>
  <div class="tile"><div class="rot">Unidades finalísticas</div><div class="val num">{pct(fim, m.unidades.length)}</div><div class="det">as demais são de suporte (atividade-meio)</div></div>
</div>

<div class="layout">
  <section class="cartao arvore" aria-labelledby="t-org">
    <div class="titulo-linha">
      <h2 id="t-org">Organograma</h2>
      <div class="controles">
        <button type="button" class="botao" onclick={() => abrirTudo(true)}>Abrir tudo</button>
        <button type="button" class="botao" onclick={() => abrirTudo(false)}>Fechar</button>
      </div>
    </div>
    <p class="sec dica">Toque numa unidade para ver cargos, titular e competências. Use ▸ para abrir os níveis abaixo.</p>

    <button type="button" class="raiz" class:sel={selecionada === idx.raiz.c} onclick={() => selecionar(idx.raiz.c)}>
      <strong>{idx.raiz.s}</strong> {idx.raiz.n}
    </button>

    {#each porBloco as b (b.id)}
      <div class="bloco">
        <h3>{b.nome}</h3>
        <p class="mudo resumo">{b.resumo}</p>
        <ul role="tree" aria-label={b.nome}>
          {#each b.unidades as u (u.c)}
            <NoArvore {u} {idx} {m} {abertos} {selecionada} {selecionar} {alternar} />
          {/each}
        </ul>
      </div>
    {/each}
    <Fonte fonte={m.fontes.estrutura} rotuloData="Coletado em" />
  </section>

  <div id="detalhe" class="detalhe">
    {#if selecionada}
      <DetalheUnidade cod={selecionada} {m} {idx} {selecionar} />
    {:else}
      <section class="cartao">
        <h2>Cargos de direção por nível</h2>
        <p class="sec">Cargos Comissionados Executivos (CCE) e Funções Comissionadas Executivas (FCE) de direção, categoria 1. Quanto maior o nível, mais alto o posto.</p>
        <div class="legenda" aria-hidden="true">
          <span><i style="background: var(--series-1)"></i>CCE</span>
          <span><i style="background: var(--series-2)"></i>FCE (exclusiva de servidor efetivo)</span>
        </div>
        <table class="barras">
          <thead><tr><th>Nível</th><th>Quantidade</th><th class="num">Total</th></tr></thead>
          <tbody>
            {#each linhasNivel as v (v.n)}
              <tr title={`Nível 1.${v.n}: ${v.CCE} CCE, ${v.FCE} FCE`}>
                <th scope="row" class="num">1.{String(v.n).padStart(2, "0")}</th>
                <td>
                  <div class="trilho">
                    {#if v.CCE}<span style="width: {(100 * v.CCE) / maxNivel}%; background: var(--series-1)"></span>{/if}
                    {#if v.FCE}<span style="width: {(100 * v.FCE) / maxNivel}%; background: var(--series-2)"></span>{/if}
                  </div>
                  <span class="sr-only">{v.CCE} CCE e {v.FCE} FCE</span>
                </td>
                <td class="num">{v.CCE + v.FCE}</td>
              </tr>
            {/each}
          </tbody>
        </table>
        <Fonte fonte={m.fontes.estrutura} rotuloData="Coletado em" />
      </section>

      <section class="cartao">
        <h2>Hierarquia típica</h2>
        <ol class="hier">
          {#each HIERARQUIA as h, i (h.cargo)}
            <li style="--i: {i}"><span>{h.cargo}</span><span class="chip">{h.nivel}</span></li>
          {/each}
        </ol>
        <p class="mudo pequeno">Lei 14.204/2021. O Quadro Demonstrativo de Cargos do decreto de estrutura diz quantos cargos de cada nível há em cada unidade.</p>
      </section>
    {/if}
  </div>
</div>

<style>
  .layout { display: grid; gap: 16px; margin-top: 16px; align-items: start; }
  @media (min-width: 900px) {
    .layout { grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr); }
    .detalhe { position: sticky; top: 12px; max-height: calc(100vh - 24px); overflow: auto; border-radius: 14px; }
  }
  .titulo-linha { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 8px; }
  .titulo-linha h2 { margin: 0; }
  .controles { display: flex; gap: 6px; }
  .dica { font-size: 0.85rem; margin: 8px 0 12px; }
  .raiz { width: 100%; text-align: left; border: 1.5px solid var(--linha); background: var(--cartao-2); border-radius: 10px; padding: 10px 12px; cursor: pointer; }
  .raiz.sel, .raiz:hover { border-color: var(--marca); }
  .bloco { margin-top: 18px; }
  .bloco h3 { margin: 0; font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--marca); }
  .resumo { font-size: 0.8rem; margin: 2px 0 6px; }
  ul[role="tree"] { list-style: none; margin: 0; padding: 0; }
  .legenda { display: flex; flex-wrap: wrap; gap: 14px; font-size: 0.82rem; color: var(--sec); margin: 6px 0 8px; }
  .legenda i { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 6px; vertical-align: -1px; }
  .barras th, .barras td { border: 0; padding: 4px 6px; }
  .barras td:nth-child(2) { width: 100%; }
  .trilho { display: flex; gap: 2px; height: 14px; align-items: stretch; }
  .trilho span { display: block; min-width: 2px; }
  .trilho span:last-child { border-radius: 0 4px 4px 0; }
  .hier { list-style: none; padding: 0; margin: 0; display: grid; gap: 6px; }
  .hier li { display: flex; justify-content: space-between; gap: 8px; align-items: center; padding: 6px 10px; padding-left: calc(10px + var(--i) * 14px); border-left: 3px solid var(--linha); }
  .pequeno { font-size: 0.8rem; margin: 10px 0 0; }
</style>
