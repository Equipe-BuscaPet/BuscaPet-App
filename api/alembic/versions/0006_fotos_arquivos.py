"""Tabela fotos_arquivos: o JPEG da foto dentro do banco, para hospedagem sem disco permanente.

Só é usada com ARMAZENAMENTO_FOTOS=banco (o padrão continua sendo a pasta em disco).

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-28 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0006'
down_revision: Union[str, None] = '0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'fotos_arquivos',
        sa.Column('nome', sa.String(length=40), nullable=False),
        sa.Column('conteudo', sa.LargeBinary(), nullable=False),
        sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('nome', name=op.f('pk_fotos_arquivos')),
    )


def downgrade() -> None:
    op.drop_table('fotos_arquivos')
