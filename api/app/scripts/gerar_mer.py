"""Gera docs/mer.md, o Modelo Entidade-Relacionamento do banco, a partir dos modelos SQLAlchemy.

Uso, a partir da pasta api/:
    python -m app.scripts.gerar_mer

O diagrama é Mermaid (o GitHub desenha sozinho). Tabelas, colunas, chaves e relacionamentos saem de
`app/models/` (os mesmos que as migrações do Alembic usam), então o MER sempre mostra o banco que existe.
O teste tests/test_doc_banco.py falha se alguém mudar um modelo e esquecer de gerar de novo.
"""
import importlib
import pkgutil
import sys
from pathlib import Path

import sqlalchemy as sa

import app.models
from app.db.base import Base

DESTINO = Path(__file__).resolve().parents[3] / "docs" / "mer.md"

# Verbo de cada relacionamento, lido "TABELA_PAI verbo TABELA_FILHA". Chave: (tabela filha, coluna da FK).
VERBOS = {
    ("tutores", "usuario_id"): "é um",
    ("abrigos", "usuario_id"): "é um",
    ("apoiadores", "usuario_id"): "é um",
    ("abrigos", "validado_por_id"): "verifica",
    ("membros_equipe_abrigo", "abrigo_id"): "tem na equipe",
    ("membros_equipe_abrigo", "usuario_id"): "integra",
    ("animais", "abrigo_id"): "cadastra",
    ("interesses", "animal_id"): "recebe",
    ("interesses", "tutor_id"): "demonstra",
    ("animais_perdidos", "tutor_id"): "registra",
    ("avistamentos", "usuario_id"): "registra",
    ("buscas_salvas", "tutor_id"): "mantém",
    ("buscas_salvas", "animal_perdido_id"): "monitorado em",
    ("correspondencias", "animal_perdido_id"): "pode gerar",
    ("correspondencias", "animal_id"): "pode gerar",
    ("correspondencias", "avistamento_id"): "pode gerar",
    ("descritores_visuais", "foto_id"): "gera",
    ("necessidades", "abrigo_id"): "publica",
    ("doacoes", "apoiador_id"): "doa",
    ("doacoes", "abrigo_id"): "recebe",
    ("doacoes", "necessidade_id"): "atendida por",
    ("pontuacoes_apoiador", "apoiador_id"): "acumula",
    ("notificacoes", "usuario_id"): "recebe",
    ("logs_auditoria", "usuario_id"): "realiza",
    ("denuncias", "denunciante_id"): "denuncia",
    ("denuncias", "animal_id"): "pode ter",
    ("denuncias", "resolvido_por_id"): "modera",
}


def _carregar_modelos() -> None:
    for modulo in pkgutil.iter_modules(app.models.__path__):
        importlib.import_module(f"app.models.{modulo.name}")


def _tipo(coluna: sa.Column) -> str:
    t = coluna.type
    if isinstance(t, sa.Enum):
        return t.name or "enum"
    for classe, nome in ((sa.Boolean, "bool"), (sa.Integer, "int"), (sa.Float, "float"), (sa.DateTime, "datetime"),
                         (sa.Date, "date"), (sa.LargeBinary, "bytes"), (sa.Text, "text"), (sa.String, "string")):
        if isinstance(t, classe):
            return nome
    return type(t).__name__.lower()


def _unicas(tabela: sa.Table) -> set[str]:
    """Colunas únicas sozinhas (UNIQUE de uma coluna só)."""
    saida = {c.name for c in tabela.columns if c.unique}
    for restricao in tabela.constraints:
        if isinstance(restricao, sa.UniqueConstraint) and len(restricao.columns) == 1:
            saida |= {c.name for c in restricao.columns}
    return saida


MODULOS = {
    "Contas e adoção": {"usuarios", "tutores", "abrigos", "apoiadores", "membros_equipe_abrigo", "animais", "interesses", "denuncias"},
    "Reencontro": {"animais_perdidos", "avistamentos", "buscas_salvas", "correspondencias", "fotos", "fotos_arquivos", "descritores_visuais"},
    "Doações": {"necessidades", "doacoes", "pontuacoes_apoiador"},
    "Transversais": {"notificacoes", "logs_auditoria"},
}


