from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from app.models import Transaction
from app.schemas import TransactionCreate, TransactionUpdate

async def create_transaction(db: AsyncSession, transaction_data: TransactionCreate, user_id: str) -> Transaction:
    db_transaction = Transaction(
        user_id=user_id,
        **transaction_data.dict()
    )
    db.add(db_transaction)
    await db.commit()
    await db.refresh(db_transaction)
    return db_transaction

async def get_transactions_by_user(
    db: AsyncSession, 
    user_id: str, 
    skip: int = 0, 
    limit: int = 100
) -> List[Transaction]:
    query = select(Transaction).where(Transaction.user_id == user_id).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

async def get_transaction_by_id(db: AsyncSession, transaction_id: int, user_id: str) -> Optional[Transaction]:
    query = select(Transaction).where(
        Transaction.id == transaction_id,
        Transaction.user_id == user_id
    )
    result = await db.execute(query)
    return result.scalars().first()

async def update_transaction(
    db: AsyncSession, 
    transaction_id: int, 
    transaction_data: TransactionUpdate, 
    user_id: str
) -> Optional[Transaction]:
    # First check if transaction exists and belongs to user
    transaction = await get_transaction_by_id(db, transaction_id, user_id)
    if not transaction:
        return None
    
    # Update only provided fields
    update_data = transaction_data.dict(exclude_unset=True)
    query = update(Transaction).where(
        Transaction.id == transaction_id,
        Transaction.user_id == user_id
    ).values(**update_data)
    
    await db.execute(query)
    await db.commit()
    
    # Return updated transaction
    return await get_transaction_by_id(db, transaction_id, user_id)

async def delete_transaction(db: AsyncSession, transaction_id: int, user_id: str) -> bool:
    # First check if transaction exists and belongs to user
    transaction = await get_transaction_by_id(db, transaction_id, user_id)
    if not transaction:
        return False
    
    query = delete(Transaction).where(
        Transaction.id == transaction_id,
        Transaction.user_id == user_id
    )
    
    await db.execute(query)
    await db.commit()
    return True