<script>
  import { carregarIndice } from "../lib/dados.js";
  import { brlCompacto, num, pct, data as fmtData } from "../lib/formato.js";
  import { href } from "../lib/estado.svelte.js";

  const indice = carregarIndice();
</script>

<div class="conteudo">
  <section class="intro">
    <h1>Como o Governo Federal se organiza</h1>
    <p class="sec">
      Secretarias, departamentos, cargos, quem ocupa cada posto e quanto cada ministério tem para gastar,
      a partir dos dados oficiais do SIORG e do Portal da Transparência.
    </p>
  </section>

  {#await indice}
    <p class="mudo" role="status">Carregando…</p>
  {:then idx}
    <h2>Ministérios no painel</h2>
    <div class="lista">
      {#each idx.ministerios as m (m.id)}
        <a class="cartao ministerio" href={href(["m", m.id, "estrutura"])}>
          <div class="cab">
            <span class="sigla">{m.sigla}</span>
            <strong>{m.nome}</strong>
            {#if m.ministro}<span class="sec">Ministro: {m.ministro.nome}{m.ministro.partido ? ` (${m.ministro.partido})` : ""}</span>{/if}
          </div>
          <dl class="numeros">
            <div><dt>Secretarias nacionais</dt><dd class="num">{num(m.n_secretarias)}</dd></div>
            <div><dt>Unidades</dt><dd class="num">{num(m.n_unidades)}</dd></div>
            <div><dt>Cargos e funções</dt><dd class="num">{num(m.n_cargos)}</dd></div>
            {#if m.orcamento}
              <div><dt>Orçamento {m.orcamento.exercicio}</dt><dd class="num">{brlCompacto(m.orcamento.dotacao_atual)}</dd></div>
              <div><dt>Pago até agora</dt><dd class="num">{pct(m.orcamento.pago, m.orcamento.dotacao_atual)}</dd></div>
            {/if}
          </dl>
          <span class="seta" aria-hidden="true">→</span>
        </a>
      {/each}
    </div>

    <section class="cartao proximos">
      <h2>Em construção</h2>
      <p class="sec">Este é o primeiro ministério publicado. As próximas etapas trazem:</p>
      <ul>
        <li>todos os ministérios atuais, a visão do governo inteiro e a comparação entre ministérios;</li>
        <li>histórico de ministros e secretários, com partido;</li>
        <li>criações, extinções e recriações de ministérios desde 2003, e o orçamento de anos anteriores.</li>
      </ul>
    </section>

    <section class="cartao">
      <h2>Fontes e atualização</h2>
      <ul class="fontes">
        {#each Object.entries(idx.fontes) as [id, f] (id)}
          <li>
            <a href={f.url} target="_blank" rel="noopener">{f.nome}</a>
            <span class="mudo"> · dados de {fmtData(f.data_referencia)} · última mudança detectada em {fmtData(f.coletado_em)}</span>
          </li>
        {/each}
      </ul>
      <p class="mudo pequeno">Página gerada em {fmtData(idx.gerado_em)}. A coleta é automática; dados que dependem de leitura humana (ocupantes, partidos, políticas) são marcados como <span class="chip">curado</span>.</p>
    </section>
  {:catch erro}
    <p role="alert">{erro.message}</p>
  {/await}
</div>

<style>
  .intro { margin: 8px 0 24px; max-width: 720px; }
  .intro h1 { font-size: clamp(1.5rem, 4vw, 2.1rem); margin: 0 0 8px; }
  .intro p { margin: 0; font-size: 1.02rem; }
  .lista { display: grid; gap: 14px; margin-bottom: 20px; }
  .ministerio { display: grid; grid-template-columns: 1fr auto; gap: 14px 18px; text-decoration: none; color: inherit; transition: border-color 0.15s, transform 0.15s, box-shadow 0.15s; }
  .ministerio:hover { border-color: var(--marca); transform: translateY(-2px); box-shadow: 0 6px 18px rgba(210, 18, 18, 0.12); color: inherit; }
  .cab { display: grid; gap: 2px; }
  .cab strong { font-family: "Montserrat", sans-serif; font-weight: 800; font-size: 1.15rem; }
  .sigla { font-size: 0.78rem; font-weight: 700; color: var(--marca); letter-spacing: 0.05em; }
  .numeros { grid-column: 1 / -1; display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 10px; margin: 0; }
  .numeros div { min-width: 0; }
  .numeros dt { font-size: 0.78rem; color: var(--sec); }
  .numeros dd { margin: 0; font-weight: 700; font-size: 1.15rem; }
  .seta { grid-row: 1; grid-column: 2; width: 36px; height: 36px; border-radius: 50%; background: var(--marca); color: #fff; display: grid; place-items: center; font-weight: 700; }
  .proximos ul, .fontes { margin: 8px 0 0; padding-left: 20px; }
  .fontes li { margin-bottom: 6px; }
  .pequeno { font-size: 0.82rem; margin: 12px 0 0; }
</style>
