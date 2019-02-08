"""empty message

Revision ID: f73ba50d1ded
Revises: 1963d6605d44
Create Date: 2019-02-06 10:38:22.923970

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f73ba50d1ded'
down_revision = '1963d6605d44'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('evidencija', sa.Column('vrsta_unosa', sa.String(length=64), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('evidencija', 'vrsta_unosa')
    # ### end Alembic commands ###