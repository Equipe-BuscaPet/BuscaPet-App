"""Gera docs/api.md, o guia das rotas da API, a partir da própria aplicação.

Uso, a partir da pasta api/:
    python -m app.scripts.gerar_doc_api            # reescreve ../docs/api.md
    python -m app.scripts.gerar_doc_api --conferir # só confere se o arquivo está em dia (sai com 1 se não estiver)

Tudo vem do código, para o guia nunca ficar velho: rotas, parâmetros, corpo e resposta saem do OpenAPI do
FastAPI; quem pode usar cada rota sai das dependências de permissão (`exigir_tipo`, `get_usuario_atual`...);
os erros possíveis saem dos `HTTPException` da função. O teste tests/test_doc_api.py falha se alguém mudar
uma rota e esquecer de gerar o guia de novo.
"""
import inspect
import re
import sys
from pathlib import Path

from fastapi import routing
from fastapi.routing import APIRoute

from app.core import deps
from app.main import app

DESTINO = Path(__file__).resolve().parents[3] / "docs" / "api.md"

# Ordem dos módulos no guia (as tags do FastAPI) e uma frase sobre cada um.
MODULOS = {
    "autenticação": "Cadastro, login e recuperação de senha. O login devolve o token usado nas outras rotas.",
    "contas": "A própria conta: consultar, editar o perfil, trocar a senha e excluir.",
    "animais": "Animais para adoção (RF-13 a RF-18): catálogo com filtros, cadastro pelo abrigo e fotos.",
    "interesses": "Interesse de adoção (RF-16): o tutor demonstra, o abrigo conversa e decide.",
    "abrigos": "Abrigos no mapa e o perfil público, que junta animais, necessidades, meta do mês e apoiadores (RF-12).",
    "reencontro": "Animais perdidos e avistados (RF-19 a RF-28), busca por semelhança visual com o núcleo OpenCL e as fotos.",
    "doações": "Mural de necessidades, doações de itens e em dinheiro (PIX fora da plataforma) e confirmação pelo abrigo (RF-30 a RF-32).",
    "apoiadores": "Ranking de quem apoia e perfil público do apoiador (RF-33, RF-34).",
    "notificações": "O sino: avisos de cada conta (RF-36).",
    "denúncias": "Denúncia de anúncio e moderação pela administração (RF-41).",
    "administração": "Verificação de abrigos pela administração (RF-06).",
    "relatórios": "Painel da administração, relatórios do abrigo, exportação CSV e histórico de operações (RF-38 a RF-40).",
    "núcleo OpenCL": "Estado do núcleo, indexação das fotos e o benchmark sequencial × OpenCL (RF-29).",
    "infra": "Saúde do serviço.",
}

PERFIS = ("tutor", "abrigo", "apoiador", "admin")
ROTULO_STATUS = {
    200: "OK", 201: "criado", 204: "sem conteúdo", 400: "pedido inválido", 401: "não autenticado", 403: "sem permissão",
    404: "não encontrado", 409: "conflito com o estado atual", 422: "dados inválidos", 503: "serviço indisponível",
}


# ---------- rotas ----------

def rotas_da_api() -> list[APIRoute]:
    """As rotas como a API as atende: com o prefixo e as dependências do roteador já aplicados. A partir do FastAPI
    0.15x, os roteadores incluídos ficam embrulhados em `app.routes`; `iter_route_contexts` (o mesmo que o OpenAPI
    usa) os desembrulha. Nas versões antigas, `app.routes` já é a lista plana."""
    if hasattr(routing, "iter_route_contexts"):
        rotas = [c.route for c in routing.iter_route_contexts(app.routes)]
    else:
        rotas = list(app.routes)
    return [r for r in rotas if isinstance(r, APIRoute)]


# ---------- quem pode usar ----------

def _chamadas(dependente) -> list:
    saida = []
    for d in dependente.dependencies:
        saida.append(d.call)
        saida.extend(_chamadas(d))
    return saida


def quem_pode(rota: APIRoute) -> str:
    chamadas = _chamadas(rota.dependant)
    tipos = set()
    for c in chamadas:
        if getattr(c, "__name__", "") == "dependencia" and c.__closure__:
            for celula in c.__closure__:
                if isinstance(celula.cell_contents, tuple):
                    tipos |= {t.value for t in celula.cell_contents}
    if tipos:
        return ", ".join(p for p in PERFIS if p in tipos)
    if deps.get_usuario_atual in chamadas:
        return "qualquer conta logada"
    if deps.get_usuario_opcional in chamadas:
        return "público (logado vê mais)"
    return "público"


