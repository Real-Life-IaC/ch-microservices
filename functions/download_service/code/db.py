from code.environment import DB_SECRET_NAME, SERVICE_NAME
from collections.abc import AsyncGenerator

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.parameters import GetParameterError, get_secret
from sqlalchemy.engine.url import URL
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


tracer = Tracer(service=SERVICE_NAME)
logger = Logger(service=SERVICE_NAME)

try:
    secret_data = get_secret(name=DB_SECRET_NAME, transform="json")
    db_secret = {
        "drivername": "postgresql+asyncpg",
        "database": secret_data.get("dbname"),
        "username": secret_data.get("username"),
        "password": secret_data.get("password"),
        "host": secret_data.get("host"),
        "port": secret_data.get("port"),
    }
    logger.info("Successfully retrieved DB credentials from Secrets Manager")
except GetParameterError:
    logger.warning(
        "Failed to retrieve from Secrets Manager. Using local db.",
        secret_name=DB_SECRET_NAME,
    )
    db_secret = {
        "drivername": "postgresql+asyncpg",
        "database": "postgres",
        "username": "postgres",
        "password": "postgres",
        "host": "postgres-db",  # Must match the service name in docker-compose.yml
        "port": 5432,
    }


engine = create_async_engine(
    url=URL.create(**db_secret),
    pool_size=5,
    max_overflow=20,
    pool_recycle=1800,
    pool_pre_ping=True,
    pool_use_lifo=True,
)


async def get_session() -> AsyncGenerator[AsyncSession]:
    """Yield a Session instance"""
    async_session = sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
