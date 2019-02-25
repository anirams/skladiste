"""empty message

Revision ID: 10ce542594f8
Revises: be48444048e5
Create Date: 2019-02-13 16:02:41.584870

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '10ce542594f8'
down_revision = 'be48444048e5'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('proizvod', sa.Column('opis_proizvoda', sa.String(length=300), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('proizvod', 'opis_proizvoda')
    # ### end Alembic commands ###