<script>
  import { carregarIndice, carregar } from "../lib/dados.js";
  import { rota, href, trocarParams } from "../lib/estado.svelte.js";
  import { brlCompacto, num, pct, capitalizar, partidoSigla, duracao } from "../lib/formato.js";
  import { CATEGORIAS, execucao, atribuirSlots, niveisDirecao, cargosDirecao } from "../lib/governo.js";
  import { BLOCOS } from "../lib/estrutura.js";
  import LinhasPercentual from "../components/LinhasPercentual.svelte";
  import BotaoCsv from "../components/BotaoCsv.svelte";

  const MAX = 6;
  let idx = $state(null);
  let agg = $state(null);
  let erro = $state(null);
  Promise.all([carregarIndice(), carregar("agregados/comparacao.json")]).then(([i, a]) => { idx = i; agg = a; }, (e) => (erro = e));

  let ids = $derived((rota.params.m || "").split(",").filter(Boolean).slice(0, MAX));
  let slots = new Map();
  let cores = $derived.by(() => (slots = atribuirSlots(ids, slots, MAX)));
  let resumo = $derived(idx ? new Map(idx.ministerios.map((m) => [m.id, m])) : new Map());
  let detalhe = $derived(agg ? new Map(agg.ministerios.map((m) => [m.id, m])) : new Map());
  let sel = $derived(ids.filter((id) => resumo.has(id)).map((id) => ({ ...resumo.get(id), d: detalhe.get(id), cor: `--series-${cores.get(id) + 1}` })));
  let disponiveis = $derived(idx ? idx.ministerios.filter((m) => !ids.includes(m.id)) : []);

  const remover = (id) => trocarParams({ m: ids.filter((x) => x !== id).join(",") });
  const adicionar = (id) => id && ids.length < MAX && trocarParams({ m: [...ids, id].join(",") });

  const direcao = (m) => Object.entries(m.d.cargos_por_nivel).filter(([k]) => /^(CCE|FCE) 1\./.test(k)).reduce((s, [, q]) => s + q, 0);
  const LINHAS = [
    { nome: "Tipo", v: (m) => CATEGORIAS[m.categoria]?.nome },
    { nome: "Titular", v: (m) => m.ministro?.nome ?? "—" },
    { nome: "Partido do titular (última candidatura)", v: (m) => (m.ministro ? partidoSigla(m.ministro.partido) ?? "sem candidatura" : "—") },
    { nome: "Ministros desde 2023", v: (m) => m.rotatividade?.ministros.mandatos ?? null, n: true },
    { nome: "Tempo médio de ministro", v: (m) => m.rotatividade?.ministros.meses_medio ?? null, n: true, f: duracao },
    { nome: "Tempo médio de secretário (1.17–1.18)", v: (m) => m.rotatividade?.secretarios.meses_medio ?? null, n: true, f: duracao },
    { nome: "Órgãos finalísticos (1º nível)", v: (m) => m.n_secretarias, n: true },
    { nome: "Unidades", v: (m) => m.n_unidades, n: true, f: num },
    { nome: "Cargos e funções", v: (m) => m.n_cargos, n: true, f: num },
    { nome: "Cargos de direção (CCE/FCE 1.xx)", v: direcao, n: true, f: num },
    { nome: "Unidades finalísticas", v: (m) => m.pct_fim, n: true, f: (v) => pct(v, 1) },
    { nome: "Orçamento sem op. especiais", v: (m) => m.orcamento_sem_oe?.dotacao_atual ?? null, n: true, f: brlCompacto },
    { nome: "Pago sem op. especiais", v: (m) => m.orcamento_sem_oe?.pago ?? null, n: true, f: brlCompacto },
    { nome: "% pago sem op. especiais", v: execucao, n: true, f: (v) => pct(v, 1) },
    { nome: "Orçamento total", v: (m) => m.orcamento?.dotacao_atual ?? null, n: true, f: brlCompacto },
    { nome: "Empenhado via emendas", v: (m) => m.orcamento?.empenhado_emendas ?? null, n: true, f: brlCompacto },
    { nome: "Emendas / empenhado", v: (m) => (m.orcamento?.empenhado ? m.orcamento.empenhado_emendas / m.orcamento.empenhado : null), n: true, f: (v) => pct(v, 1) },
  ];
  const fmt = (l, m) => { const v = l.v(m); return v == null ? "—" : l.f ? l.f(v) : v; };

  let series = $derived(sel.filter((m) => m.orcamento_sem_oe?.dotacao_atual).map((m) => ({
    nome: m.sigla, cor: m.cor, pontos: m.d.mensal_sem_oe.map(([mes, , , pago]) => [mes, pago / m.orcamento_sem_oe.dotacao_atual]),
  })));
  let maxDot = $derived(Math.max(1, ...sel.map((m) => m.orcamento_sem_oe?.dotacao_atual || 0)));
  let niveis = $derived(niveisDirecao(sel.map((m) => m.d)));
  let maxNivel = $derived(Math.max(1, ...niveis.flatMap((n) => sel.map((m) => cargosDirecao(m.d, n)))));

  const colunasCsv = () => [{ chave: "indicador", titulo: "Indicador" }, ...sel.map((m) => ({ chave: m.id, titulo: m.sigla }))];
  const linhasCsv = () => LINHAS.map((l) => ({ indicador: l.nome, ...Object.fromEntries(sel.map((m) => [m.id, l.v(m)])) }));
