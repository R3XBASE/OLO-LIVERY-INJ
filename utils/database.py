import asyncpg
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class Database:
    _pool = None
    
    @classmethod
    async def get_pool(cls):
        if cls._pool is None:
            cls._pool = await asyncpg.create_pool(os.getenv('DATABASE_URL'))
        return cls._pool
    
    @classmethod
    async def close_pool(cls):
        if cls._pool:
            await cls._pool.close()
            cls._pool = None

async def create_tables():
    pool = await Database.get_pool()
    
    with open('database/init.sql', 'r') as f:
        sql = f.read()
    
    async with pool.acquire() as conn:
        await conn.execute(sql)

async def get_user(telegram_id: int):
    pool = await Database.get_pool()
    
    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT * FROM users WHERE telegram_id = $1", telegram_id
        )
        
        if not user:
            user = await conn.fetchrow(
                """INSERT INTO users (telegram_id, username, full_name, credit) 
                VALUES ($1, $2, $3, $4) RETURNING *""",
                telegram_id, '', '', 0
            )
        
        return user

async def update_user_credit(telegram_id: int, credit_change: int):
    pool = await Database.get_pool()
    
    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            """UPDATE users SET credit = credit + $1, updated_at = $2 
            WHERE telegram_id = $3 RETURNING *""",
            credit_change, datetime.now(), telegram_id
        )
        return user

async def create_transaction(user_id: int, product_id: int, tx_id: str, amount: float):
    pool = await Database.get_pool()
    
    async with pool.acquire() as conn:
        transaction = await conn.fetchrow(
            """INSERT INTO transactions (user_id, product_id, tx_id, amount, status) 
            VALUES ($1, $2, $3, $4, 'pending') RETURNING *""",
            user_id, product_id, tx_id, amount
        )
        return transaction

async def get_active_products():
    pool = await Database.get_pool()
    
    async with pool.acquire() as conn:
        products = await conn.fetch(
            "SELECT * FROM products WHERE is_active = true ORDER BY price"
        )
        return products

async def is_admin(telegram_id: int):
    pool = await Database.get_pool()
    
    async with pool.acquire() as conn:
        admin = await conn.fetchrow(
            "SELECT * FROM admins WHERE telegram_id = $1 AND is_active = true",
            telegram_id
        )
        return admin is not None

async def get_pending_transactions():
    pool = await Database.get_pool()
    
    async with pool.acquire() as conn:
        transactions = await conn.fetch("""
            SELECT t.*, u.telegram_id, u.username, u.full_name, p.name as product_name, p.credit_amount
            FROM transactions t
            JOIN users u ON t.user_id = u.id
            JOIN products p ON t.product_id = p.id
            WHERE t.status = 'pending'
            ORDER BY t.created_at DESC
        """)
        return transactions

async def update_transaction_status(transaction_id: int, status: str, admin_notes: str = None):
    pool = await Database.get_pool()
    
    async with pool.acquire() as conn:
        await conn.execute(
            """UPDATE transactions SET status = $1, admin_notes = $2, updated_at = $3 
            WHERE id = $4""",
            status, admin_notes, datetime.now(), transaction_id
        )

async def get_user_by_id(user_id: int):
    pool = await Database.get_pool()
    
    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT * FROM users WHERE id = $1", user_id
        )
        return user

async def get_transaction_by_id(transaction_id: int):
    pool = await Database.get_pool()
    
    async with pool.acquire() as conn:
        transaction = await conn.fetchrow(
            "SELECT * FROM transactions WHERE id = $1", transaction_id
        )
        return transaction

async def get_system_stats():
    pool = await Database.get_pool()
    
    async with pool.acquire() as conn:
        total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
        total_transactions = await conn.fetchval("SELECT COUNT(*) FROM transactions")
        total_revenue = await conn.fetchval(
            "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE status = 'approved'"
        )
        pending_transactions = await conn.fetchval(
            "SELECT COUNT(*) FROM transactions WHERE status = 'pending'"
        )
        
        return {
            'total_users': total_users,
            'total_transactions': total_transactions,
            'total_revenue': total_revenue,
            'pending_transactions': pending_transactions
        }