<script>
  import { carregarMinisterio } from "../lib/dados.js";
  import { rota, href } from "../lib/estado.svelte.js";
  import { indexar, buscar } from "../lib/estrutura.js";
  import Estrutura from "../components/Estrutura.svelte";
  import Pessoas from "../components/Pessoas.svelte";
  import Orcamento from "../components/Orcamento.svelte";
  import Politicas from "../components/Politicas.svelte";
  import Sobre from "../components/Sobre.svelte";

  let { id } = $props();

  const ABAS = [
    { id: "estrutura", nome: "Estrutura" },
    { id: "pessoas", nome: "Quem é quem" },
    { id: "orcamento", nome: "Orçamento" },
    { id: "politicas", nome: "Políticas" },
    { id: "sobre", nome: "Competências e história" },
  ];

  let m = $state(null);
  let erro = $state(null);
  $effect(() => {
    carregarMinisterio(id).then((d) => (m = d), (e) => (erro = e));
  });

  let idx = $derived(m && indexar(m));
  let aba = $derived(ABAS.some((a) => a.id === rota.partes[2]) ? rota.partes[2] : "estrutura");
  let ministro = $derived(m?.ocupantes.find((o) => o.unidade === m.cod_siorg && o.papel === "titular" && !o.ate));

  let termo = $state("");
  let resultados = $derived(m ? buscar(m, termo) : []);

  $effect(() => {
    if (m) document.title = `${m.sigla} · Estrutura dos Ministérios`;
  });
</script>

{#if erro}
  <div class="conteudo"><p role="alert">{erro.message}</p><a href="#/">Voltar ao início</a></div>
{:else if !m}
  <div class="conteudo"><p class="mudo" role="status">Carregando…</p></div>
{:else}
  <div class="faixa">
    <div class="conteudo cab">
      <nav class="migalhas" aria-label="Você está em"><a href="#/">Início</a> <span aria-hidden="true">›</span> {m.sigla}</nav>
      <h1>{m.nome}</h1>
      {#if ministro}
        <p class="sec">Ministro: <strong>{ministro.nome}</strong>{ministro.partido ? ` · ${ministro.partido}` : ""}</p>
      {/if}

      <div class="busca" role="search">
        <label class="sr-only" for="busca">Buscar unidade, pessoa, programa, ação ou política</label>
        <input id="busca" type="search" placeholder="Buscar unidade, pessoa, programa, ação ou política…" bind:value={termo} autocomplete="off" />
        {#if termo.trim().length >= 2}
          <ul class="resultados" aria-live="polite">
            {#each resultados as r, i (i)}
              <li><a href={href(["m", id, r.rota[0]], r.rota[1])} onclick={() => (termo = "")}><span class="chip">{r.tipo}</span> {r.titulo}</a></li>
            {:else}
              <li class="mudo vazio">Nada encontrado para “{termo}”.</li>
            {/each}
          </ul>
        {/if}
      </div>

      <nav class="abas" aria-label="Seções do ministério">
        {#each ABAS as a (a.id)}
          <a href={href(["m", id, a.id])} aria-current={aba === a.id ? "page" : undefined}>{a.nome}</a>
        {/each}
      </nav>
    </div>
  </div>

  <div class="conteudo">
    {#if aba === "estrutura"}
      <Estrutura {m} {idx} />
    {:else if aba === "pessoas"}
      <Pessoas {m} {idx} />
    {:else if aba === "orcamento"}
      <Orcamento {m} />
    {:else if aba === "politicas"}
      <Politicas {m} {idx} />
    {:else}
      <Sobre {m} />
    {/if}
  </div>
{/if}

<style>
  .faixa { background: var(--cartao); border-bottom: 1px solid var(--linha); }
  .cab { padding-bottom: 0; }
  .migalhas { font-size: 0.85rem; color: var(--mudo); }
  h1 { font-size: clamp(1.4rem, 3.6vw, 2rem); margin: 6px 0 4px; }
  .cab > p { margin: 0 0 14px; }
  .busca { position: relative; max-width: 560px; margin-bottom: 14px; }
  .busca input { width: 100%; }
  .resultados { position: absolute; z-index: 5; left: 0; right: 0; top: calc(100% + 4px); list-style: none; margin: 0; padding: 6px; background: var(--cartao); border: 1px solid var(--linha); border-radius: 12px; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15); max-height: 60vh; overflow: auto; }
  .resultados a { display: flex; gap: 8px; align-items: baseline; padding: 8px; border-radius: 8px; text-decoration: none; color: var(--texto); font-size: 0.9rem; }
  .resultados a:hover, .resultados a:focus-visible { background: var(--cartao-2); }
  .vazio { padding: 8px; font-size: 0.9rem; }
  .abas { display: flex; gap: 4px; overflow-x: auto; scrollbar-width: none; margin: 0 -16px; padding: 0 16px; }
  .abas a { flex: none; padding: 10px 14px; text-decoration: none; color: var(--sec); font-weight: 600; font-size: 0.92rem; border-bottom: 3px solid transparent; }
  .abas a:hover { color: var(--texto); }
  .abas a[aria-current="page"] { color: var(--texto); border-bottom-color: var(--marca); }
</style>
