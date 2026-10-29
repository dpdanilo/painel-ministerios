import io
import zipfile

import pytest

from etl import orcamento, siorg, validar
from etl.publicar import separar_competencias
from etl.versionamento import mesclar

URI = "https://estruturaorganizacional.dados.gov.br/id/"


# ------------------------------------------------------------------ versionamento

def test_mesclar_linha_nova_alterada_e_removida():
    antigas = [
        {"cod": "1", "nome": "A", "m": "x", "valido_de": "2025-01-01", "valido_ate": ""},
        {"cod": "2", "nome": "B", "m": "x", "valido_de": "2025-01-01", "valido_ate": ""},
        {"cod": "3", "nome": "C", "m": "x", "valido_de": "2025-01-01", "valido_ate": ""},
    ]
    novas = [
        {"cod": "1", "nome": "A", "m": "x"},                              # igual
        {"cod": "2", "nome": "B2", "m": "x", "valido_de": "2026-03-01"},  # renomeada
        {"cod": "4", "nome": "D", "m": "x"},                              # nova
    ]
    r = mesclar(antigas, novas, ["cod"], ["nome"], "2026-05-01")
    por = {(x["cod"], x["valido_de"]): x for x in r}
    assert por[("1", "2025-01-01")]["valido_ate"] == ""
    assert por[("2", "2025-01-01")]["valido_ate"] == "2026-03-01"
    assert por[("2", "2026-03-01")]["nome"] == "B2" and por[("2", "2026-03-01")]["valido_ate"] == ""
    assert por[("3", "2025-01-01")]["valido_ate"] == "2026-05-01"
    assert por[("4", "2026-05-01")]["valido_ate"] == ""


def test_mesclar_nao_fecha_linhas_fora_do_escopo():
    antigas = [{"cod": "9", "nome": "Z", "m": "outro", "valido_de": "2025-01-01", "valido_ate": ""}]
    r = mesclar(antigas, [], ["cod"], ["nome"], "2026-05-01", {"m": {"x"}})
    assert r[0]["valido_ate"] == ""


def test_mesclar_alteracao_sem_data_nova_usa_snapshot():
    antigas = [{"cod": "1", "nome": "A", "valido_de": "2025-01-01", "valido_ate": ""}]
    r = mesclar(antigas, [{"cod": "1", "nome": "A2", "valido_de": "2025-01-01"}], ["cod"], ["nome"], "2026-05-01")
    assert sorted((x["valido_de"], x["valido_ate"]) for x in r) == [("2025-01-01", "2026-05-01"), ("2026-05-01", "")]


# ------------------------------------------------------------------ SIORG

def _u(cod, pai, tipo="unidade-administrativa", cat="6", nome=None, area="Suporte"):
    return {"codigoUnidade": f"{URI}unidade-organizacional/{cod}", "codigoUnidadePai": f"{URI}unidade-organizacional/{pai}",
            "codigoTipoUnidade": f"{URI}tipo-unidade/{tipo}", "codigoCategoriaUnidade": f"{URI}categoria-unidade/{cat}",
            "nome": nome or f"U{cod}", "sigla": f"S{cod}", "areaAtuacao": area, "competencia": "",
            "versaoConsulta": "1.0.0", "dataInicialVersaoConsulta": "2026-01-01"}


def test_unidades_blocos_e_heranca():
    bruto = [
        _u(100, 26, tipo="orgao", cat="1"),
        _u(1, 100, cat="6"),                       # Gabinete → assistência
        _u(2, 100, cat="8", area="Finalística"),   # Secretaria → singular
        _u(21, 2, cat="6"),                        # coordenação de apoio dentro da secretaria → herda singular
        _u(22, 2, tipo="unidade-colegiada", cat="7"),
        _u(3, 100, tipo="entidade", cat="39"),
        _u(31, 3),                                 # interna da entidade: não entra
    ]
    un = {u["cod_siorg"]: u for u in siorg.unidades_de(bruto, "mx", "100")}
    assert un["100"]["profundidade"] == 0 and un["100"]["cod_pai"] == ""
    assert un["1"]["bloco"] == "assistencia"
    assert un["2"]["bloco"] == "singular" and un["2"]["atividade"] == "fim"
    assert un["21"]["bloco"] == "singular" and un["21"]["profundidade"] == 2
    assert un["22"]["bloco"] == "colegiado"
    assert un["3"]["bloco"] == "vinculada"
    assert "31" not in un


