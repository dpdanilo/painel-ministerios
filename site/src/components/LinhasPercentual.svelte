<script>
  import { tema } from "../lib/estado.svelte.js";
  import { mesCurto } from "../lib/formato.js";

  /** series: [{ nome, cor (var CSS), pontos: [[mes, fração 0..1]] }] */
  let { series, rotulo = "% pago" } = $props();

  let el = $state();
  let grafico;
  let verTabela = $state(false);
  const echartsPronto = import("../lib/echarts.js");
  const cor = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const pctTxt = (v) => (v == null ? "–" : `${(v * 100).toFixed(1).replace(".", ",")}%`);

  let meses = $derived([...new Set(series.flatMap((s) => s.pontos.map((p) => p[0])))].sort((a, b) => a - b));

  function opcoes() {
    const ink = { mudo: cor("--mudo"), grade: cor("--grade"), eixo: cor("--eixo"), sup: cor("--cartao"), texto: cor("--texto") };
    return {
      animation: false,
      grid: { left: 8, right: 16, top: 16, bottom: 8, containLabel: true },
      tooltip: {
        trigger: "axis", axisPointer: { type: "line", lineStyle: { color: ink.eixo, width: 1 } },
        backgroundColor: ink.sup, borderColor: ink.grade, textStyle: { color: ink.texto, fontSize: 13 },
        formatter: (ps) => {
          const linhas = [...ps].sort((a, b) => (b.value ?? -1) - (a.value ?? -1)).map((p) =>
            `<div style="display:flex;gap:8px;align-items:center"><span style="width:10px;height:2px;background:${cor(series[p.seriesIndex].cor)}"></span>${p.seriesName}<b style="margin-left:auto;padding-left:12px">${pctTxt(p.value)}</b></div>`);
          return `<div style="font-weight:600;margin-bottom:4px">${rotulo} até ${mesCurto(meses[ps[0].dataIndex])}</div>${linhas.join("")}`;
        },
      },
      xAxis: { type: "category", data: meses.map(mesCurto), boundaryGap: false, axisLine: { lineStyle: { color: ink.eixo } }, axisTick: { show: false }, axisLabel: { color: ink.mudo } },
      yAxis: { type: "value", min: 0, max: (v) => Math.max(1, Math.ceil(v.max * 10) / 10), splitLine: { lineStyle: { color: ink.grade } }, axisLabel: { color: ink.mudo, formatter: (v) => `${Math.round(v * 100)}%` } },
      series: series.map((s) => {
        const porMes = new Map(s.pontos);
        return {
          name: s.nome, type: "line", data: meses.map((m) => porMes.get(m) ?? null), connectNulls: false,
          lineStyle: { width: 2, color: cor(s.cor) }, itemStyle: { color: cor(s.cor), borderColor: ink.sup, borderWidth: 2 },
          symbol: "circle", symbolSize: 8, showSymbol: false, emphasis: { focus: "series" },
        };
      }),
    };
  }

  $effect(() => {
    series; tema.atual;
    let vivo = true;
    echartsPronto.then(({ init }) => {
      if (!vivo || !el) return;
      grafico ??= init(el, null, { renderer: "svg" });
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
  {#each series as s (s.nome)}<span><i style="background: var({s.cor})"></i>{s.nome} <b class="num">{pctTxt(s.pontos.at(-1)?.[1])}</b></span>{/each}
</div>
<div class="grafico" bind:this={el} role="img" aria-label={`${rotulo} acumulado no ano: ` + series.map((s) => `${s.nome} ${pctTxt(s.pontos.at(-1)?.[1])}`).join(", ")}></div>
<button type="button" class="botao" onclick={() => (verTabela = !verTabela)} aria-expanded={verTabela}>{verTabela ? "Ocultar tabela" : "Ver como tabela"}</button>
{#if verTabela}
  <div class="tabela-rolagem">
    <table>
      <thead><tr><th>Até</th>{#each series as s (s.nome)}<th class="num">{s.nome}</th>{/each}</tr></thead>
      <tbody>
        {#each meses as mes (mes)}
          <tr><td>{mesCurto(mes)}</td>{#each series as s (s.nome)}<td class="num">{pctTxt(new Map(s.pontos).get(mes))}</td>{/each}</tr>
        {/each}
      </tbody>
    </table>
  </div>
{/if}

<style>
  .legenda { display: flex; flex-wrap: wrap; gap: 6px 16px; font-size: 0.82rem; color: var(--sec); }
  .legenda i { display: inline-block; width: 14px; height: 2px; margin-right: 6px; vertical-align: 3px; }
  .grafico { width: 100%; height: 300px; margin: 6px 0 10px; }
  table { margin-top: 10px; }
</style>
