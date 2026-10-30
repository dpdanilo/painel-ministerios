<script>
  import { href } from "../lib/estado.svelte.js";
  import { data as fmtData, mesAno } from "../lib/formato.js";

  /** ministerios: resumos do index (com `ministros[]`) · fim: "AAAA-MM" do último mês com dados */
  let { ministerios, fim } = $props();

  const INICIO = new Date("2023-01-01").getTime();
  let FIM = $derived(new Date(`${fim}-28`).getTime());
  const pos = (iso, padrao) => {
    const t = iso ? new Date(iso.length === 7 ? `${iso}-01` : iso).getTime() : padrao;
    return Math.min(100, Math.max(0, (100 * (t - INICIO)) / (FIM - INICIO)));
  };
  let linhas = $derived(ministerios
    .filter((m) => m.ministros?.length)
    .map((m) => ({ m, segs: m.ministros.map((o, i) => ({ ...o, i, x0: pos(o.de, INICIO), x1: pos(o.ate, FIM) })) }))
    .sort((a, b) => b.segs.length - a.segs.length || a.m.sigla.localeCompare(b.m.sigla)));
  let anos = $derived([2023, 2024, 2025, 2026].map((a) => ({ a, x: pos(`${a}-01-01`, INICIO) })));
</script>

<div class="legenda" aria-hidden="true">
  <span><i class="t0"></i><i class="t1"></i>cada segmento é um(a) ministro(a); tons alternados separam trocas</span>
</div>
<div class="gantt" role="list" aria-label="Ministros de cada órgão desde janeiro de 2023">
  <div class="eixo" aria-hidden="true">
    <span class="rot"></span>
    <span class="trilha">{#each anos as a (a.a)}<span class="ano" style="left: {a.x}%">{a.a}</span>{/each}</span>
  </div>
  {#each linhas as { m, segs } (m.id)}
    <div class="linha" role="listitem">
      <a class="rot" href={href(["m", m.id, "pessoas"])} title={m.nome}>{m.sigla}</a>
      <span class="trilha">
        {#each anos as a (a.a)}<span class="grade" style="left: {a.x}%" aria-hidden="true"></span>{/each}
        {#each segs as s (s.i)}
          <span class="seg t{s.i % 2}" style="left: {s.x0}%; width: {Math.max(0.6, s.x1 - s.x0)}%"
            title={`${s.nome}${s.partido ? ` (${s.partido})` : ""}: ${fmtData(s.de) ?? "?"} – ${s.ate ? `~${mesAno(s.ate)}` : "hoje"}`}>
            {#if s.x1 - s.x0 > 9}<span class="nome">{s.nome}{s.partido ? ` · ${s.partido}` : ""}</span>{/if}
          </span>
        {/each}
        <span class="sr-only">{segs.map((s) => `${s.nome}${s.partido ? `, ${s.partido}` : ""}, de ${fmtData(s.de) ?? "?"} a ${s.ate ? mesAno(s.ate) : "hoje"}`).join("; ")}</span>
      </span>
    </div>
  {/each}
</div>

<style>
  .legenda { font-size: 0.82rem; color: var(--sec); margin-bottom: 8px; }
  .legenda i { display: inline-block; width: 14px; height: 10px; border-radius: 2px; margin-right: 2px; vertical-align: -1px; }
  .legenda i:last-of-type { margin-right: 8px; }
  .t0 { background: var(--gantt-a); color: var(--gantt-a-txt); }
  .t1 { background: var(--gantt-b); color: var(--gantt-b-txt); }
  .gantt { display: grid; gap: 3px; }
  .eixo, .linha { display: grid; grid-template-columns: 76px 1fr; gap: 8px; align-items: center; }
  .rot { font-size: 0.8rem; font-weight: 700; color: var(--texto); text-decoration: none; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  a.rot:hover { color: var(--link); text-decoration: underline; }
  .trilha { position: relative; height: 22px; }
  .eixo .trilha { height: 18px; }
  .ano { position: absolute; top: 0; transform: translateX(-50%); font-size: 0.72rem; color: var(--mudo); }
  .ano:first-child { transform: none; }
  .grade { position: absolute; top: 0; bottom: 0; width: 1px; background: var(--grade); }
  .seg { position: absolute; top: 2px; bottom: 2px; border-radius: 4px; box-shadow: 0 0 0 1px var(--cartao); overflow: hidden; }
  .nome { position: absolute; left: 6px; right: 4px; top: 50%; transform: translateY(-50%); font-size: 0.7rem; font-weight: 600; color: inherit; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
</style>
