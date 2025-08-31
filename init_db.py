import asyncio
from app.database import engine, Base
from app.models import Transaction
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from datetime import datetime

async def init_db():
    """初始化数据库"""
    async with engine.begin() as conn:
        # 创建所有表
        await conn.run_sync(Base.metadata.create_all)
        print("数据库表创建成功")
        
        # 检查是否已有数据
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with async_session() as session:
            result = await session.execute(select(Transaction).limit(1))
            if not result.scalars().first():
                # 添加示例数据
                sample_transaction = Transaction(
                    user_id="demo_user",
                    amount=99.99,
                    vendor="示例商家",
                    category="餐饮",
                    transaction_date=datetime.now(),
                    description="这是一条示例交易记录"
                )
                session.add(sample_transaction)
                await session.commit()
                print("示例数据添加成功")
            else:
                print("数据库中已有数据，跳过添加示例数据")

if __name__ == "__main__":
    asyncio.run(init_db())