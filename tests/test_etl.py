import io
import zipfile

import pytest

from etl import orcamento, siorg, validar
from etl.correspondencia import chave_nome
from etl.publicar import e_operacao_especial, separar_competencias
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
    (tmp_path / "pessoas.yaml").write_text("pessoas:\n  - {nome: A, filiacoes: [{partido: X, valido_de: 2020-01-01, valido_ate: null}]}\n", encoding="utf-8")
    (tmp_path / "ocupacoes.yaml").write_text("ocupacoes:\n" + ocupacoes, encoding="utf-8")
    (tmp_path / "politicas_publicas.yaml").write_text("politicas:\n" + politicas, encoding="utf-8")
    return tmp_path


def test_validador_acusa_titulares_sobrepostos(tmp_path):
    p = _curadoria(tmp_path, ocupacoes="""
  - {nome: A, unidade: "100", papel: titular, valido_de: 2023-01-01, valido_ate: 2024-06-01, fonte: x}
  - {nome: B, unidade: "100", papel: titular, valido_de: 2024-01-01, valido_ate: null, fonte: x}
""")
    rel = validar.Relatorio()
    validar.validar_curadoria(rel, p, unidades={"100"})
    assert any("sobrepostos" in e for e in rel.erros)


def test_validador_aceita_titulares_em_sequencia(tmp_path):
    p = _curadoria(tmp_path, ocupacoes="""
  - {nome: A, unidade: "100", papel: titular, valido_de: 2023-01-01, valido_ate: 2024-01-01, fonte: x}
  - {nome: B, unidade: "100", papel: titular, valido_de: 2024-01-01, valido_ate: null, fonte: x}
""")
    rel = validar.Relatorio()
    validar.validar_curadoria(rel, p, unidades={"100"})
    assert rel.erros == ["pessoa A: filiação sem fonte"]


def test_validador_acusa_sem_fonte_codigo_e_acao_inexistentes(tmp_path):
    p = _curadoria(tmp_path, sem_fonte=True,
                   ocupacoes='  - {pessoa: zz, unidade: "777", papel: titular, fonte: x}\n',
                   politicas='  - {id: p1, nome: P, ministerio: mx, vinculos: [{exercicio: 2026, acao: "XXXX", justificativa: j, fonte: f}]}\n')
    rel = validar.Relatorio()
    validar.validar_curadoria(rel, p, unidades={"100"}, acoes={("2026", "00AF")})
    texto = "\n".join(rel.erros)
    assert "sem fonte" in texto
    assert "filiação sem fonte" in texto
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


# ------------------------------------------------------------------ fase 2

def test_chave_nome_para_correspondencia():
    assert chave_nome("Instituto do Patrimônio Histórico e Artístico Nacional") == chave_nome("INSTITUTO PATRIMONIO HISTORICO ARTISTICO NACIONAL")
    assert chave_nome("Ministério das Cidades - Unidades com vínculo direto") == chave_nome("Ministério das Cidades")


def test_operacao_especial():
    assert e_operacao_especial("OPERACOES ESPECIAIS: SERVICO DA DIVIDA INTERNA (JUROS EAMORT")
    assert not e_operacao_especial("MORADIA DIGNA")


def test_validador_aceita_anual_defasado_em_um_mes():
    base = {"exercicio": "2026", "cod_orgao_superior": "1", "cod_uo": "11", "dotacao_inicial": "0", "dotacao_atual": "0",
            "liquidado": "0", "pago": "0"}
    linhas = [{**base, "empenhado": "150", "empenhado_orcdesp": "100"}]   # anual sem o último mês (50)
    mensal = [{"exercicio": "2026", "mes": "1", "cod_uo": "11", "empenhado": "100"},
              {"exercicio": "2026", "mes": "2", "cod_uo": "11", "empenhado": "50"}]
    rel = validar.Relatorio()
    validar.validar_orcamento(rel, linhas, mensal=mensal)
    assert not any("arquivo anual" in a for a in rel.avisos)
    rel = validar.Relatorio()
    validar.validar_orcamento(rel, [{**linhas[0], "empenhado_orcdesp": "60"}], mensal=mensal)
    assert any("arquivo anual" in a for a in rel.avisos)


# ------------------------------------------------------------------ fase 3

from etl import servidores
from etl.publicar import do_governo_atual, meses_entre