</script>

<div class="conteudo">
  <nav class="migalhas" aria-label="Você está em"><a href="#/">Governo</a> <span aria-hidden="true">›</span> Comparar</nav>
  <h1>Comparar órgãos</h1>

  {#if erro}
    <p role="alert">{erro.message}</p>
  {:else if !idx}
    <p class="mudo" role="status">Carregando…</p>
  {:else}
    <div class="seletor">
      {#each sel as m (m.id)}
        <span class="sel"><i style="background: var({m.cor})"></i>{m.sigla}
          <button type="button" onclick={() => remover(m.id)} aria-label={`Remover ${m.sigla}`}>✕</button></span>
      {/each}
      {#if ids.length < MAX}
        <label class="sr-only" for="add">Adicionar órgão</label>
        <select id="add" value="" onchange={(e) => { adicionar(e.currentTarget.value); e.currentTarget.value = ""; }}>
          <option value="">+ Adicionar órgão…</option>
          {#each disponiveis as m (m.id)}<option value={m.id}>{m.sigla} – {m.nome}</option>{/each}
        </select>
      {/if}
    </div>

    {#if sel.length < 2}
      <section class="cartao vazio">
        <p>Escolha pelo menos dois órgãos (até {MAX}) para comparar estrutura, cargos e orçamento.</p>
        <p class="sec">Sugestões:
          <a href={href(["comparar"], { m: "mcid,midr" })}>Cidades × Integração</a> ·
          <a href={href(["comparar"], { m: "ms,mec,mds" })}>Saúde × Educação × Desenvolvimento Social</a> ·
          <a href={href(["comparar"], { m: "mmulheres,mir,mpi,mdhc" })}>Mulheres, Igualdade Racial, Povos Indígenas e Direitos Humanos</a>
        </p>
      </section>
    {:else}
      <section class="cartao" aria-labelledby="t-lado">
        <div class="cab-secao">
          <h2 id="t-lado">Lado a lado</h2>
          <BotaoCsv arquivo={`comparacao-${ids.join("-")}.csv`} colunas={colunasCsv()} linhas={linhasCsv} />
        </div>
        <div class="tabela-rolagem">
          <table class="lado">
            <thead><tr><th>Indicador</th>{#each sel as m (m.id)}<th class="num"><a href={href(["m", m.id, "estrutura"])}><i style="background: var({m.cor})"></i>{m.sigla}</a></th>{/each}</tr></thead>
            <tbody>
              {#each LINHAS as l (l.nome)}
                <tr><th scope="row">{l.nome}</th>{#each sel as m (m.id)}<td class:num={l.n}>{fmt(l, m)}</td>{/each}</tr>
              {/each}
            </tbody>
          </table>
        </div>
        <p class="mudo pequeno">Operações especiais = dívida, transferências constitucionais, sentenças e outros encargos. Órgãos da Presidência não têm orçamento separado.</p>
      </section>

      <section class="cartao" aria-labelledby="t-orc">
        <h2 id="t-orc">Orçamento e quanto já foi pago</h2>
        <p class="sec pequeno">Dotação atual sem operações especiais (barra clara) e valor pago (barra colorida), na mesma escala.</p>
        <ul class="barras-orc">
          {#each sel as m (m.id)}
            <li>
              <span class="rot"><i style="background: var({m.cor})"></i><strong>{m.sigla}</strong></span>
              {#if m.orcamento_sem_oe}
                <span class="trilho" aria-hidden="true">
                  <span class="dot" style="width: {(100 * m.orcamento_sem_oe.dotacao_atual) / maxDot}%"></span>
                  <span style="width: {(100 * m.orcamento_sem_oe.pago) / maxDot}%; background: var({m.cor})"></span>
                </span>
                <span class="val num">{brlCompacto(m.orcamento_sem_oe.pago)} de {brlCompacto(m.orcamento_sem_oe.dotacao_atual)} <span class="mudo">({pct(execucao(m), 1)})</span></span>
              {:else}
                <span class="mudo val">orçamento consolidado na Presidência da República</span>
              {/if}
            </li>
          {/each}
        </ul>
      </section>

      {#if series.length}
        <section class="cartao" aria-labelledby="t-ritmo">
          <h2 id="t-ritmo">Ritmo de execução no ano</h2>
          <p class="sec pequeno">Quanto da dotação (sem operações especiais) já foi pago, mês a mês. Porcentagem, para comparar órgãos de tamanhos diferentes.</p>
          <LinhasPercentual {series} rotulo="Pago / dotação" />
        </section>
      {/if}

      <div class="duas">
        <section class="cartao" aria-labelledby="t-niveis">
          <h2 id="t-niveis">Cargos de direção por nível</h2>
          <div class="tabela-rolagem">
            <table>
              <thead><tr><th>Nível</th>{#each sel as m (m.id)}<th class="num">{m.sigla}</th>{/each}</tr></thead>
              <tbody>
                {#each niveis as n (n)}
                  <tr><th scope="row" class="num">1.{String(n).padStart(2, "0")}</th>
                    {#each sel as m (m.id)}
                      {@const q = cargosDirecao(m.d, n)}
                      <td class="num celula"><span class="fundo" style="width: {(100 * q) / maxNivel}%; background: var({m.cor})"></span><span class="txt">{q || "—"}</span></td>
                    {/each}
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
          <p class="mudo pequeno">1.18 = Secretário-Executivo · 1.17 = Secretário · 1.15 = Diretor · 1.13 = Coordenador-Geral.</p>
        </section>

        <section class="cartao" aria-labelledby="t-blocos">
          <h2 id="t-blocos">Unidades por bloco</h2>
          <div class="tabela-rolagem">
            <table>
              <thead><tr><th>Bloco</th>{#each sel as m (m.id)}<th class="num">{m.sigla}</th>{/each}</tr></thead>
              <tbody>
                {#each BLOCOS.filter((b) => sel.some((m) => m.d.unidades_por_bloco[b.id])) as b (b.id)}
                  <tr><th scope="row">{b.nome}</th>{#each sel as m (m.id)}<td class="num">{num(m.d.unidades_por_bloco[b.id] || 0)}</td>{/each}</tr>
                {/each}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      <section aria-labelledby="t-quali">
        <h2 id="t-quali" class="titulo-solto">Quem comanda e o que executa</h2>
        <div class="cards">
          {#each sel as m (m.id)}
            <article class="cartao">
              <h3><i style="background: var({m.cor})"></i><a href={href(["m", m.id, "estrutura"])}>{m.nome}</a></h3>
              <h4>Principais programas{m.orcamento ? ` (${m.orcamento.exercicio})` : ""}</h4>
              {#if m.d.principais_programas.length}
                <ol>
                  {#each m.d.principais_programas as p (p.codigo)}<li>{capitalizar(p.nome)} <span class="mudo num">· {brlCompacto(p.dotacao_atual)}</span></li>{/each}
                </ol>
              {:else}<p class="mudo">Orçamento consolidado na Presidência.</p>{/if}
              <h4>Dirigentes</h4>
              {#if m.d.ocupantes.length}
                <ul>{#each m.d.ocupantes.slice(0, 6) as o, i (i)}<li>{o.nome} <span class="mudo">· {o.cargo}{o.partido ? ` · ${o.partido}` : ""}</span></li>{/each}</ul>
              {:else}<p class="mudo">Sem dados no SIAPE.</p>{/if}
              {#if m.d.politicas.length}
                <h4>Políticas mapeadas</h4>
                <p>{m.d.politicas.join(" · ")}</p>
              {/if}
            </article>
          {/each}
        </div>
      </section>
    {/if}
  {/if}
</div>

<style>
  .migalhas { font-size: 0.85rem; color: var(--mudo); }
  h1 { font-size: clamp(1.4rem, 3.6vw, 2rem); margin: 6px 0 14px; }
  .seletor { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 16px; }
  .sel { display: inline-flex; align-items: center; gap: 6px; padding: 4px 4px 4px 12px; border: 1.5px solid var(--linha); border-radius: 999px; background: var(--cartao); font-weight: 700; font-size: 0.9rem; }
  .sel button { border: 0; background: var(--cartao-2); width: 28px; height: 28px; border-radius: 50%; cursor: pointer; }
  i { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 6px; flex: none; }
  .cartao { margin-top: 16px; }
  .vazio p { margin: 0 0 8px; }
  .pequeno { font-size: 0.82rem; margin: 4px 0 10px; }
  .lado th[scope="row"] { font-weight: 600; text-transform: none; letter-spacing: 0; font-size: 0.88rem; color: var(--texto); }
  .lado thead a { text-decoration: none; color: var(--texto); white-space: nowrap; }
  .barras-orc { list-style: none; padding: 0; margin: 0; display: grid; gap: 12px; }
  .barras-orc li { display: grid; grid-template-columns: 90px 1fr; gap: 4px 10px; align-items: center; }
  .barras-orc .rot { display: flex; align-items: center; }
  .barras-orc .val { grid-column: 2; font-size: 0.82rem; color: var(--sec); }
  .trilho { position: relative; height: 14px; }
  .trilho span { position: absolute; left: 0; top: 0; bottom: 0; border-radius: 0 4px 4px 0; min-width: 2px; }
  .trilho .dot { background: var(--grade); }
  .duas { display: grid; gap: 16px; }
  @media (min-width: 900px) { .duas { grid-template-columns: 1fr 1fr; } }
  .celula { position: relative; }
  .celula .fundo { position: absolute; right: 0; top: 6px; bottom: 6px; opacity: 0.25; border-radius: 3px; }
  .celula .txt { position: relative; }
  .titulo-solto { margin-top: 24px; }
  .cards { display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(min(100%, 280px), 1fr)); }
  .cards .cartao { margin-top: 0; }
  .cards h3 { display: flex; align-items: baseline; }
  .cards h3 a { color: var(--texto); }
  h4 { font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.04em; color: var(--sec); margin: 14px 0 6px; }
  .cards ol, .cards ul { margin: 0; padding-left: 20px; font-size: 0.88rem; display: grid; gap: 4px; }
  .cards p { font-size: 0.88rem; margin: 0; }
</style>
