<script>
  import { tema } from "../lib/estado.svelte.js";

  /**
   * series: [{ nome, cor (var CSS), pontos: [[x, y]] }]
   * tipo: "line" | "bar" · tempo: eixo X de datas (degraus) · fmt: formata valores · fmtX: formata o eixo X
   * marcas: [{ x, rotulo }] linhas verticais de referência (ex.: posses presidenciais)
   */
  let { series, tipo = "line", tempo = false, degrau = false, fmt = (v) => v, fmtX = (x) => x, rotulo = "", altura = 300,
        marcas = [], tabelaTitulo = "Período" } = $props();

  let el = $state();
  let grafico;
  let verTabela = $state(false);
  const echartsPronto = import("../lib/echarts.js");
  const cor = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();

  let xs = $derived([...new Set(series.flatMap((s) => s.pontos.map((p) => p[0])))].sort());
  let uma = $derived(series.length === 1);

  function opcoes() {
    const ink = { mudo: cor("--mudo"), grade: cor("--grade"), eixo: cor("--eixo"), sup: cor("--cartao"), texto: cor("--texto"), sec: cor("--sec") };
    const dados = (s) => (tempo ? s.pontos : (() => { const m = new Map(s.pontos); return xs.map((x) => m.get(x) ?? null); })());
    return {
      animation: false,
      grid: { left: 8, right: 16, top: marcas.length ? 28 : 16, bottom: 8, containLabel: true },
      tooltip: {
        trigger: "axis", axisPointer: { type: tipo === "bar" ? "shadow" : "line", lineStyle: { color: ink.eixo, width: 1 }, shadowStyle: { color: "rgba(127,127,127,0.08)" } },
        backgroundColor: ink.sup, borderColor: ink.grade, textStyle: { color: ink.texto, fontSize: 13 },
        formatter: (ps) => {
          const x = tempo ? ps[0].value[0] : xs[ps[0].dataIndex];
          const linhas = ps.filter((p) => (tempo ? p.value[1] : p.value) != null).map((p) =>
            `<div style="display:flex;gap:8px;align-items:center"><span style="width:10px;height:${tipo === "bar" ? 10 : 2}px;border-radius:2px;background:${cor(series[p.seriesIndex].cor)}"></span>${p.seriesName}<b style="margin-left:auto;padding-left:12px">${fmt(tempo ? p.value[1] : p.value)}</b></div>`);
          const extra = series[0].dica ? series[0].dica(x) : "";
          return `<div style="font-weight:600;margin-bottom:4px">${fmtX(x)}</div>${linhas.join("")}${extra}`;
        },
      },
      xAxis: tempo
        ? { type: "time", axisLine: { lineStyle: { color: ink.eixo } }, axisTick: { show: false }, axisLabel: { color: ink.mudo }, splitLine: { show: false } }
        : { type: "category", data: xs, boundaryGap: tipo === "bar", axisLine: { lineStyle: { color: ink.eixo } }, axisTick: { show: false }, axisLabel: { color: ink.mudo, formatter: fmtX } },
      yAxis: { type: "value", splitLine: { lineStyle: { color: ink.grade } }, axisLabel: { color: ink.mudo, formatter: (v) => fmt(v) } },
      series: series.map((s, i) => ({
        name: s.nome, type: tipo, data: dados(s), step: degrau ? "end" : false,
        barMaxWidth: 24, barGap: "8%",
        itemStyle: tipo === "bar" ? { color: cor(s.cor), borderRadius: [4, 4, 0, 0] } : { color: cor(s.cor), borderColor: ink.sup, borderWidth: 2 },
        lineStyle: { width: 2, color: cor(s.cor) }, symbol: "circle", symbolSize: 8, showSymbol: false, connectNulls: false,
        emphasis: { focus: uma ? "none" : "series" },
        markLine: i === 0 && marcas.length ? {
          symbol: "none", silent: true, lineStyle: { color: ink.eixo, type: "solid", width: 1 },
          label: { position: "end", color: ink.mudo, fontSize: 11, formatter: (p) => p.data.rotulo },
          data: marcas.map((m) => ({ xAxis: m.x, rotulo: m.rotulo })),
        } : undefined,
      })),
    };
  }

  $effect(() => {
    series; tipo; tema.atual;
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

{#if !uma}
  <div class="legenda" aria-hidden="true">
    {#each series as s (s.nome)}<span><i class:barra={tipo === "bar"} style="background: var({s.cor})"></i>{s.nome}</span>{/each}
  </div>
{/if}
<div class="grafico" style="height: {altura}px" bind:this={el} role="img" aria-label={rotulo}></div>
<button type="button" class="botao" onclick={() => (verTabela = !verTabela)} aria-expanded={verTabela}>{verTabela ? "Ocultar tabela" : "Ver como tabela"}</button>
{#if verTabela}
  <div class="tabela-rolagem">
    <table>
      <thead><tr><th>{tabelaTitulo}</th>{#each series as s (s.nome)}<th class="num">{s.nome}</th>{/each}</tr></thead>
      <tbody>
        {#each xs as x (x)}
          <tr><td>{fmtX(x)}</td>{#each series as s (s.nome)}<td class="num">{fmt(new Map(s.pontos).get(x) ?? null) ?? "–"}</td>{/each}</tr>
        {/each}
      </tbody>
    </table>
  </div>
{/if}

<style>
  .legenda { display: flex; flex-wrap: wrap; gap: 6px 16px; font-size: 0.82rem; color: var(--sec); }
  .legenda i { display: inline-block; width: 14px; height: 2px; margin-right: 6px; vertical-align: 3px; }
  .legenda i.barra { width: 10px; height: 10px; border-radius: 3px; vertical-align: -1px; }
  .grafico { width: 100%; margin: 6px 0 10px; }
  table { margin-top: 10px; }
</style>