def mermaid(so: set[str] | None = None) -> tuple[str, int, int]:
    """O bloco erDiagram. Com `so`, só aquele módulo: as tabelas dele com todas as colunas e, das tabelas a que ele
    se liga, só as chaves (o diagrama inteiro não cabe numa página do documento da Sprint)."""
    _carregar_modelos()
    todas = sorted(Base.metadata.tables.values(), key=lambda t: t.name)
    no_modulo = {t.name for t in todas} if so is None else so
    relacoes, vizinhas = [], set()
    for t in todas:
        if t.name not in no_modulo:
            continue
        unicas = _unicas(t)
        for c in t.columns:
            for fk in c.foreign_keys:
                pai = fk.column.table.name
                vizinhas.add(pai)
                filho_card = "o|" if c.primary_key or c.name in unicas else "o{"
                pai_card = "||" if not c.nullable else "|o"
                relacoes.append(f'    {pai.upper()} {pai_card}--{filho_card} {t.name.upper()} : "{VERBOS.get((t.name, c.name), "tem")}"')
    entidades = []
    for t in todas:
        if t.name not in no_modulo | vizinhas:
            continue
        completa, unicas, linhas = t.name in no_modulo, _unicas(t), []
        for c in t.columns:
            chaves = [k for k, sim in (("PK", c.primary_key), ("FK", bool(c.foreign_keys)), ("UK", c.name in unicas and not c.primary_key)) if sim]
            if completa or c.primary_key:
                nota = f' "-> {list(c.foreign_keys)[0].target_fullname}"' if c.foreign_keys else ""
                linhas.append(f"        {_tipo(c)} {c.name}{' ' + ', '.join(chaves) if chaves else ''}{nota}")
        entidades.append(f"    {t.name.upper()} {{\n" + "\n".join(linhas) + "\n    }")
    fks = sum(len(t.foreign_keys) for t in todas)
    return "erDiagram\n" + "\n".join(relacoes) + "\n\n" + "\n".join(entidades) + "\n", len(todas), fks


def gerar() -> str:
    codigo, tabelas, fks = mermaid()
    partes = [CABECALHO.format(tabelas=tabelas, fks=fks), "## Modelo completo\n\n```mermaid\n", codigo, "```\n"]
    partes.append("\n## Por módulo\n\nO mesmo modelo em partes menores, mais fáceis de ler. Tabelas de outro módulo "
                  "aparecem só com a chave primária.\n")
    for nome, tabelas_do_modulo in MODULOS.items():
        partes += [f"\n### {nome}\n\n```mermaid\n", mermaid(tabelas_do_modulo)[0], "```\n"]
    return "".join(partes) + RODAPE


CABECALHO = """# BuscaPet — Modelo Entidade-Relacionamento (MER)

> Gerado a partir dos modelos SQLAlchemy (`api/app/models/`) por `python -m app.scripts.gerar_mer` (pasta `api/`).
> Não edite à mão. Corresponde às migrações do Alembic até a última (`alembic upgrade head`) e ao
> [`schema.sql`](schema.sql).

**{tabelas} tabelas** e **{fks} chaves estrangeiras**. Nas linhas: `||` um e só um, `|o` zero ou um, `o{{` zero ou
muitos, `o|` zero ou um. PK = chave primária, FK = chave estrangeira (com a tabela de
destino), UK = valor único.

"""

RODAPE = """
## Como ler o modelo

| Módulo | Tabelas |
|---|---|
| Contas e perfis | `usuarios` (login de todos) e um perfil por tipo: `tutores`, `abrigos`, `apoiadores`; `membros_equipe_abrigo` |
| Adoção | `animais`, `interesses`, `denuncias` |
| Reencontro | `animais_perdidos`, `avistamentos`, `buscas_salvas`, `correspondencias`, `fotos`, `descritores_visuais` |
| Doações | `necessidades`, `doacoes`, `pontuacoes_apoiador` |
| Transversais | `notificacoes`, `logs_auditoria` |

**Decisões de modelagem**

- **Um perfil por tipo de conta** (`tutores`, `abrigos`, `apoiadores` com chave primária = `usuarios.id`): cada
  perfil tem as próprias colunas obrigatórias, sem uma tabela única cheia de colunas vazias.
- **`fotos` é polimórfica**: pertence a um animal, a um perdido ou a um avistamento, indicado por `entidade_tipo` +
  `entidade_id`. Por isso não aparece ligada por linha no diagrama: não existe chave estrangeira para "uma de três
  tabelas" em SQL; a integridade é garantida pela API. A extração de descritores (núcleo OpenCL) trata toda foto do
  mesmo jeito, venha de onde vier.
- **`doacoes.apoiador_id` aponta para `usuarios`**, não só para `apoiadores`: doa a empresa (apoiador) e também a
  pessoa física (tutor). Doação em dinheiro tem `valor_centavos` (PIX feito fora da plataforma); a meta do mês fica em
  `abrigos.meta_mensal_centavos`. Valores sempre em centavos, inteiros.
- **`pontuacoes_apoiador` é um cache mensal** do ranking (uma linha por pessoa e mês), recalculado quando o abrigo
  confirma uma doação; o ranking do ano é a soma dos meses.
- **Nada some de verdade quando há histórico:** conta excluída fica `ativo = false`; anúncio removido pela
  moderação ganha `removido_em`. Interesses, doações, denúncias e o histórico (`logs_auditoria`) continuam apontando
  para eles.
- **`descritores_visuais`** guarda o vetor que o núcleo OpenCL calcula para cada foto (uma linha por foto), usado na
  busca por semelhança e no monitoramento das `buscas_salvas`.
"""


if __name__ == "__main__":
    texto = gerar()
    if "--conferir" in sys.argv:
        atual = DESTINO.read_text(encoding="utf-8").replace("\r\n", "\n") if DESTINO.exists() else ""
        sys.exit(0 if atual == texto else f"{DESTINO} está desatualizado: rode python -m app.scripts.gerar_mer")
    DESTINO.write_text(texto, encoding="utf-8", newline="\n")
    print(f"Gerado {DESTINO}.")
