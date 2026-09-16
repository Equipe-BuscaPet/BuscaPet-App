"""schema inicial — Sprint 2

Cria todas as tabelas do modelo relacional (docs/schema.sql) a partir dos
models em app/models/. Não inclui dados nem índices de performance além dos
unique/PK necessários para a integridade — isso fica para quando houver
volume real para otimizar (Sprint 4, ajustes de índice citados no plano de
sprints).

Revision ID: 0001
Revises:
Create Date: 2026-09-16

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("nome", sa.String(150), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("senha_hash", sa.String(255), nullable=False),
        sa.Column("tipo_conta", sa.Enum("tutor", "abrigo", "apoiador", "admin", name="tipo_conta"), nullable=False),
        sa.Column("ativo", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "tutores",
        sa.Column("usuario_id", sa.Integer, sa.ForeignKey("usuarios.id"), primary_key=True),
        sa.Column("telefone", sa.String(20)),
        sa.Column("cidade", sa.String(120)),
    )

    op.create_table(
        "abrigos",
        sa.Column("usuario_id", sa.Integer, sa.ForeignKey("usuarios.id"), primary_key=True),
        sa.Column("nome_abrigo", sa.String(150), nullable=False),
        sa.Column("endereco", sa.String(255), nullable=False),
        sa.Column("latitude", sa.Float, nullable=False),
        sa.Column("longitude", sa.Float, nullable=False),
        sa.Column("horario_funcionamento", sa.String(255)),
        sa.Column("descricao", sa.String(2000)),
        sa.Column("telefone", sa.String(20)),
        sa.Column("chave_doacao_financeira", sa.String(140)),
        sa.Column("documento_comprobatorio_url", sa.String(500)),
        sa.Column(
            "status_validacao",
            sa.Enum("pendente", "aprovado", "rejeitado", name="status_validacao"),
            nullable=False,
            server_default="pendente",
        ),
        sa.Column("validado_por_id", sa.Integer, sa.ForeignKey("usuarios.id")),
        sa.Column("validado_em", sa.DateTime(timezone=True)),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "membros_equipe_abrigo",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("abrigo_id", sa.Integer, sa.ForeignKey("abrigos.usuario_id"), nullable=False),
        sa.Column("usuario_id", sa.Integer, sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("papel", sa.Enum("admin_abrigo", "operador", name="papel_equipe_abrigo"), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("abrigo_id", "usuario_id", name="uq_membro_por_abrigo"),
    )

    op.create_table(
        "apoiadores",
        sa.Column("usuario_id", sa.Integer, sa.ForeignKey("usuarios.id"), primary_key=True),
        sa.Column("cnpj", sa.String(18), nullable=False, unique=True),
        sa.Column(
            "tipo_estabelecimento",
            sa.Enum("petshop", "clinica", "distribuidora", "pessoa_fisica", name="tipo_estabelecimento"),
            nullable=False,
        ),
        sa.Column("endereco", sa.String(255), nullable=False),
        sa.Column("latitude", sa.Float),
        sa.Column("longitude", sa.Float),
        sa.Column(
            "status_validacao",
            sa.Enum("pendente", "aprovado", "rejeitado", name="status_validacao_apoiador"),
            nullable=False,
            server_default="aprovado",
        ),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "animais",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("abrigo_id", sa.Integer, sa.ForeignKey("abrigos.usuario_id"), nullable=False),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("especie", sa.Enum("cao", "gato", "outro", name="especie_animal"), nullable=False),
        sa.Column("raca_aproximada", sa.String(120)),
        sa.Column("porte", sa.String(20), nullable=False),
        sa.Column("idade_estimada_meses", sa.Integer),
        sa.Column("sexo", sa.Enum("macho", "femea", "indefinido", name="sexo_animal"), nullable=False),
        sa.Column("castrado", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("vacinado", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("vermifugado", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("temperamento", sa.String(500)),
        sa.Column("convivencia_criancas", sa.Boolean),
        sa.Column("convivencia_outros_animais", sa.Boolean),
        sa.Column("historia_resgate", sa.String(2000)),
        sa.Column("data_entrada", sa.DateTime(timezone=True)),
        sa.Column("condicao_chegada", sa.String(500)),
        sa.Column(
            "status",
            sa.Enum("disponivel", "em_processo", "adotado", "obito", "transferido", name="status_animal"),
            nullable=False,
            server_default="disponivel",
        ),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "fotos",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("entidade_tipo", sa.String(20), nullable=False),
        sa.Column("entidade_id", sa.Integer, nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("ordem", sa.Integer, nullable=False, server_default="0"),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_fotos_entidade", "fotos", ["entidade_tipo", "entidade_id"])

    op.create_table(
        "interesses",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("animal_id", sa.Integer, sa.ForeignKey("animais.id"), nullable=False),
        sa.Column("tutor_id", sa.Integer, sa.ForeignKey("tutores.usuario_id"), nullable=False),
        sa.Column(
            "status",
            sa.Enum("aguardando", "em_conversa", "aprovado", "recusado", name="status_interesse"),
            nullable=False,
            server_default="aguardando",
        ),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "animais_perdidos",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tutor_id", sa.Integer, sa.ForeignKey("tutores.usuario_id"), nullable=False),
        sa.Column("especie", sa.Enum("cao", "gato", "outro", name="especie_perdido"), nullable=False),
        sa.Column("porte", sa.String(20), nullable=False),
        sa.Column("cor_predominante", sa.String(60), nullable=False),
        sa.Column("pelagem", sa.String(60)),
        sa.Column("sexo", sa.Enum("macho", "femea", "indefinido", name="sexo_perdido"), nullable=False),
        sa.Column("sinais_particulares", sa.String(500)),
        sa.Column("latitude", sa.Float, nullable=False),
        sa.Column("longitude", sa.Float, nullable=False),
        sa.Column("raio_busca_km", sa.Float, nullable=False, server_default="5.0"),
        sa.Column("data_desaparecimento", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolvido", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "avistamentos",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("usuario_id", sa.Integer, sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("especie", sa.Enum("cao", "gato", "outro", name="especie_avistamento"), nullable=False),
        sa.Column("porte", sa.String(20), nullable=False),
        sa.Column("cor_predominante", sa.String(60), nullable=False),
        sa.Column("pelagem", sa.String(60)),
        sa.Column("sexo", sa.Enum("macho", "femea", "indefinido", name="sexo_avistamento"), nullable=False),
        sa.Column("sinais_particulares", sa.String(500)),
        sa.Column("latitude", sa.Float, nullable=False),
        sa.Column("longitude", sa.Float, nullable=False),
        sa.Column("data_avistamento", sa.DateTime(timezone=True), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "descritores_visuais",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("foto_id", sa.Integer, sa.ForeignKey("fotos.id"), nullable=False, unique=True),
        sa.Column("histograma_cor", sa.Text, nullable=False),
        sa.Column("textura", sa.Text, nullable=False),
        sa.Column("proporcoes", sa.Text, nullable=False),
        sa.Column("versao_algoritmo", sa.String(20), nullable=False, server_default="v1"),
        sa.Column("calculado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "buscas_salvas",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tutor_id", sa.Integer, sa.ForeignKey("tutores.usuario_id"), nullable=False),
        sa.Column("animal_perdido_id", sa.Integer, sa.ForeignKey("animais_perdidos.id"), nullable=False),
        sa.Column(
            "status", sa.Enum("monitorando", "resolvida", name="status_busca"), nullable=False, server_default="monitorando"
        ),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("resolvida_em", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "correspondencias",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "tipo",
            sa.Enum("busca_tutor", "alerta_abrigo", "busca_inversa", name="tipo_correspondencia"),
            nullable=False,
        ),
        sa.Column("animal_perdido_id", sa.Integer, sa.ForeignKey("animais_perdidos.id")),
        sa.Column("animal_id", sa.Integer, sa.ForeignKey("animais.id")),
        sa.Column("avistamento_id", sa.Integer, sa.ForeignKey("avistamentos.id")),
        sa.Column("score", sa.Float, nullable=False),
        sa.Column("grau_semelhanca", sa.Enum("alta", "media", "baixa", name="grau_semelhanca"), nullable=False),
        sa.Column("notificado", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "necessidades",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("abrigo_id", sa.Integer, sa.ForeignKey("abrigos.usuario_id"), nullable=False),
        sa.Column("item", sa.String(200), nullable=False),
        sa.Column("quantidade", sa.Integer, nullable=False),
        sa.Column("urgencia", sa.Enum("baixa", "media", "alta", name="urgencia_necessidade"), nullable=False),
        sa.Column(
            "status", sa.Enum("aberta", "atendida", name="status_necessidade"), nullable=False, server_default="aberta"
        ),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "doacoes",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("apoiador_id", sa.Integer, sa.ForeignKey("apoiadores.usuario_id"), nullable=False),
        sa.Column("abrigo_id", sa.Integer, sa.ForeignKey("abrigos.usuario_id"), nullable=False),
        sa.Column("necessidade_id", sa.Integer, sa.ForeignKey("necessidades.id")),
        sa.Column("item", sa.String(200), nullable=False),
        sa.Column("quantidade", sa.Integer, nullable=False),
        sa.Column(
            "status",
            sa.Enum("aguardando_confirmacao", "confirmada", "recusada", name="status_doacao"),
            nullable=False,
            server_default="aguardando_confirmacao",
        ),
        sa.Column("registrado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("confirmado_em", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "pontuacoes_apoiador",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("apoiador_id", sa.Integer, sa.ForeignKey("apoiadores.usuario_id"), nullable=False),
        sa.Column("mes_referencia", sa.DateTime(timezone=True), nullable=False),
        sa.Column("pontos_volume", sa.Float, nullable=False, server_default="0"),
        sa.Column("pontos_regularidade", sa.Float, nullable=False, server_default="0"),
        sa.Column("pontos_total", sa.Float, nullable=False, server_default="0"),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("apoiador_id", "mes_referencia", name="uq_pontuacao_apoiador_mes"),
    )

    op.create_table(
        "notificacoes",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("usuario_id", sa.Integer, sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("mensagem", sa.String(500), nullable=False),
        sa.Column("referencia_tipo", sa.String(30)),
        sa.Column("referencia_id", sa.Integer),
        sa.Column("lida", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "denuncias",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("denunciante_id", sa.Integer, sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("animal_id", sa.Integer, sa.ForeignKey("animais.id"), nullable=False),
        sa.Column("motivo", sa.String(1000), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pendente", "removido", "advertido", "banido", "ignorado", name="status_denuncia"),
            nullable=False,
            server_default="pendente",
        ),
        sa.Column("resolvido_por_id", sa.Integer, sa.ForeignKey("usuarios.id")),
        sa.Column("resolvido_em", sa.DateTime(timezone=True)),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "logs_auditoria",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("usuario_id", sa.Integer, sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("acao", sa.String(100), nullable=False),
        sa.Column("entidade_tipo", sa.String(50), nullable=False),
        sa.Column("entidade_id", sa.Integer, nullable=False),
        sa.Column("detalhes_json", sa.Text),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    for table in (
        "logs_auditoria",
        "denuncias",
        "notificacoes",
        "pontuacoes_apoiador",
        "doacoes",
        "necessidades",
        "correspondencias",
        "buscas_salvas",
        "descritores_visuais",
        "avistamentos",
        "animais_perdidos",
        "interesses",
        "fotos",
        "animais",
        "apoiadores",
        "membros_equipe_abrigo",
        "abrigos",
        "tutores",
        "usuarios",
    ):
        op.drop_table(table)
