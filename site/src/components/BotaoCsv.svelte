<script>
  import { baixarCsv } from "../lib/csv.js";
  /** colunas: [{chave, titulo}], linhas: () => objetos (função, para gerar só no clique) */
  let { arquivo, colunas, linhas } = $props();
</script>

<button type="button" class="botao" onclick={() => baixarCsv(arquivo, colunas, linhas())}>
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M12 3v12m0 0-4-4m4 4 4-4M4 17v3h16v-3"/></svg>
  Baixar CSV
</button>