def test_funcao_e_titulo_siape():
    assert servidores.funcao_de({"cargo": "Sem informaç", "sigla": "CCX", "nivel": "0117"}) == ("CCE 1.17", 17)
    assert servidores.funcao_de({"cargo": "Sem informaç", "sigla": "FEX", "nivel": "0115"}) == ("FCE 1.15", 15)
    assert servidores.funcao_de({"cargo": "MINISTRO DE ESTADO", "sigla": "-1", "nivel": "-1"}) == ("MEST", 99)
    assert servidores.titulo("SECRETARIO(A) EXECUTIVO(A) DA PASTA") == "Secretario(a) Executivo(a) da Pasta"
    assert servidores.eh_dirigente({"DESCRICAO_CARGO": "X", "SITUACAO_VINCULO": "ATIVO", "SIGLA_FUNCAO": "CCX", "NIVEL_FUNCAO": "0113"})
    assert not servidores.eh_dirigente({"DESCRICAO_CARGO": "X", "SITUACAO_VINCULO": "ATIVO", "SIGLA_FUNCAO": "CCX", "NIVEL_FUNCAO": "0110"})
    assert not servidores.eh_dirigente({"DESCRICAO_CARGO": "X", "SITUACAO_VINCULO": "ATIVO", "SIGLA_FUNCAO": "CCX", "NIVEL_FUNCAO": "0213"})


def test_pessoa_id_estavel_e_sem_cpf():
    a = servidores.pessoa_id("José da Silva", "123456")
    assert a == servidores.pessoa_id("JOSE DA SILVA", "123456") and "123456" not in a


def test_governo_anterior_e_duracao():
    assert not do_governo_atual({"inicio": "2022-03-31", "fim_aprox": "2023-02"})
    assert do_governo_atual({"inicio": "2019-05-01", "fim_aprox": ""})      # servidor de carreira que segue no cargo
    assert do_governo_atual({"inicio": "2023-01-01", "fim_aprox": "2024-05"})
    assert meses_entre("2023-01-01", "2024-05", "2026-08") == 16
    assert meses_entre("2026-04-02", None, "2026-08") == 4


def test_uorg_abreviada_bate_com_siorg():
    c = servidores.chave
    assert servidores.bate_abreviado(c("COORD-GERAL DE GEST DE INFORM FUNCIONAIS"), c("Coordenação-Geral de Gestão de Informações Funcionais"))
    assert servidores.bate_abreviado(c("SUBSECRETARIA DE PLANEJAMENTO, ORCAMENTO"), c("Subsecretaria de Planejamento, Orçamento e Administração"))
    assert not servidores.bate_abreviado(c("SECRETARIA EXECUTIVA"), c("Secretaria Executiva Adjunta"))
    assert not servidores.bate_abreviado(c("DEPARTAMENTO DE OBRAS"), c("Departamento de Projetos"))
    assert servidores.bate_abreviado(c("MIN DO EMPRE MICRO EMP DE PEQUENO PORTE"),
                                     c("Ministério do Empreendedorismo, da Microempresa e da Empresa de Pequeno Porte"))
    assert not servidores.bate_abreviado(c("MIN DESENVOLV IND COMERCIO E SERVICOS"),
                                         c("Ministério do Empreendedorismo, da Microempresa e da Empresa de Pequeno Porte"))


def test_mandatos_tolera_falha_e_descarta_residuo():
    meses = ["202301", "202302", "202303", "202304", "202305", "202306", "202307", "202308", "202309", "202310"]
    linha = lambda inicio: {"inicio": inicio, "atividade": "SECRETARIO(A)", "cargo": "", "cod_uorg": "1", "uorg": "U",
                            "_mid": "mx", "_funcao": "CCE 1.17", "_nivel": 17}
    pessoas = {"p1": {"nome": "Fulana"}, "p2": {"nome": "Beltrano"}}
    presenca = {
        ("p1", "CCE 1.17", "1"): {0: linha("2023-01-02"), 1: linha("2023-01-02"), 3: linha("2023-01-02"), 4: linha("2023-01-02")},
        ("p2", "CCE 1.17", "1"): {8: linha("2022-03-31")},            # reaparece 1 mês com ingresso antigo: resíduo
    }
    r = servidores.mandatos(presenca, meses, pessoas)
    assert len(r) == 1
    assert (r[0]["primeiro_mes"], r[0]["ultimo_mes"], r[0]["fim_aprox"]) == ("202301", "202305", "2023-06")


def test_posse_do_sucessor_encerra_antecessor():
    o = [{"funcao": "MEST", "ministerio_id": "mx", "inicio": "2023-01-01", "primeiro_mes": "202301", "fim_aprox": "2024-04"},
         {"funcao": "MEST", "ministerio_id": "mx", "inicio": "2023-10-01", "primeiro_mes": "202310", "fim_aprox": ""},
         {"funcao": "CCE 1.17", "ministerio_id": "mx", "inicio": "2023-01-01", "primeiro_mes": "202301", "fim_aprox": ""}]
    servidores.encerrar_antecessores(o)
    assert o[0]["fim_aprox"] == "2023-10" and o[1]["fim_aprox"] == "" and o[2]["fim_aprox"] == ""
