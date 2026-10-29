/**
 * Gera CSV no formato que o Excel em português abre direto: separador ";", vírgula decimal
 * e BOM UTF-8 (para manter os acentos).
 * colunas: [{ chave, titulo }] · linhas: objetos
 */
export function paraCsv(colunas, linhas) {
  const celula = (v) => {
    if (v == null) return "";
    if (typeof v === "number") return String(v).replace(".", ",");
    const s = String(v);
    return /[";\n\r]/.test(s) ? `"${s.replaceAll('"', '""')}"` : s;
  };
  const cab = colunas.map((c) => celula(c.titulo)).join(";");
  const corpo = linhas.map((l) => colunas.map((c) => celula(l[c.chave])).join(";"));
  return "﻿" + [cab, ...corpo].join("\r\n") + "\r\n";
}

export function baixarCsv(nomeArquivo, colunas, linhas) {
  const blob = new Blob([paraCsv(colunas, linhas)], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = Object.assign(document.createElement("a"), { href: url, download: nomeArquivo });
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
