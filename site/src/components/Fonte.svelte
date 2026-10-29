<script>
  import { data as fmtData } from "../lib/formato.js";
  /** fonte: { nome, url, data, referencia } */
  let { fonte, rotuloData = "Atualizado em", curado = false } = $props();
</script>

{#if fonte}
  <p class="fonte">
    {#if curado}<span class="chip">curado</span>{/if}
    Fonte:
    {#if fonte.url}<a href={fonte.url} target="_blank" rel="noopener">{fonte.nome}</a>{:else}{fonte.nome}{/if}
    {#if fonte.data} · {rotuloData} {fmtData(fonte.data)}{/if}
    {#if fonte.referencia} · versão de {fmtData(fonte.referencia)}{/if}
  </p>
{/if}

<style>
  .fonte { font-size: 0.78rem; color: var(--mudo); margin: 14px 0 0; display: flex; flex-wrap: wrap; gap: 4px; align-items: center; }
  .fonte a { color: var(--sec); }
</style>
