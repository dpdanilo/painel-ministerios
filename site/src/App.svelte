<script>
  import { rota, alternarTema, tema } from "./lib/estado.svelte.js";
  import Inicio from "./views/Inicio.svelte";
  import Ministerio from "./views/Ministerio.svelte";

  let pagina = $derived(rota.partes[0] === "m" && rota.partes[1] ? "ministerio" : "inicio");
</script>

<a class="pular" href="#conteudo" onclick={(e) => { e.preventDefault(); document.getElementById("conteudo")?.focus(); }}>Pular para o conteúdo</a>

<header class="topo">
  <div class="barra">
    <a class="marca" href="#/">
      <svg viewBox="0 0 32 32" aria-hidden="true"><path d="M8 24V13l8-5 8 5v11h-5v-6h-6v6z" fill="currentColor"/></svg>
      <span>Estrutura dos Ministérios</span>
    </a>
    <nav class="acoes" aria-label="Geral">
      <a href="https://dpdanilo.github.io/vira-2026/">Vira 2026</a>
      <button type="button" class="tema" onclick={alternarTema} aria-label={tema.atual === "dark" ? "Usar tema claro" : "Usar tema escuro"}>
        {#if tema.atual === "dark"}
          <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4.5" fill="currentColor"/><g stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></g></svg>
        {:else}
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z" fill="currentColor"/></svg>
        {/if}
      </button>
    </nav>
  </div>
</header>

<main id="conteudo" tabindex="-1">
  {#if pagina === "ministerio"}
    {#key rota.partes[1]}
      <Ministerio id={rota.partes[1]} />
    {/key}
  {:else}
    <Inicio />
  {/if}
</main>

<footer class="rodape">
  Dados oficiais: SIORG (MGI) e Portal da Transparência (CGU), com curadoria identificada.
  <a href="https://github.com/dpdanilo/painel-ministerios">Código e dados abertos</a>
</footer>

<style>
  .pular { position: absolute; left: -9999px; top: 8px; z-index: 10; background: var(--cartao); padding: 8px 12px; border-radius: 8px; }
  .pular:focus { left: 8px; }
  .topo { background: var(--marca); color: var(--sobre-marca); }
  .barra { max-width: 1180px; margin: 0 auto; padding: 10px 16px; display: flex; align-items: center; justify-content: space-between; gap: 12px; min-height: 56px; }
  .marca { display: flex; align-items: center; gap: 10px; color: inherit; text-decoration: none; font-family: "Montserrat", sans-serif; font-weight: 900; text-transform: uppercase; font-size: 1rem; letter-spacing: -0.01em; }
  .marca svg { width: 26px; height: 26px; flex: none; }
  .acoes { display: flex; align-items: center; gap: 6px; }
  .acoes a { white-space: nowrap; color: inherit; font-weight: 600; font-size: 0.88rem; text-decoration: none; padding: 8px 10px; border-radius: 999px; }
  .acoes a:hover { background: rgba(255, 255, 255, 0.15); color: inherit; }
  .tema { width: 40px; height: 40px; border-radius: 50%; border: 0; background: rgba(255, 255, 255, 0.15); color: inherit; cursor: pointer; display: grid; place-items: center; }
  .tema svg { width: 20px; height: 20px; }
  .tema:hover { background: rgba(255, 255, 255, 0.28); }
  .topo :focus-visible { outline-color: #fff; }
  main:focus { outline: none; }
  .rodape { text-align: center; color: var(--mudo); font-size: 0.8rem; padding: 0 16px 32px; }
  @media (max-width: 420px) { .marca span { font-size: 0.86rem; } }
</style>
