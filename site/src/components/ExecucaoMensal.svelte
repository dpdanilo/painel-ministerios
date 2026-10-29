<script>
  import { tema } from "../lib/estado.svelte.js";
  import { brlCompacto, mesCurto, pct } from "../lib/formato.js";

  /** serie: [{mes, empenhado, liquidado, pago}] acumulados · dotacao: linha de referência (mesma escala) */
  let { serie, dotacao = null } = $props();

  const SERIES = [
    { chave: "empenhado", nome: "Empenhado", cor: "--series-1" },
    { chave: "liquidado", nome: "Liquidado", cor: "--series-2" },
    { chave: "pago", nome: "Pago", cor: "--series-3" },
  ];

  let el = $state();
  let grafico;
  let verTabela = $state(false);

  // ECharts só é baixado quando este gráfico aparece (fora da carga inicial).
  const echartsPronto = import("../lib/echarts.js");

  function cor(nome) {
    return getComputedStyle(document.documentElement).getPropertyValue(nome).trim();
  }

  function opcoes() {
    const ink = { sec: cor("--sec"), mudo: cor("--mudo"), grade: cor("--grade"), eixo: cor("--eixo"), sup: cor("--cartao"), texto: cor("--texto") };
    return {
      animation: false,
      grid: { left: 8, right: 16, top: 24, bottom: 8, containLabel: true },
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "line", lineStyle: { color: ink.eixo, width: 1 } },
        backgroundColor: ink.sup, borderColor: ink.grade, textStyle: { color: ink.texto, fontSize: 13 },
        formatter: (ps) => {
          const mes = serie[ps[0].dataIndex];
          const linhas = SERIES.map((s) =>
            `<div style="display:flex;gap:8px;align-items:center"><span style="width:10px;height:2px;background:${cor(s.cor)}"></span>${s.nome}<b style="margin-left:auto;padding-left:12px">${brlCompacto(mes[s.chave])}</b></div>`);
          const ref = dotacao ? `<div style="color:${ink.mudo};margin-top:4px">Pago = ${pct(mes.pago, dotacao)} da dotação</div>` : "";
          return `<div style="font-weight:600;margin-bottom:4px">até ${mesCurto(mes.mes)}</div>${linhas.join("")}${ref}`;
        },
      },
      xAxis: {
        type: "category", data: serie.map((s) => mesCurto(s.mes)), boundaryGap: false,
        axisLine: { lineStyle: { color: ink.eixo } }, axisTick: { show: false }, axisLabel: { color: ink.mudo },
      },
      yAxis: {
        type: "value", splitLine: { lineStyle: { color: ink.grade, width: 1 } },
        axisLabel: { color: ink.mudo, formatter: (v) => brlCompacto(v).replace("R$ ", "") },
        max: dotacao ? (v) => Math.max(v.max, dotacao) : undefined,
      },
      series: SERIES.map((s, i) => ({
        name: s.nome, type: "line", data: serie.map((p) => p[s.chave]),
        lineStyle: { width: 2, color: cor(s.cor), cap: "round", join: "round" },
        itemStyle: { color: cor(s.cor), borderColor: ink.sup, borderWidth: 2 },
        symbol: "circle", symbolSize: 8, showSymbol: false,
        emphasis: { focus: "none" },
        markLine: i === 0 && dotacao ? {
          symbol: "none", silent: true, lineStyle: { color: ink.eixo, type: "solid", width: 1 },
          label: { position: "insideStartTop", color: ink.mudo, formatter: `Dotação atual ${brlCompacto(dotacao)}` },
          data: [{ yAxis: dotacao }],
        } : undefined,
      })),
    };
  }

  $effect(() => {
    // dependências: serie, dotacao, tema
    serie; dotacao; tema.atual;
    let vivo = true;
    echartsPronto.then((echarts) => {
      if (!vivo || !el) return;
      grafico ??= echarts.init(el, null, { renderer: "svg" });
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
  {#each SERIES as s (s.chave)}<span><i style="background: var({s.cor})"></i>{s.nome} <b class="num">{brlCompacto(serie.at(-1)?.[s.chave])}</b></span>{/each}
</div>
<div class="grafico" bind:this={el} role="img" aria-label={`Execução acumulada até ${serie.length ? mesCurto(serie.at(-1).mes) : ""}: ` + SERIES.map((s) => `${s.nome} ${brlCompacto(serie.at(-1)?.[s.chave])}`).join(", ")}></div>
<button type="button" class="botao" onclick={() => (verTabela = !verTabela)} aria-expanded={verTabela}>{verTabela ? "Ocultar tabela" : "Ver como tabela"}</button>
{#if verTabela}
  <div class="tabela-rolagem">
    <table>
      <thead><tr><th>Até</th>{#each SERIES as s (s.chave)}<th class="num">{s.nome}</th>{/each}</tr></thead>
      <tbody>
        {#each serie as p (p.mes)}
          <tr><td>{mesCurto(p.mes)}</td>{#each SERIES as s (s.chave)}<td class="num">{brlCompacto(p[s.chave])}</td>{/each}</tr>
        {/each}
      </tbody>
    </table>
  </div>
{/if}

<style>
  .legenda { display: flex; flex-wrap: wrap; gap: 14px; font-size: 0.82rem; color: var(--sec); }
  .legenda i { display: inline-block; width: 14px; height: 2px; margin-right: 6px; vertical-align: 3px; }
  .grafico { width: 100%; height: 300px; margin: 6px 0 10px; }
  table { margin-top: 10px; }
</style>