def erros(rota: APIRoute, perfil: str) -> list[int]:
    codigos = set()
    for funcao in [rota.endpoint] + [c for c in _chamadas(rota.dependant) if inspect.isfunction(c)]:
        try:
            fonte = inspect.getsource(funcao)
        except (OSError, TypeError):
            continue
        codigos |= {int(c) for c in re.findall(r"HTTP_(\d{3})_", fonte) if int(c) >= 400}
        codigos |= {int(c) for c in re.findall(r"HTTPException\((\d{3})", fonte)}
    if perfil != "público" and not perfil.startswith("público"):
        codigos |= {401}
        if perfil != "qualquer conta logada":
            codigos |= {403}
    if rota.body_field is not None or any(p for p in rota.dependant.query_params) or rota.dependant.path_params:
        codigos |= {422}
    return sorted(codigos)


# ---------- esquemas do OpenAPI ----------

def _ref(esquemas: dict, s: dict) -> tuple[str, dict]:
    nome = s["$ref"].split("/")[-1]
    return nome, esquemas[nome]


def _num(v) -> str:
    return str(int(v)) if isinstance(v, float) and v.is_integer() else str(v)


def _tem_secao(nome: str, alvo: dict) -> bool:
    """Os formatos com campos ganham seção própria no fim do guia (e link onde aparecem)."""
    return bool(alvo.get("properties")) and not nome.startswith(("Body_", "HTTPValidation", "Validation"))


def tipo(esquemas: dict, s: dict) -> str:
    if "$ref" in s:
        nome, alvo = _ref(esquemas, s)
        if "enum" in alvo:
            return " \\| ".join(f"`{v}`" for v in alvo["enum"])
        return f"[`{nome}`](#{nome.lower()})" if _tem_secao(nome, alvo) else f"`{nome}`"
    if "anyOf" in s:
        partes = [tipo(esquemas, x) for x in s["anyOf"] if x.get("type") != "null"]
        nulo = any(x.get("type") == "null" for x in s["anyOf"])
        return " ou ".join(partes) + (" (ou null)" if nulo else "")
    if "enum" in s:
        return " \\| ".join(f"`{v}`" for v in s["enum"])
    if "const" in s:
        return f"`{s['const']}`"
    t = s.get("type", "qualquer")
    if t == "array":
        return f"lista de {tipo(esquemas, s.get('items', {}))}"
    if s.get("format") == "binary" or "contentMediaType" in s:  # arquivo enviado (OpenAPI 3.0 e 3.1)
        return "arquivo"
    if s.get("format") in ("date-time", "date", "email"):
        return {"date-time": "data e hora (ISO 8601)", "date": "data (AAAA-MM-DD)", "email": "e-mail"}[s["format"]]
    return {"integer": "inteiro", "number": "número", "string": "texto", "boolean": "sim/não", "object": "objeto"}.get(t, t)


def regras(s: dict) -> str:
    for x in s.get("anyOf", []):
        if x.get("type") != "null":
            s = {**x, **{k: v for k, v in s.items() if k != "anyOf"}}
    partes = []
    for chave, texto in (("minLength", "mín. {} caracteres"), ("maxLength", "máx. {} caracteres"), ("minimum", "≥ {}"),
                         ("exclusiveMinimum", "> {}"), ("maximum", "≤ {}"), ("minItems", "mín. {} itens"), ("maxItems", "máx. {} itens")):
        if chave in s:
            partes.append(texto.format(_num(s[chave])))
    if "default" in s and s["default"] is not None:
        partes.append(f"padrão `{s['default']}`")
    if s.get("description"):
        partes.append(s["description"])
    return "; ".join(partes)


def tabela_campos(esquemas: dict, s: dict) -> list[str]:
    if "$ref" in s:
        _, s = _ref(esquemas, s)
    props = s.get("properties", {})
    if not props:
        return []
    obrig = set(s.get("required", []))
    linhas = ["| Campo | Tipo | Obrigatório | Regras |", "|---|---|---|---|"]
    for nome, p in props.items():
        linhas.append(f"| `{nome}` | {tipo(esquemas, p)} | {'sim' if nome in obrig else 'não'} | {regras(p)} |")
    return linhas


def corpo_de(op: dict) -> tuple[str, dict] | None:
    conteudo = op.get("requestBody", {}).get("content", {})
    for formato in ("application/json", "multipart/form-data", "application/x-www-form-urlencoded"):
        if formato in conteudo:
            return formato, conteudo[formato]["schema"]
    return None


def resposta_de(esquemas: dict, op: dict) -> tuple[str, str]:
    for codigo, r in op["responses"].items():
        if codigo.startswith("2"):
            schema = r.get("content", {}).get("application/json", {}).get("schema")
            if codigo == "204":
                return codigo, "sem corpo"
            if not schema or schema == {}:
                return codigo, "JSON (objeto) ou arquivo, conforme a rota"
            return codigo, tipo(esquemas, schema)
    return "200", "—"


# ---------- montagem ----------