def test_cargos_agrega_por_unidade_e_nivel():
    base = {"codigoOrgao": 100, "codigoUnidade": 2, "siglaCargo": "CCE", "categoriaCargo": "1", "nivelCargo": "17",
            "denominacaoCargo": "Secretário", "mobilidade": "FX", "total": 1}
    alocados = [base, {**base, "total": 2}, {**base, "codigoOrgao": 999}]
    c = siorg.cargos_de(alocados, "mx", "100")
    assert len(c) == 1 and c[0]["quantidade"] == 3


# ------------------------------------------------------------------ orçamento

def _zip(tmp_path, nome, cabecalho, linhas):
    texto = "\r\n".join(";".join(f'"{v}"' for v in l) for l in [cabecalho, *linhas]) + "\r\n"
    caminho = tmp_path / nome
    with zipfile.ZipFile(caminho, "w") as z:
        z.writestr(nome.replace(".zip", ".csv"), texto.encode("latin-1"))
    return caminho


def test_num_formato_brasileiro():
    assert orcamento._num("1234,56") == 1234.56
    assert orcamento._num("-10,00") == -10.0
    assert orcamento._num("") == 0


def test_ler_anual_filtra_orgao_e_soma(tmp_path):
    cab = ["EXERCÍCIO", "CÓDIGO ÓRGÃO SUPERIOR", "NOME ÓRGÃO SUPERIOR", "CÓDIGO ÓRGÃO SUBORDINADO", "NOME ÓRGÃO SUBORDINADO",
           "CÓDIGO UNIDADE ORÇAMENTÁRIA", "NOME UNIDADE ORÇAMENTÁRIA", "CÓDIGO PROGRAMA ORÇAMENTÁRIO",
           "NOME PROGRAMA ORÇAMENTÁRIO", "CÓDIGO AÇÃO", "NOME AÇÃO", "ORÇAMENTO INICIAL (R$)",
           "ORÇAMENTO ATUALIZADO (R$)", "ORÇAMENTO EMPENHADO (R$)"]
    l1 = ["2026", "56000", "MCID", "56000", "MCID", "56101", "MCID", "2320", "MORADIA", "00AF", "FAR", "100,50", "90,00", "10,00"]
    l2 = [*l1[:11], "1,50", "1,00", "0,00"]
    outro = ["2026", "41000", *l1[2:]]
    agg, nomes, _ = orcamento.ler_anual(_zip(tmp_path, "a.zip", cab, [l1, l2, outro]), {"56000"})
    (k, v), = agg.items()
    assert k[3:] == ("56101", "2320", "00AF")
    assert v["dotacao_inicial"] == pytest.approx(102.0) and v["dotacao_atual"] == pytest.approx(91.0)
    assert nomes["acao"]["00AF"] == ("FAR", "2320")


def test_ler_mensal_filtra_por_uo_e_separa_emendas(tmp_path):
    cab = ["Ano e mês do lançamento", "Código Unidade Orçamentária", "Código Programa Orçamentário", "Código Ação",
           "Valor Empenhado (R$)", "Valor Liquidado (R$)", "Valor Pago (R$)", "Valor Restos a Pagar Pagos (R$)",
           "Nome Autor Emenda"]
    linhas = [["2026/03", "56101", "2320", "00AF", "10,00", "5,00", "4,00", "1,00", "SEM EMENDA"],
              ["2026/03", "56101", "2320", "00AF", "3,00", "0,00", "0,00", "0,00", "FULANO"],
              ["2026/03", "99999", "2320", "00AF", "50,00", "0,00", "0,00", "0,00", "SEM EMENDA"]]
    agg, _ = orcamento.ler_mensal(_zip(tmp_path, "m.zip", cab, linhas), {"56101"})
    v = agg[("56101", "2320", "00AF")]
    assert (v["empenhado"], v["liquidado"], v["pago"], v["empenhado_emendas"]) == (13.0, 5.0, 4.0, 3.0)


# ------------------------------------------------------------------ publicação

def test_separar_competencias():
    t = "I - política urbana;  II - habitação, saneamento;  e III - mobilidade."
    assert separar_competencias(t) == ["Política urbana", "Habitação, saneamento", "Mobilidade"]


