<script>
  import { data as fmtData, brlCompacto, mesAno } from "../lib/formato.js";
  import { carregarIndice } from "../lib/dados.js";
  import { TIPOS_EVENTO, serieAnual } from "../lib/historia.js";
  import Fonte from "./Fonte.svelte";
  import GraficoSerie from "./GraficoSerie.svelte";
  import BotaoCsv from "./BotaoCsv.svelte";

  let { m } = $props();
  let normas = $derived(m.normas);
  const norma = (id) => normas[id];
  let eventos = $derived([...m.eventos].sort((a, b) => b.data.localeCompare(a.data)));
  let historia = $derived([...(m.historia || [])].reverse());
  let camadas = $derived([
    { nivel: "Lei", define: "Cria o ministério e define sua área de competência", id: m.norma_organizacao },
    { nivel: "Decreto", define: "Estrutura Regimental: órgãos, competências de cada um e quadro de cargos", id: m.norma_estrutura },
    { nivel: "Portaria", define: "Regimento Interno: detalha coordenações e divisões", id: null },
  ]);

  // Orçamento desde 2014 (série do órgão orçamentário), em valores corrigidos ou nominais.
  let ipca = $state(null);
  carregarIndice().then((i) => (ipca = i.ipca));
  let real = $state(true);
  let semOE = $state(true);
  let anual = $derived(m.orcamento_anual || []);
  let temOE = $derived(anual.some((l) => Math.abs(l[2] - l[5]) > 1));
  let series = $derived([
    { nome: "Dotação atual", cor: "--etapa-1", pontos: serieAnual(anual, semOE ? "dotacao_sem_oe" : "dotacao_atual", { real, ipca }) },
    { nome: "Pago", cor: "--etapa-3", pontos: serieAnual(anual, semOE ? "pago_sem_oe" : "pago", { real, ipca }) },
  ]);
  const anoAtual = () => anual.at(-1)?.[0];
  const colunasCsv = [
    { chave: "ano", titulo: "Ano" }, { chave: "ini", titulo: "Dotação inicial (R$ nominais)" }, { chave: "atual", titulo: "Dotação atual (R$ nominais)" },
    { chave: "emp", titulo: "Empenhado (R$ nominais)" }, { chave: "pago", titulo: "Pago (R$ nominais)" },
    { chave: "atual_sem", titulo: "Dotação atual sem op. especiais" }, { chave: "pago_sem", titulo: "Pago sem op. especiais" },
    { chave: "fator", titulo: "Fator IPCA" },
  ];
  const linhasCsv = () => anual.map((l) => ({ ano: l[0], ini: l[1], atual: l[2], emp: l[3], pago: l[4], atual_sem: l[5], pago_sem: l[6], fator: ipca?.fatores?.[l[0]] }));
</script>

