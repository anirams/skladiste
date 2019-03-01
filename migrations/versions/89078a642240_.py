"""empty message

Revision ID: 89078a642240
Revises: f73ba50d1ded
Create Date: 2019-02-06 11:59:18.236831

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '89078a642240'
down_revision = 'f73ba50d1ded'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('evidencija', sa.Column('promijenjena_kolicina', sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('evidencija', 'promijenjena_kolicina')
    # ### end Alembic commands ###