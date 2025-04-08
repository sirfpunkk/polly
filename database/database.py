from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

class Database:
    def __init__(self, db_url: str):
        self.engine = create_async_engine(db_url)
        self.async_session = sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )

    async def init_db(self):
        async with self.engine.begin() as conn:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    id BIGINT PRIMARY KEY,
                    username TEXT,
                    registered_at TIMESTAMP DEFAULT NOW(),
                    ref_code TEXT,
                    ref_by BIGINT,
                    request_count INTEGER DEFAULT 0,
                    last_request TIMESTAMP,
                    balance INTEGER DEFAULT 0
                );
                
                -- Другие таблицы (объявления, фото, контакты, подписки и т.д.)
            """))