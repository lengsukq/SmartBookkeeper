from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.database import get_db
from app.crud import get_transactions_by_user, update_transaction, delete_transaction, get_transaction_by_id, create_transaction
from app.schemas import TransactionInDB, TransactionUpdate, TransactionCreate
from app.security import get_current_user
from datetime import datetime

router = APIRouter()

@router.post("/api/v1/transactions/", response_model=TransactionInDB)
async def create_user_transaction(
    transaction: TransactionCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """创建新的交易记录"""
    try:
        # 创建交易
        new_transaction = await create_transaction(db, transaction, user_id)
        
        if not new_transaction:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create transaction"
            )
        
        return new_transaction
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create transaction: {str(e)}"
        )

@router.get("/api/v1/transactions/", response_model=List[TransactionInDB])
async def get_user_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """获取当前用户的记账列表"""
    try:
        transactions = await get_transactions_by_user(db, user_id, skip=skip, limit=limit)
        return transactions
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get transactions: {str(e)}"
        )

@router.put("/api/v1/transactions/{transaction_id}", response_model=TransactionInDB)
async def update_user_transaction(
    transaction_id: int,
    transaction_update: TransactionUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """修改记录"""
    try:
        # 检查交易是否存在且属于当前用户
        existing_transaction = await get_transaction_by_id(db, transaction_id, user_id)
        if not existing_transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction not found or access denied"
            )
        
        # 更新交易
        updated_transaction = await update_transaction(
            db, transaction_id, transaction_update, user_id
        )
        
        if not updated_transaction:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update transaction"
            )
        
        return updated_transaction
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update transaction: {str(e)}"
        )

@router.delete("/api/v1/transactions/{transaction_id}")
async def delete_user_transaction(
    transaction_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """删除记录"""
    try:
        # 检查交易是否存在且属于当前用户
        existing_transaction = await get_transaction_by_id(db, transaction_id, user_id)
        if not existing_transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction not found or access denied"
            )
        
        # 删除交易
        success = await delete_transaction(db, transaction_id, user_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to delete transaction"
            )
        
        return {"status": "success", "message": "Transaction deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete transaction: {str(e)}"
        )