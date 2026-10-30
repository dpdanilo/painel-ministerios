<script>
  import { tema, href } from "../lib/estado.svelte.js";
  import { CATEGORIAS } from "../lib/governo.js";
  import { brlCompacto, num, pct } from "../lib/formato.js";

  /** ministerios: resumos do index · metrica: item de METRICAS */
  let { ministerios, metrica } = $props();

  let el = $state();
  let grafico;
  const echartsPronto = import("../lib/echarts.js");
  const cor = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const fmt = (v) => (metrica.tipo === "brl" ? brlCompacto(v) : num(v));

  let itens = $derived(ministerios.map((m) => ({ m, v: metrica.valor(m) })).filter((x) => x.v > 0).sort((a, b) => b.v - a.v));
  let total = $derived(itens.reduce((s, x) => s + x.v, 0));
  let semValor = $derived(ministerios.filter((m) => !(metrica.valor(m) > 0)));

  function opcoes() {
    const sup = cor("--cartao");
    return {
      animation: false,
      tooltip: {
        backgroundColor: sup, borderColor: cor("--grade"), textStyle: { color: cor("--texto"), fontSize: 13 },
        formatter: (p) => {
          const m = p.data.m;
          return `<b>${m.nome}</b><br>${metrica.nome}: <b>${fmt(p.value)}</b> (${pct(p.value, total)} do total)<br><span style="color:${cor("--mudo")}">${CATEGORIAS[m.categoria]?.nome ?? ""} · clique para abrir</span>`;
        },
      },
      series: [{
        type: "treemap", roam: false, nodeClick: false, breadcrumb: { show: false },
        left: 0, right: 0, top: 0, bottom: 0, squareRatio: 0.9,
        itemStyle: { gapWidth: 2, borderColor: sup, borderWidth: 0 },
        label: {
          show: true, color: "#ffffff", fontSize: 12, fontWeight: 600, overflow: "truncate",
          formatter: (p) => `${p.data.m.sigla}\n${fmt(p.value)}`,
        },
        upperLabel: { show: false },
        data: itens.map(({ m, v }) => ({ name: m.sigla, value: v, m, itemStyle: { color: cor(CATEGORIAS[m.categoria]?.cor ?? "--series-1"), borderRadius: 4 } })),
      }],
    };
  }

  $effect(() => {
    itens; tema.atual;
    let vivo = true;
    echartsPronto.then(({ init }) => {
      if (!vivo || !el) return;
      if (!grafico) {
        grafico = init(el, null, { renderer: "svg" });
        grafico.on("click", (p) => p.data?.m && (location.hash = href(["m", p.data.m.id, "estrutura"])));
      }
      grafico.setOption(opcoes(), true);
    });
    return () => (vivo = false);
  });

  $effect(() => {
    if (!el) return;
    const ro = new ResizeObserver(() => grafico?.resize());
    ro.observe(el);
    return () => { ro.disconnect(); grafico?.dispose(); grafico = null; };
  });
</script>

<div class="legenda" aria-hidden="true">
  {#each Object.entries(CATEGORIAS) as [id, c] (id)}<span><i style="background: var({c.cor})"></i>{c.nome}</span>{/each}
</div>
<div class="mapa" bind:this={el} role="img"
  aria-label={`${metrica.nome} por órgão. Maiores: ` + itens.slice(0, 5).map((x) => `${x.m.sigla} ${fmt(x.v)}`).join(", ")}></div>
{#if semValor.length}
  <p class="mudo pequeno">Fora do mapa (sem valor próprio): {semValor.map((m) => m.sigla).join(", ")}.
    {#if metrica.tipo === "brl"}Os órgãos da Presidência têm o orçamento consolidado na UO “Presidência da República”.{/if}</p>
{/if}

<style>
  .legenda { display: flex; flex-wrap: wrap; gap: 14px; font-size: 0.82rem; color: var(--sec); margin-bottom: 8px; }
  .legenda i { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 6px; vertical-align: -1px; }
  .mapa { width: 100%; height: clamp(320px, 55vw, 520px); cursor: pointer; }
  .pequeno { font-size: 0.8rem; margin: 8px 0 0; }
</style>
