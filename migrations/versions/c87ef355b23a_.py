"""empty message

Revision ID: c87ef355b23a
Revises: 6a7c7cb8d1d1
Create Date: 2019-02-13 11:01:07.528392

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c87ef355b23a'
down_revision = '6a7c7cb8d1d1'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('evidencija', sa.Column('trenutna_kolicina', sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('evidencija', 'trenutna_kolicina')
    # ### end Alembic commands ###