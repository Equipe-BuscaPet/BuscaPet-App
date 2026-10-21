"""Doação de tutor (pessoa física) e meta mensal em dinheiro do abrigo (RF-31, RF-33).

- doacoes.apoiador_id e pontuacoes_apoiador.apoiador_id passam a apontar para usuarios (não só apoiadores):
  quem doa pode ser um apoiador (empresa) ou um tutor (pessoa física). Os ids não mudam, porque o id do
  apoiador já é o id do usuário.
- doacoes.valor_centavos: doação em dinheiro (PIX feito fora da plataforma); nulo = doação de itens.
- abrigos.meta_mensal_centavos e abrigos.meta_mensal_descricao: a meta de gastos do mês e para que serve.

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-21 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0005'
down_revision: Union[str, None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('fk_doacoes_apoiador_id_apoiadores', 'doacoes', type_='foreignkey')
    op.create_foreign_key('fk_doacoes_apoiador_id_usuarios', 'doacoes', 'usuarios', ['apoiador_id'], ['id'])
    op.drop_constraint('fk_pontuacoes_apoiador_apoiador_id_apoiadores', 'pontuacoes_apoiador', type_='foreignkey')
    op.create_foreign_key('fk_pontuacoes_apoiador_apoiador_id_usuarios', 'pontuacoes_apoiador', 'usuarios', ['apoiador_id'], ['id'])
    op.add_column('doacoes', sa.Column('valor_centavos', sa.Integer(), nullable=True))
    op.add_column('abrigos', sa.Column('meta_mensal_centavos', sa.Integer(), nullable=True))
    op.add_column('abrigos', sa.Column('meta_mensal_descricao', sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column('abrigos', 'meta_mensal_descricao')
    op.drop_column('abrigos', 'meta_mensal_centavos')
    op.drop_column('doacoes', 'valor_centavos')
    # Volta a exigir apoiador: só funciona se nenhum tutor tiver doado.
    op.drop_constraint('fk_pontuacoes_apoiador_apoiador_id_usuarios', 'pontuacoes_apoiador', type_='foreignkey')
    op.create_foreign_key('fk_pontuacoes_apoiador_apoiador_id_apoiadores', 'pontuacoes_apoiador', 'apoiadores', ['apoiador_id'], ['usuario_id'])
    op.drop_constraint('fk_doacoes_apoiador_id_usuarios', 'doacoes', type_='foreignkey')
    op.create_foreign_key('fk_doacoes_apoiador_id_apoiadores', 'doacoes', 'apoiadores', ['apoiador_id'], ['usuario_id'])
