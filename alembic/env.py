import os
from logging.config import fileConfig
from dotenv import load_dotenv

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# 1. Cargar variables de entorno del archivo .env
load_dotenv()

# 2. Importar la Base de datos y TODOS los módulos de modelos
from app.core.database import Base
import app.models.catalogs
import app.models.users
import app.models.potholes

# Objeto de configuración de Alembic
config = context.config

# 3. Inyectar la URL de conexión desde el .env (sobrescribe lo que diga alembic.ini)
config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL"))

# Configuración de logs de Python
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 4. Asignar los metadatos de nuestros modelos para que Alembic los compare
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section, {})
    
    # Inyectar la URL de la base de datos desde las variables de entorno
    import os
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        configuration["sqlalchemy.url"] = db_url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
