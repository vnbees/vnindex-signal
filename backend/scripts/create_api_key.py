"""Tạo API key mới và lưu hash vào DB."""
import argparse
import asyncio
import secrets
import bcrypt
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import settings
from models.signal import ApiKey, Base


async def create_key(label: str):
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    raw_key = "sk-vnindex-" + secrets.token_hex(20)
    key_hash = bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt(rounds=12)).decode()

    async with async_session() as session:
        api_key = ApiKey(key_hash=key_hash, label=label, is_active=True)
        session.add(api_key)
        await session.commit()
        await session.refresh(api_key)

    print(f"\nAPI Key (lưu lại, chỉ hiển thị 1 lần):\n{raw_key}\n")
    print(f"Key ID: {api_key.id} | Label: {label} | Created: {api_key.created_at.date()}")
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default="default")
    args = parser.parse_args()
    asyncio.run(create_key(args.label))
