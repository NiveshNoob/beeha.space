"""Initial normalized Beeha catalog schema."""
from alembic import op
from backend.app.database import Base
from backend.app import models  # noqa: F401
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None
def upgrade():
    Base.metadata.create_all(bind=op.get_bind())
    from sqlalchemy import table, column, String
    languages = table("languages", column("code", String), column("name", String), column("native_name", String))
    op.bulk_insert(languages, [
        {"code":"ta", "name":"Tamil", "native_name":"தமிழ்"}, {"code":"en", "name":"English", "native_name":"English"},
        {"code":"hi", "name":"Hindi", "native_name":"हिन्दी"}, {"code":"te", "name":"Telugu", "native_name":"తెలుగు"},
        {"code":"ml", "name":"Malayalam", "native_name":"മലയാളം"}, {"code":"kn", "name":"Kannada", "native_name":"ಕನ್ನಡ"},
        {"code":"und", "name":"Unspecified", "native_name":"Unspecified"},
    ])
def downgrade():
    Base.metadata.drop_all(bind=op.get_bind())