<div class="grade">
  <section class="cartao" aria-labelledby="t-comp">
    <h2 id="t-comp">Competências</h2>
    <p class="sec pequeno">O que a lei atribui ao órgão (art. 1º do Anexo I do decreto de estrutura).</p>
    <ol>
      {#each m.competencias as c, i (i)}<li>{c}</li>{/each}
    </ol>
    <Fonte fonte={m.fontes.estrutura} rotuloData="Coletado em" />
  </section>

  <div>
    <section class="cartao" aria-labelledby="t-normas">
      <h2 id="t-normas">Camadas normativas</h2>
      <ol class="camadas">
        {#each camadas as c (c.nivel)}
          <li>
            <strong>{c.nivel}</strong>
            <span class="sec">{c.define}</span>
            {#if c.id && norma(c.id)}
              <a href={norma(c.id).url} target="_blank" rel="noopener">{norma(c.id).tipo} {norma(c.id).numero}{norma(c.id).vigencia ? `, vigente desde ${fmtData(norma(c.id).vigencia)}` : ""}</a>
            {:else if c.nivel === "Portaria"}
              <span class="mudo">Ver os atos de cada unidade na aba Estrutura</span>
            {:else}
              <span class="mudo">Ainda não curado</span>
            {/if}
          </li>
        {/each}
      </ol>
    </section>

    {#if historia.length}
      <section class="cartao" aria-labelledby="t-nomes">
        <h2 id="t-nomes">Nomes desde 2003</h2>
        <ol class="tempo">
          {#each historia as h, i (i)}
            <li class:atual={!h.ate}>
              <span class="quando num">{h.de ? fmtData(h.de) : "antes de 2003"} – {h.ate ? fmtData(h.ate) : "hoje"}</span>
              <strong>{h.nome}</strong>
              {#if h.categoria === "presidencia"}<span class="chip">órgão da Presidência</span>{/if}
              {#if h.norma && norma(h.norma)}<a href={norma(h.norma).url} target="_blank" rel="noopener">{norma(h.norma).tipo} {norma(h.norma).numero}</a>{/if}
            </li>
          {/each}
        </ol>
        <p class="mudo pequeno">Intervalos sem nome = período em que as funções do órgão estavam dentro de outro ministério (veja as mudanças abaixo).</p>
      </section>
    {/if}
  </div>
</div>

{#if eventos.length}
  <section class="cartao" aria-labelledby="t-hist">
    <h2 id="t-hist">Criações, fusões e recriações</h2>
    <ol class="eventos">
      {#each eventos as e (e.id)}
        <li>
          <span class="quando num">{fmtData(e.data)}</span>
          <span class="chip">{TIPOS_EVENTO[e.tipo] || e.tipo}</span>
          <span>{e.descricao}</span>
          {#if Object.keys(e.nomes?.origem || {}).length || Object.keys(e.nomes?.destino || {}).length}
            <span class="fluxo mudo">
              {Object.values(e.nomes.origem).join(" + ") || "—"} → {Object.values(e.nomes.destino).join(" + ") || "extinto"}
            </span>
          {/if}
          {#if e.norma && norma(e.norma)}<a href={norma(e.norma).url} target="_blank" rel="noopener">{norma(e.norma).tipo} {norma(e.norma).numero}</a>{/if}
        </li>
      {/each}
    </ol>
    <Fonte fonte={{ nome: "Curadoria a partir do texto das normas no Planalto", url: null }} curado />
  </section>
{/if}

{#if anual.length}
  <section class="cartao" aria-labelledby="t-orc-hist">
    <div class="cab-secao">
      <h2 id="t-orc-hist">Orçamento desde 2014</h2>
      <BotaoCsv arquivo={`${m.id}-orcamento-historico.csv`} colunas={colunasCsv} linhas={linhasCsv} />
    </div>
    <div class="filtros">
      <div class="segmentado" role="group" aria-label="Valores">
        <button type="button" aria-pressed={real} onclick={() => (real = true)}>Corrigido pela inflação</button>
        <button type="button" aria-pressed={!real} onclick={() => (real = false)}>Valores da época</button>
      </div>
      {#if temOE}
        <label class="caixa"><input type="checkbox" bind:checked={semOE} /> Sem operações especiais</label>
      {/if}
    </div>
    <GraficoSerie {series} tipo="bar" fmt={(v) => (v == null ? "–" : brlCompacto(v))} tabelaTitulo="Ano"
      rotulo={`Dotação e pago por ano, ${real ? "corrigidos pelo IPCA" : "em valores da época"}`} />
    <p class="mudo pequeno">
      Série do órgão orçamentário {m.orgao_orcamentario}, que nem sempre acompanha as reformas: entre 2019 e 2022, por exemplo, vários ministérios
      extintos continuaram com orçamento próprio dentro do ministério que os absorveu. O Portal da Transparência mostra o código com o nome atual em todos os anos.
      {#if real && ipca}Valores em reais de {mesAno(ipca.referencia)}, pela média do IPCA de cada ano.{/if}
      {#if anoAtual()}{anoAtual()} ainda em execução.{/if}
    </p>
  </section>
{/if}

<style>
  .grade { display: grid; gap: 16px; align-items: start; }
  @media (min-width: 900px) { .grade { grid-template-columns: 1.2fr 1fr; } }
  .grade .cartao + .cartao { margin-top: 16px; }
  section.cartao:not(.grade *) { margin-top: 16px; }
  ol { padding-left: 22px; margin: 0; display: grid; gap: 8px; }
  .pequeno { font-size: 0.82rem; }
  .camadas, .tempo, .eventos { list-style: none; padding: 0; }
  .camadas li, .tempo li { display: grid; gap: 2px; padding: 8px 0 8px 14px; border-left: 3px solid var(--linha); }
  .tempo li.atual { border-left-color: var(--marca); }
  .eventos li { display: flex; flex-wrap: wrap; gap: 4px 10px; align-items: baseline; padding: 8px 0; border-bottom: 1px solid var(--linha); }
  .fluxo { flex-basis: 100%; font-size: 0.82rem; }
  .quando { font-size: 0.8rem; color: var(--mudo); }
  .caixa { display: flex !important; align-items: center; gap: 8px; min-height: 38px; flex: 0 1 auto !important; font-size: 0.88rem !important; }
  .caixa input { width: 18px; height: 18px; accent-color: var(--marca); }
</style>
