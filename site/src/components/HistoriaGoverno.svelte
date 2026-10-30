<script>
  import { data as fmtData, brlCompacto, mesAno } from "../lib/formato.js";
  import { TIPOS_EVENTO, GOVERNOS, porNorma, corrigir } from "../lib/historia.js";
  import { href } from "../lib/estado.svelte.js";
  import GraficoSerie from "./GraficoSerie.svelte";

  /** idx: index.json (serie_ministerios, eventos, normas, orcamento_anual_total, ipca) */
  let { idx } = $props();

  const serie = $derived(idx.serie_ministerios.map((l) => ({ data: l[0], total: l[1], min: l[2], pres: l[3], outros: l[4] })));
  let porData = $derived(new Map(serie.map((s) => [s.data, s])));
  let seriesContagem = $derived([{
    nome: "Órgãos com status de ministério", cor: "--series-1", pontos: serie.map((s) => [s.data, s.total]),
    dica: (x) => {
      const d = porData.get(new Date(x).toISOString().slice(0, 10)) ?? [...porData.values()].filter((s) => s.data <= new Date(x).toISOString().slice(0, 10)).at(-1);
      return d ? `<div style="margin-top:4px;opacity:.75">${d.min} ministérios · ${d.pres} da Presidência · ${d.outros} outros (AGU, CGU)</div>` : "";
    },
  }]);
  let maximo = $derived(serie.reduce((a, b) => (b.total > a.total ? b : a), serie[0]));
  let minimo = $derived(serie.reduce((a, b) => (b.total < a.total ? b : a), serie[0]));

  let filtroTipo = $state("");
  let reformas = $derived(porNorma(idx.eventos.filter((e) => !filtroTipo || e.tipo === filtroTipo), idx.normas));
  let abertas = $state(new Set());
  const alternar = (k) => { const s = new Set(abertas); s.has(k) ? s.delete(k) : s.add(k); abertas = s; };
  let noPainel = $derived(new Set(idx.ministerios.map((m) => m.id)));

  let real = $state(true);
  let seriesOrc = $derived([
    { nome: "Dotação atual", cor: "--etapa-1", pontos: idx.orcamento_anual_total.map((l) => [String(l[0]), real ? corrigir(l[1], l[0], idx.ipca) : l[1]]) },
    { nome: "Pago", cor: "--etapa-3", pontos: idx.orcamento_anual_total.map((l) => [String(l[0]), real ? corrigir(l[2], l[0], idx.ipca) : l[2]]) },
  ]);
</script>

