<script>
  import { BLOCOS, caminho, cargoDirigente, contarDescendentes } from "../lib/estrutura.js";
  import { rotuloCargo, data as fmtData, num } from "../lib/formato.js";
  import { href, trocarParams } from "../lib/estado.svelte.js";
  import Fonte from "./Fonte.svelte";

  let { cod, m, idx, selecionar } = $props();

  let u = $derived(idx.porCodigo.get(cod));
  let trilha = $derived(caminho(idx, cod));
  let cargos = $derived([...(m.cargos[cod] || [])].sort((a, b) => a[1].localeCompare(b[1]) || Number(b[2]) - Number(a[2])));
  let dirigente = $derived(cargoDirigente(m.cargos[cod]));
  let pessoas = $derived(idx.ocupantesPorUnidade.get(cod) || []);
  let filhos = $derived(idx.filhos.get(cod) || []);
  let bloco = $derived(BLOCOS.find((b) => b.id === u.b));
  let uo = $derived(Object.entries(m.orcamento?.uos || {}).find(([, v]) => v.siorg === cod));
  let politicas = $derived(m.politicas.filter((p) => p.unidades?.includes(cod)));
  let totalCargos = $derived(cargos.reduce((s, c) => s + c[4], 0));
</script>

<section class="cartao" aria-labelledby="t-unidade">
  <div class="topo">
    <button type="button" class="botao fechar" onclick={() => trocarParams({ u: null })}>✕ <span class="sr-only">Fechar detalhe</span></button>
    <nav class="trilha" aria-label="Hierarquia">
      {#each trilha.slice(0, -1) as t (t.c)}
        <button type="button" onclick={() => selecionar(t.c)}>{t.s}</button><span aria-hidden="true"> › </span>
      {/each}
    </nav>
    <h2 id="t-unidade">{u.n}</h2>
    <div class="chips">
      <span class="chip">{u.s}</span>
      {#if bloco}<span class="chip">{bloco.nome}</span>{/if}
      {#if u.a}<span class="chip">{u.a === "fim" ? "Atividade-fim" : "Atividade-meio (suporte)"}</span>{/if}
      <span class="chip">SIORG {u.c}</span>
    </div>
  </div>

  <h3>Quem dirige</h3>
  {#if pessoas.length}
    <ul class="pessoas">
      {#each pessoas as p (p.pessoa)}
        <li>
          <strong>{p.nome}</strong>
          <span class="sec">{p.cargo}</span>
          <span class="mudo">Partido: {p.partido || "não informado"} · Início: {p.de ? fmtData(p.de) : "não verificado"}</span>
        </li>
      {/each}
    </ul>
    <Fonte fonte={{ nome: "gov.br – Quem é Quem", url: pessoas[0].fonte, data: pessoas[0].verificado_em }} rotuloData="Verificado em" curado />
  {:else}
    <p class="mudo">Titular ainda não curado{dirigente ? ` · cargo: ${dirigente.denominacao} (${dirigente.rotulo})` : ""}.</p>
  {/if}

  {#if cargos.length}
    <h3>Cargos e funções ({num(totalCargos)})</h3>
    <div class="tabela-rolagem">
      <table>
        <thead><tr><th>Código</th><th>Denominação</th><th class="num">Qtd.</th></tr></thead>
        <tbody>
          {#each cargos as c, i (i)}
            <tr><td class="codigo">{rotuloCargo(c[0], c[1], c[2])}</td><td>{c[3]}</td><td class="num">{c[4]}</td></tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}

  {#if filhos.length}
    <h3>Unidades subordinadas ({contarDescendentes(idx, cod)})</h3>
    <ul class="subs">
      {#each filhos as f (f.c)}
        <li><button type="button" onclick={() => selecionar(f.c)}><strong>{f.s}</strong> {f.n}</button></li>
      {/each}
    </ul>
  {/if}

  {#if u.comp?.length}
    <h3>Competências</h3>
    <ol class="comp">
      {#each u.comp as c, i (i)}<li>{c}</li>{/each}
    </ol>
  {/if}

  {#if uo || politicas.length}
    <h3>Ligações</h3>
    <ul class="links">
      {#if uo}<li>Orçamento próprio: <a href={href(["m", m.id, "orcamento"], { uo: uo[0] })}>UO {uo[0]}</a></li>{/if}
      {#each politicas as p (p.id)}<li>Política: <a href={href(["m", m.id, "politicas"], { p: p.id })}>{p.nome}</a></li>{/each}
    </ul>
  {/if}

  {#if u.ato}
    <p class="mudo pequeno">
      Última alteração registrada no SIORG: {u.ato.tipo} nº {u.ato.numero}{u.ato.vigencia ? `, vigente desde ${fmtData(u.ato.vigencia)}` : ""}.
      {#if u.ato.url}<a href={u.ato.url} target="_blank" rel="noopener">Ver no DOU</a>{/if}
    </p>
  {/if}
  <Fonte fonte={m.fontes.estrutura} rotuloData="Coletado em" />
</section>

<style>
  .topo { position: relative; padding-right: 48px; }
  .fechar { position: absolute; right: 0; top: 0; width: 36px; padding: 0; justify-content: center; }
  .trilha { font-size: 0.8rem; color: var(--mudo); }
  .trilha button { background: none; border: 0; padding: 2px; color: var(--link); cursor: pointer; text-decoration: underline; font-size: inherit; }
  h2 { margin: 4px 0 8px; }
  .chips { display: flex; flex-wrap: wrap; gap: 6px; }
  h3 { margin-top: 20px; }
  .pessoas, .subs, .links { list-style: none; padding: 0; margin: 0; display: grid; gap: 8px; }
  .pessoas li { display: grid; gap: 1px; }
  .pessoas .mudo { font-size: 0.82rem; }
  .subs button { background: none; border: 0; padding: 4px 0; text-align: left; cursor: pointer; color: var(--texto); font-size: 0.9rem; }
  .subs button:hover { color: var(--link); text-decoration: underline; }
  .comp { padding-left: 22px; margin: 0; font-size: 0.9rem; display: grid; gap: 6px; }
  .pequeno { font-size: 0.8rem; margin-top: 18px; }
  .codigo { white-space: nowrap; font-variant-numeric: tabular-nums; }
</style>