# ------------------------------------------------------------------ validador

def _curadoria(tmp_path, ocupacoes="", politicas="", normas="", sem_fonte=False):
    (tmp_path / "ministerios.yaml").write_text(f"""
ministerios:
  - id: mx
    no_painel: true
    versoes:
      - {{nome: M, sigla: MX, cod_siorg: "100", valido_de: 2023-01-01, valido_ate: null, norma_criacao: lei-1-2023{'' if sem_fonte else ', fonte: x'}}}
""", encoding="utf-8")
    (tmp_path / "normas.yaml").write_text("normas:\n  - {id: lei-1-2023, url: x}\n" + normas, encoding="utf-8")
    (tmp_path / "pessoas.yaml").write_text("pessoas:\n  - {id: a, nome: A}\n  - {id: b, nome: B}\n", encoding="utf-8")
    (tmp_path / "ocupacoes.yaml").write_text("ocupacoes:\n" + ocupacoes, encoding="utf-8")
    (tmp_path / "politicas_publicas.yaml").write_text("politicas:\n" + politicas, encoding="utf-8")
    return tmp_path


def test_validador_acusa_titulares_sobrepostos(tmp_path):
    p = _curadoria(tmp_path, ocupacoes="""
  - {pessoa: a, unidade: "100", papel: titular, valido_de: 2023-01-01, valido_ate: 2024-06-01, fonte: x}
  - {pessoa: b, unidade: "100", papel: titular, valido_de: 2024-01-01, valido_ate: null, fonte: x}
""")
    rel = validar.Relatorio()
    validar.validar_curadoria(rel, p, unidades={"100"})
    assert any("sobrepostos" in e for e in rel.erros)


def test_validador_aceita_titulares_em_sequencia(tmp_path):
    p = _curadoria(tmp_path, ocupacoes="""
  - {pessoa: a, unidade: "100", papel: titular, valido_de: 2023-01-01, valido_ate: 2024-01-01, fonte: x}
  - {pessoa: b, unidade: "100", papel: titular, valido_de: 2024-01-01, valido_ate: null, fonte: x}
""")
    rel = validar.Relatorio()
    validar.validar_curadoria(rel, p, unidades={"100"})
    assert rel.erros == []


def test_validador_acusa_sem_fonte_codigo_e_acao_inexistentes(tmp_path):
    p = _curadoria(tmp_path, sem_fonte=True,
                   ocupacoes='  - {pessoa: zz, unidade: "777", papel: titular, fonte: x}\n',
                   politicas='  - {id: p1, nome: P, ministerio: mx, vinculos: [{exercicio: 2026, acao: "XXXX", justificativa: j, fonte: f}]}\n')
    rel = validar.Relatorio()
    validar.validar_curadoria(rel, p, unidades={"100"}, acoes={("2026", "00AF")})
    texto = "\n".join(rel.erros)
    assert "sem fonte" in texto
    assert "pessoa não existe" in texto
    assert "unidade 777" in texto
    assert "ação XXXX" in texto


def test_validador_unidades_pai_inexistente_e_ciclo():
    linhas = [
        {"cod_siorg": "1", "cod_pai": "", "profundidade": "0", "bloco": "", "sigla": "R", "categoria": "1", "valido_de": "", "valido_ate": ""},
        {"cod_siorg": "2", "cod_pai": "3", "profundidade": "1", "bloco": "singular", "sigla": "A", "categoria": "8", "valido_de": "", "valido_ate": ""},
        {"cod_siorg": "3", "cod_pai": "2", "profundidade": "1", "bloco": "singular", "sigla": "B", "categoria": "8", "valido_de": "", "valido_ate": ""},
        {"cod_siorg": "4", "cod_pai": "99", "profundidade": "1", "bloco": "singular", "sigla": "C", "categoria": "8", "valido_de": "", "valido_ate": ""},
    ]
    rel = validar.Relatorio()
    validar.validar_unidades(rel, linhas)
    assert any("ciclo" in e for e in rel.erros)
    assert any("pai 99" in e for e in rel.erros)


# ------------------------------------------------------------------ dados do repositório

def test_dados_versionados_passam_na_validacao():
    rel = validar.validar_tudo()
    assert rel.erros == [], rel.texto()
