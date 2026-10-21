"""O guia da API (docs/api.md) é gerado do código e precisa estar em dia com ele."""
from app.scripts.gerar_doc_api import DESTINO, gerar, quem_pode, rotas_da_api


def test_guia_da_api_esta_em_dia_com_o_codigo():
    atual = DESTINO.read_text(encoding="utf-8").replace("\r\n", "\n")
    assert atual == gerar(), "docs/api.md desatualizado: rode `python -m app.scripts.gerar_doc_api` na pasta api/"


def test_toda_rota_tem_descricao_e_esta_no_guia():
    guia = DESTINO.read_text(encoding="utf-8")
    rotas = rotas_da_api()
    assert len(rotas) == 77
    for rota in rotas:
        assert rota.endpoint.__doc__, f"{rota.path}: escreva a docstring (vira a descrição no Swagger e no guia)"
        for metodo in rota.methods:
            assert f"### `{metodo} {rota.path}`" in guia


def test_quem_pode_sai_das_dependencias_de_permissao():
    rotas = {(m, r.path): r for r in rotas_da_api() for m in r.methods}
    assert quem_pode(rotas[("POST", "/doacoes")]) == "tutor, apoiador"
    assert quem_pode(rotas[("POST", "/necessidades")]) == "abrigo"
    assert quem_pode(rotas[("GET", "/admin/nucleo")]) == "admin"  # permissão no roteador, não na função
    assert quem_pode(rotas[("GET", "/perdidos/{perdido_id}")]) == "público (logado vê mais)"
    assert quem_pode(rotas[("GET", "/necessidades")]) == "público"
    assert quem_pode(rotas[("POST", "/usuarios/eu/senha")]) == "qualquer conta logada"
