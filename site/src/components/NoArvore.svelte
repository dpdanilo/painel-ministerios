<script>
  import NoArvore from "./NoArvore.svelte";
  import { cargoDirigente, contarDescendentes } from "../lib/estrutura.js";

  let { u, idx, m, abertos, selecionada, selecionar, alternar, nivel = 1 } = $props();

  let filhos = $derived(idx.filhos.get(u.c) || []);
  let aberto = $derived(abertos.has(u.c));
  let dirigente = $derived(cargoDirigente(m.cargos[u.c]));
  let titular = $derived((idx.ocupantesPorUnidade.get(u.c) || []).find((o) => o.papel !== "adjunto"));
</script>

<li role="treeitem" aria-level={nivel} aria-expanded={filhos.length ? aberto : undefined} aria-selected={selecionada === u.c}>
  <div class="linha" class:sel={selecionada === u.c}>
    {#if filhos.length}
      <button type="button" class="abre" onclick={() => alternar(u.c)} aria-label={`${aberto ? "Fechar" : "Abrir"} ${u.s}: ${contarDescendentes(idx, u.c)} unidades abaixo`}>
        <span class:girado={aberto} aria-hidden="true">▸</span>
      </button>
    {:else}
      <span class="abre vazio" aria-hidden="true"></span>
    {/if}
    <button type="button" class="nome" onclick={() => selecionar(u.c)}>
      <span class="titulo"><strong>{u.s}</strong> {u.n}</span>
      <span class="meta">
        {#if dirigente}<span class="chip">{dirigente.rotulo}</span>{/if}
        {#if u.a === "meio"}<span class="chip">suporte</span>{/if}
        {#if titular}<span class="pessoa">{titular.nome}</span>{/if}
      </span>
    </button>
  </div>
  {#if aberto && filhos.length}
    <ul role="group">
      {#each filhos as f (f.c)}
        <NoArvore u={f} {idx} {m} {abertos} {selecionada} {selecionar} {alternar} nivel={nivel + 1} />
      {/each}
    </ul>
  {/if}
</li>

<style>
  li { margin: 0; }
  ul { list-style: none; margin: 0 0 0 14px; padding: 0 0 0 8px; border-left: 1px solid var(--linha); }
  .linha { display: flex; align-items: flex-start; gap: 2px; border-radius: 8px; }
  .linha.sel { background: var(--cartao-2); box-shadow: inset 3px 0 0 var(--marca); }
  .abre { flex: none; width: 32px; height: 36px; border: 0; background: none; cursor: pointer; color: var(--sec); font-size: 0.9rem; display: grid; place-items: center; border-radius: 6px; }
  .abre:hover { background: var(--cartao-2); color: var(--texto); }
  .abre span { display: inline-block; transition: transform 0.15s; }
  .abre .girado { transform: rotate(90deg); }
  .nome { flex: 1; min-width: 0; text-align: left; background: none; border: 0; padding: 7px 6px; cursor: pointer; border-radius: 6px; display: grid; gap: 3px; }
  .nome:hover .titulo { text-decoration: underline; text-decoration-color: var(--marca); }
  .titulo { font-size: 0.92rem; overflow-wrap: anywhere; }
  .meta { display: flex; flex-wrap: wrap; gap: 4px 6px; align-items: center; }
  .pessoa { font-size: 0.8rem; color: var(--sec); }
</style>