def _titulo(modulo: str) -> str:
    return modulo[0].upper() + modulo[1:]


def _ancora(texto: str) -> str:
    return re.sub(r"[^\w\- ]", "", texto.lower()).strip().replace(" ", "-")


def gerar() -> str:
    openapi = app.openapi()
    esquemas = openapi["components"]["schemas"]
    rotas = [r for r in rotas_da_api() if r.include_in_schema]
    por_modulo: dict[str, list[tuple[str, APIRoute, dict]]] = {m: [] for m in MODULOS}
    for r in rotas:
        for metodo in sorted(r.methods):
            op = openapi["paths"][r.path][metodo.lower()]
            por_modulo.setdefault((r.tags or ["infra"])[0], []).append((metodo, r, op))
    total = sum(len(v) for v in por_modulo.values())

    s = [CABECALHO.format(total=total), "## Sumário", ""]
    for modulo, itens in por_modulo.items():
        if itens:
            s.append(f"- [{_titulo(modulo)}](#{_ancora(modulo)}) ({len(itens)})")
    s += ["", "---", ""]

    for modulo, itens in por_modulo.items():
        if not itens:
            continue
        s += [f"## {_titulo(modulo)}", "", MODULOS.get(modulo, ""), "",
              "| Método | Rota | Quem pode usar | O que faz |", "|---|---|---|---|"]
        for metodo, r, op in itens:
            resumo = (r.endpoint.__doc__ or op.get("summary", "")).strip().split("\n")[0].split(". ")[0].rstrip(".")
            s.append(f"| `{metodo}` | `{r.path}` | {quem_pode(r)} | {resumo} |")
        s.append("")
        for metodo, r, op in itens:
            perfil = quem_pode(r)
            s += [f"### `{metodo} {r.path}`", ""]
            descricao = inspect.cleandoc(r.endpoint.__doc__ or op.get("summary", ""))
            s += [descricao, "", f"- **Quem pode usar:** {perfil}"]
            params = op.get("parameters", [])
            if params:
                s += ["- **Parâmetros:**", ""]
                s += ["  | Nome | Onde | Tipo | Obrigatório | Regras |", "  |---|---|---|---|---|"]
                for p in params:
                    onde = {"path": "caminho", "query": "consulta (?)", "header": "cabeçalho"}.get(p["in"], p["in"])
                    s.append(f"  | `{p['name']}` | {onde} | {tipo(esquemas, p['schema'])} | {'sim' if p.get('required') else 'não'} | "
                             f"{regras({**p['schema'], 'description': p.get('description', '')})} |")
                s.append("")
            corpo = corpo_de(op)
            if corpo:
                formato, schema = corpo
                nome = tipo(esquemas, schema) if "$ref" in schema else "um de três formatos"
                rotulo = {"application/json": "JSON", "multipart/form-data": "formulário com arquivos (multipart)",
                          "application/x-www-form-urlencoded": "formulário (x-www-form-urlencoded)"}[formato]
                s += [f"- **Corpo ({rotulo}):** {nome}", ""]
                campos = tabela_campos(esquemas, schema)
                if campos:
                    s += ["  " + linha for linha in campos] + [""]
                elif "oneOf" in schema or "anyOf" in schema or "discriminator" in schema:
                    opcoes = [x["$ref"].split("/")[-1] for x in schema.get("oneOf", schema.get("anyOf", [])) if "$ref" in x]
                    s += [f"  Um destes formatos, escolhido pelo campo `tipo_conta`: {', '.join(f'`{o}`' for o in opcoes)}.", ""]
            codigo, resposta = resposta_de(esquemas, op)
            s.append(f"- **Resposta:** `{codigo}` ({ROTULO_STATUS.get(int(codigo), '')}) — {resposta}")
            lista_erros = erros(r, perfil)
            if lista_erros:
                s.append("- **Erros possíveis:** " + ", ".join(f"`{c}` {ROTULO_STATUS.get(c, '')}" for c in lista_erros))
            s += ["", ""]

    s += ESQUEMAS_TITULO.splitlines()
    usados = sorted(n for n, e in esquemas.items() if _tem_secao(n, e))
    for nome in usados:
        s += [f"### `{nome}`", ""]
        if esquemas[nome].get("description"):
            s += [inspect.cleandoc(esquemas[nome]["description"]), ""]
        s += tabela_campos(esquemas, esquemas[nome]) + [""]
    return "\n".join(s).rstrip() + "\n"


