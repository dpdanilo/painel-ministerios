<script>
  import { data as fmtData } from "../lib/formato.js";
  import Fonte from "./Fonte.svelte";

  let { m } = $props();
  let normas = $derived(m.normas);
  const norma = (id) => normas[id];
  const TIPOS = { criacao: "Criação", extincao: "Extinção", fusao: "Fusão", desmembramento: "Desmembramento", recriacao: "Recriação", renomeacao: "Renomeação" };
  let eventos = $derived([...m.eventos].sort((a, b) => a.data.localeCompare(b.data)));
  let camadas = $derived([
    { nivel: "Lei", define: "Cria o ministério e define sua área de competência", id: m.norma_organizacao },
    { nivel: "Decreto", define: "Estrutura Regimental: órgãos, competências de cada um e quadro de cargos", id: m.norma_estrutura },
    { nivel: "Portaria", define: "Regimento Interno: detalha coordenações e divisões", id: null },
  ]);
</script>

<div class="grade">
  <section class="cartao" aria-labelledby="t-comp">
    <h2 id="t-comp">Competências</h2>
    <p class="sec pequeno">O que a lei atribui ao ministério (art. 1º do Anexo I do decreto de estrutura).</p>
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
            {:else if !c.id}
              <span class="mudo">Ver os atos de cada unidade na aba Estrutura</span>
            {/if}
          </li>
        {/each}
      </ol>
    </section>

    <section class="cartao" aria-labelledby="t-hist">
      <h2 id="t-hist">Linha do tempo</h2>
      <ol class="tempo">
        {#each eventos as e (e.id)}
          <li>
            <span class="quando num">{fmtData(e.data)}</span>
            <strong>{TIPOS[e.tipo] || e.tipo}</strong>
            {#if e.descricao}<span class="sec">{e.descricao}</span>{/if}
            {#if e.norma && norma(e.norma)}<a href={norma(e.norma).url} target="_blank" rel="noopener">{norma(e.norma).tipo} {norma(e.norma).numero}</a>{/if}
          </li>
        {/each}
      </ol>
      <Fonte fonte={{ nome: "Curadoria (legislação citada em cada evento)", url: null }} curado />
    </section>
  </div>
</div>

<style>
  .grade { display: grid; gap: 16px; align-items: start; }
  @media (min-width: 900px) { .grade { grid-template-columns: 1.2fr 1fr; } }
  ol { padding-left: 22px; margin: 0; display: grid; gap: 8px; }
  .pequeno { font-size: 0.85rem; }
  .camadas, .tempo { list-style: none; padding: 0; }
  .camadas li, .tempo li { display: grid; gap: 2px; padding: 8px 0 8px 14px; border-left: 3px solid var(--linha); }
  .tempo li { border-left-color: var(--marca); }
  .quando { font-size: 0.8rem; color: var(--mudo); }
</style>
