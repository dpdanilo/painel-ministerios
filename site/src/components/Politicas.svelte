<script>
  import { rota, href } from "../lib/estado.svelte.js";
  import { linhas, somar } from "../lib/orcamento.js";
  import { brlCompacto, pct, capitalizar } from "../lib/formato.js";
  import Fonte from "./Fonte.svelte";

  let { m, idx } = $props();
  let orc = $derived(m.orcamento);
  let todas = $derived(linhas(orc));

  function valores(v) {
    if (!orc || String(v.exercicio) !== String(orc.exercicio)) return null;
    return somar(todas.filter((l) => (v.acao && l.acao === v.acao) || (v.programa && l.programa === v.programa)));
  }

  let politicas = $derived(m.politicas.map((p) => {
    const vinc = (p.vinculos || []).map((v) => ({
      ...v,
      nome: v.acao ? capitalizar(orc?.acoes[v.acao]) : capitalizar(orc?.programas[v.programa]),
      val: valores(v),
    }));
    return { ...p, vinc, total: somar(vinc.map((v) => v.val).filter(Boolean)) };
  }));

  $effect(() => {
    const alvo = rota.params.p;
    if (alvo) requestAnimationFrame(() => document.getElementById(`pol-${alvo}`)?.scrollIntoView({ block: "start", behavior: "smooth" }));
  });
</script>

<p class="sec intro">Os programas do orçamento nem sempre têm o nome pelo qual a política é conhecida. Aqui cada política está ligada às ações e programas que a financiam, com a justificativa de cada ligação.</p>

<div class="grade">
  {#each politicas as p (p.id)}
    <section id={`pol-${p.id}`} class="cartao" class:alvo={rota.params.p === p.id} aria-labelledby={`t-${p.id}`}>
      <h2 id={`t-${p.id}`}>{p.nome}</h2>
      {#if p.norma && m.normas[p.norma]}
        <p class="mudo pequeno">Base legal: <a href={m.normas[p.norma].url} target="_blank" rel="noopener">{m.normas[p.norma].tipo} {m.normas[p.norma].numero}</a></p>
      {/if}
      {#if p.unidades?.length}
        <p class="pequeno">Responsável:
          {#each p.unidades as u, i (u)}{i ? ", " : ""}<a href={href(["m", m.id, "estrutura"], { u })}>{idx.porCodigo.get(u)?.n || u}</a>{/each}
        </p>
      {/if}

      {#if p.vinc.length}
        <div class="totais">
          <div><span class="rot">Dotação atual {orc?.exercicio}</span><strong class="num">{brlCompacto(p.total.dotacao_atual)}</strong></div>
          <div><span class="rot">Pago</span><strong class="num">{brlCompacto(p.total.pago)}</strong><span class="mudo"> {pct(p.total.pago, p.total.dotacao_atual)}</span></div>
        </div>
        <ul class="vinculos">
          {#each p.vinc as v, i (i)}
            <li>
              <a href={href(["m", m.id, "orcamento"], v.acao ? { acao: v.acao, prog: null } : { prog: v.programa })}>
                {v.acao ? `Ação ${v.acao}` : `Programa ${v.programa}`}</a> – {v.nome}
              {#if v.val}<span class="mudo num"> · {brlCompacto(v.val.dotacao_atual)} / pago {brlCompacto(v.val.pago)}</span>{/if}
              <div class="mudo pequeno">{v.justificativa}</div>
            </li>
          {/each}
        </ul>
      {:else}
        <p class="mudo">Ligação com o orçamento ainda em verificação.</p>
      {/if}
      {#if p.nota}<p class="nota pequeno">{p.nota}</p>{/if}
      <Fonte fonte={{ nome: "Curadoria com base no Portal da Transparência e na legislação", url: null }} curado />
    </section>
  {/each}
</div>

<style>
  .intro { max-width: 760px; margin: 0 0 16px; }
  .grade { display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(min(100%, 340px), 1fr)); align-items: start; }
  .cartao + .cartao { margin-top: 0; }
  .alvo { border-color: var(--marca); }
  h2 { margin-bottom: 6px; }
  .pequeno { font-size: 0.82rem; margin: 4px 0; }
  .totais { display: flex; flex-wrap: wrap; gap: 18px; margin: 12px 0; }
  .totais div { display: grid; }
  .totais .rot { font-size: 0.78rem; color: var(--sec); }
  .totais strong { font-size: 1.3rem; }
  .vinculos { list-style: none; padding: 0; margin: 0; display: grid; gap: 10px; font-size: 0.9rem; }
  .nota { background: var(--cartao-2); padding: 8px 10px; border-radius: 8px; margin-top: 12px; }
</style>