<section class="cartao" aria-labelledby="t-esplanada">
  <h2 id="t-esplanada">Como a Esplanada mudou desde 2003</h2>
  <div class="tiles">
    <div class="tile"><div class="rot">Mais órgãos com status de ministério</div><div class="val num">{maximo.total}</div><div class="det">em {fmtData(maximo.data)}</div></div>
    <div class="tile"><div class="rot">Menos</div><div class="val num">{minimo.total}</div><div class="det">em {fmtData(minimo.data)}</div></div>
    <div class="tile"><div class="rot">Hoje</div><div class="val num">{serie.at(-1).total}</div><div class="det">{serie.at(-1).min} ministérios, {serie.at(-1).pres} da Presidência, {serie.at(-1).outros} outros</div></div>
    <div class="tile"><div class="rot">Mudanças registradas</div><div class="val num">{idx.eventos.length}</div><div class="det">em {porNorma(idx.eventos).length} normas</div></div>
  </div>
  <GraficoSerie series={seriesContagem} tempo degrau marcas={GOVERNOS} fmt={(v) => v} fmtX={(x) => fmtData(new Date(x).toISOString().slice(0, 10))} altura={280}
    tabelaTitulo="A partir de" rotulo={`Número de órgãos com status de ministério desde 2003: de ${minimo.total} a ${maximo.total}; hoje ${serie.at(-1).total}.`} />
  <p class="mudo pequeno">Conta ministérios e órgãos cujo titular tem status (ou prerrogativas) de Ministro de Estado: secretarias da Presidência, AGU e CGU. Não inclui o presidente do Banco Central, que teve esse status de 2004 a 2021. Linhas verticais: início de cada governo.</p>

  <div class="cab-secao espaco">
    <h3>Reformas, norma por norma</h3>
    <label class="sr-only" for="tipo-ev">Tipo de mudança</label>
    <select id="tipo-ev" bind:value={filtroTipo}>
      <option value="">Todas as mudanças</option>
      {#each Object.entries(TIPOS_EVENTO) as [k, v] (k)}<option value={k}>{v}</option>{/each}
    </select>
  </div>
  <ul class="reformas">
    {#each reformas as r (r.norma ?? r.data)}
      <li>
        <button type="button" class="cab-reforma" aria-expanded={abertas.has(r.norma)} onclick={() => alternar(r.norma)}>
          <span class="quando num">{fmtData(r.data)}</span>
          <strong>{r.info ? `${r.info.tipo} ${r.info.numero}` : "Norma"}</strong>
          <span class="mudo">{r.eventos.length} mudança{r.eventos.length > 1 ? "s" : ""}</span>
          <span class="chips">{#each [...new Set(r.eventos.map((e) => e.tipo))] as t (t)}<span class="chip">{TIPOS_EVENTO[t]}</span>{/each}</span>
          <span aria-hidden="true" class="seta" class:girada={abertas.has(r.norma)}>▸</span>
        </button>
        {#if abertas.has(r.norma)}
          <ul class="eventos">
            {#each r.eventos as e (e.id)}
              <li>
                <span class="chip">{TIPOS_EVENTO[e.tipo]}</span> {e.descricao}
                <div class="mudo fluxo">
                  {#each Object.entries(e.nomes.origem) as [id, nome], i (id)}{i ? " + " : ""}{nome}{/each}
                  {#if Object.keys(e.nomes.origem).length} → {/if}
                  {#each Object.entries(e.nomes.destino) as [id, nome], i (id)}{i ? " + " : ""}{#if noPainel.has(id)}<a href={href(["m", id, "sobre"])}>{nome}</a>{:else}{nome}{/if}{/each}
                  {#if !Object.keys(e.nomes.destino).length}extinto{/if}
                </div>
              </li>
            {/each}
            {#if r.info?.url}<li><a href={r.info.url} target="_blank" rel="noopener">Ler a norma no Planalto</a></li>{/if}
          </ul>
        {/if}
      </li>
    {/each}
  </ul>
</section>

<section class="cartao" aria-labelledby="t-orc-anos">
  <div class="cab-secao">
    <h2 id="t-orc-anos">Orçamento dos órgãos atuais desde 2014</h2>
    <div class="segmentado" role="group" aria-label="Valores">
      <button type="button" aria-pressed={real} onclick={() => (real = true)}>Corrigido pela inflação</button>
      <button type="button" aria-pressed={!real} onclick={() => (real = false)}>Valores da época</button>
    </div>
  </div>
  <p class="sec pequeno">Soma dos órgãos orçamentários dos {idx.ministerios.filter((m) => m.orcamento).length} órgãos atuais com orçamento próprio, sem operações especiais.</p>
  <GraficoSerie series={seriesOrc} tipo="bar" fmt={(v) => (v == null ? "–" : brlCompacto(v))} tabelaTitulo="Ano"
    rotulo="Dotação atual e pago por ano, soma dos órgãos atuais, sem operações especiais" />
  <p class="mudo pequeno">{real && idx.ipca ? `Valores em reais de ${mesAno(idx.ipca.referencia)} (média do IPCA de cada ano). ` : ""}O último ano ainda está em execução. Fonte: Portal da Transparência (2014 é o primeiro ano com dados abertos).</p>
</section>

<style>
  .cartao { margin-top: 16px; }
  .pequeno { font-size: 0.8rem; margin: 6px 0 10px; }
  .espaco { margin-top: 20px; }
  h3 { margin: 0; }
  .reformas { list-style: none; padding: 0; margin: 0; display: grid; gap: 6px; }
  .cab-reforma { width: 100%; display: flex; flex-wrap: wrap; align-items: center; gap: 6px 12px; text-align: left; background: var(--cartao-2); border: 1px solid var(--linha); border-radius: 10px; padding: 10px 12px; cursor: pointer; }
  .cab-reforma:hover { border-color: var(--marca); }
  .chips { display: flex; flex-wrap: wrap; gap: 4px; }
  .seta { margin-left: auto; transition: transform 0.15s; }
  .seta.girada { transform: rotate(90deg); }
  .quando { font-size: 0.8rem; color: var(--mudo); }
  .eventos { list-style: none; padding: 8px 4px 4px 14px; margin: 0; display: grid; gap: 10px; border-left: 3px solid var(--linha); margin-left: 10px; }
  .eventos li { font-size: 0.9rem; }
  .fluxo { font-size: 0.8rem; margin-top: 2px; }
</style>