CABECALHO = """# BuscaPet — guia da API

> Gerado a partir do código por `python -m app.scripts.gerar_doc_api` (pasta `api/`). Não edite à mão: mude a rota
> (a descrição é a docstring da função) e gere de novo. O teste `tests/test_doc_api.py` acusa se ficar desatualizado.

A API do BuscaPet foi **desenvolvida pela equipe** (FastAPI, Python 3.12) e é a única API de dados que a interface
consome. São **{total} rotas**. Ela, por sua vez, chama o **núcleo OpenCL** (serviço próprio, em C) para comparar
fotos; o contrato do núcleo está em [`nucleo-opencl/README.md`](../nucleo-opencl/README.md).

## Como usar

- **Endereço:** `http://localhost:8000` no desenvolvimento.
- **Documentação interativa:** `/docs` (Swagger, dá para testar cada rota) e `/redoc`. O contrato bruto fica em
  `/openapi.json`.
- **Formato:** JSON em UTF-8. Datas e horas em ISO 8601 (UTC); datas "do dia" como `AAAA-MM-DD`. **Dinheiro em
  centavos** (`valor_centavos: 5000` = R$ 50,00), para não haver erro de arredondamento.
- **Erros:** sempre com `detail`. Nos erros de regra, `detail` é uma frase pronta para mostrar à pessoa
  (`{{"detail": "Esta necessidade já foi atendida."}}`); nos de validação (`422`), é a lista de campos com problema.

### Autenticação

1. `POST /auth/login` com **formulário** (`username` = e-mail, `password` = senha). A resposta traz `access_token`.
2. Nas rotas protegidas, envie o cabeçalho `Authorization: Bearer <access_token>`. O token vale **24 horas**.
3. No Swagger, o botão **Authorize** faz isso: use o e-mail e a senha de uma conta.

```bash
curl -X POST http://localhost:8000/auth/login -d "username=maria@exemplo.com" -d "password=Senha1234!"
# {{"access_token": "eyJhbGciOi...", "token_type": "bearer", "usuario": {{...}}}}
```

### Perfis e permissões

Login único; o tipo de conta é escolhido no cadastro. A coluna **Quem pode usar** de cada rota diz quem passa:

| Perfil | Quem é |
|---|---|
| público | qualquer pessoa, sem login |
| público (logado vê mais) | sem login funciona; logado, a resposta traz mais (ex.: o local exato do próprio registro) |
| qualquer conta logada | tutor, abrigo, apoiador ou admin |
| `tutor` | pessoa que adota, procura o animal perdido e doa como pessoa física |
| `abrigo` | abrigo ou protetor; publicar necessidades e receber doações exige o selo **Verificado** |
| `apoiador` | empresa (petshop, clínica, distribuidora) que doa e aparece no ranking da categoria |
| `admin` | administração do sistema (não há cadastro público de admin) |

Sem login numa rota protegida: `401`. Com login, mas perfil sem acesso: `403`.

### Códigos de resposta

| Código | Quando |
|---|---|
| `200` / `201` / `204` | deu certo (consulta / criado / sem corpo) |
| `400` | pedido inválido (ex.: senha atual errada, link de senha vencido) |
| `401` | sem login ou token vencido |
| `403` | o perfil não pode fazer isso (ou falta o selo Verificado) |
| `404` | não existe, ou não é seu |
| `409` | conflito com o estado atual (ex.: doação já respondida, e-mail já cadastrado) |
| `422` | dados inválidos (campo faltando, formato errado, regra de negócio dos dados) |
| `503` | o núcleo OpenCL não respondeu |

### Exemplos

```bash
API=http://localhost:8000
TOKEN=$(curl -s -X POST $API/auth/login -d "username=maria@exemplo.com" -d "password=Senha1234!" | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# Catálogo: gatos pequenos disponíveis
curl "$API/animais?especie=gato&porte=pequeno"

# Interesse de adoção (tutor)
curl -X POST "$API/animais/1/interesses" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \\
     -d '{{"mensagem": "Moro em casa com quintal."}}'

# Doação em dinheiro: depois do PIX para a chave do abrigo, informar o valor (R$ 50,00)
curl -X POST "$API/doacoes" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \\
     -d '{{"abrigo_id": 2, "valor_centavos": 5000}}'

# Busca por semelhança a partir de um animal perdido
curl "$API/reencontro/semelhantes?origem=perdido&id=1&raio_km=20" -H "Authorization: Bearer $TOKEN"
```
"""

ESQUEMAS_TITULO = """---

## Formatos de dados

Os objetos que aparecem nos corpos e nas respostas acima."""


if __name__ == "__main__":
    texto = gerar()
    if "--conferir" in sys.argv:
        atual = DESTINO.read_text(encoding="utf-8").replace("\r\n", "\n") if DESTINO.exists() else ""
        if atual != texto:
            sys.exit(f"{DESTINO} está desatualizado: rode python -m app.scripts.gerar_doc_api")
        print("docs/api.md em dia.")
    else:
        DESTINO.write_text(texto, encoding="utf-8", newline="\n")
        print(f"Gerado {DESTINO} ({texto.count(chr(10))} linhas).")
