import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils.database import is_admin, update_user_credit, get_active_products, Database
from utils.database import get_pending_transactions, update_transaction_status, get_user_by_id, get_system_stats

logger = logging.getLogger(__name__)

class AdminHandlers:
    async def admin_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        if not await is_admin(user_id):
            await update.message.reply_text("❌ Anda bukan admin!")
            return
        
        text = "👨‍💼 **Admin Panel**\n\nPilih opsi di bawah:"
        
        keyboard = [
            [InlineKeyboardButton("📊 Statistik", callback_data="admin_stats")],
            [InlineKeyboardButton("💰 Kelola Produk", callback_data="admin_products")],
            [InlineKeyboardButton("📋 Transaksi Pending", callback_data="admin_pending")],
            [InlineKeyboardButton("👥 Kelola User", callback_data="admin_users")],
            [InlineKeyboardButton("🏠 Menu Utama", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def handle_admin_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        callback_data = query.data
        
        if not await is_admin(query.from_user.id):
            await query.answer("❌ Anda bukan admin!", show_alert=True)
            return
        
        if callback_data == "admin_stats":
            await self.show_stats(query)
        elif callback_data == "admin_products":
            await self.manage_products(query)
        elif callback_data == "admin_pending":
            await self.show_pending_transactions(query)
        elif callback_data.startswith('admin_approve_'):
            transaction_id = int(callback_data.replace('admin_approve_', ''))
            await self.approve_transaction(query, transaction_id)
        elif callback_data.startswith('admin_reject_'):
            transaction_id = int(callback_data.replace('admin_reject_', ''))
            await self.reject_transaction(query, transaction_id)
    
    async def show_stats(self, query):
        stats = await get_system_stats()
        
        text = f"""
📊 **Statistik Sistem**

👥 **Total Users:** {stats['total_users']}
💳 **Total Transaksi:** {stats['total_transactions']}
⏳ **Pending Transactions:** {stats['pending_transactions']}
💰 **Total Revenue:** Rp {stats['total_revenue']:,.0f}
        """
        
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh", callback_data="admin_stats")],
            [InlineKeyboardButton("📋 Transaksi Pending", callback_data="admin_pending")],
            [InlineKeyboardButton("🔙 Kembali", callback_data="admin_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_pending_transactions(self, query):
        transactions = await get_pending_transactions()
        
        if not transactions:
            text = "✅ **Tidak ada transaksi pending**"
        else:
            text = "⏳ **Transaksi Pending**\n\n"
            for tx in transactions:
                text += f"""
🆔 **TX ID:** `{tx['tx_id']}`
👤 **User:** {tx['full_name']} (@{tx['username']})
📦 **Paket:** {tx['product_name']} ({tx['credit_amount']} credit)
💰 **Amount:** Rp {tx['amount']:,.0f}
🕒 **Waktu:** {tx['created_at'].strftime('%Y-%m-%d %H:%M')}

"""
        
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh", callback_data="admin_pending")],
            [InlineKeyboardButton("📊 Statistik", callback_data="admin_stats")],
            [InlineKeyboardButton("🔙 Kembali", callback_data="admin_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def approve_transaction(self, query, transaction_id: int):
        pool = await Database.get_pool()
        
        async with pool.acquire() as conn:
            transaction = await conn.fetchrow("""
                SELECT t.*, u.telegram_id, u.id as user_id, p.credit_amount
                FROM transactions t
                JOIN users u ON t.user_id = u.id
                JOIN products p ON t.product_id = p.id
                WHERE t.id = $1
            """, transaction_id)
            
            if not transaction:
                await query.answer("❌ Transaksi tidak ditemukan!", show_alert=True)
                return
            
            await conn.execute(
                "UPDATE transactions SET status = 'approved', updated_at = CURRENT_TIMESTAMP WHERE id = $1",
                transaction_id
            )
            
            await conn.execute(
                "UPDATE users SET credit = credit + $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2",
                transaction['credit_amount'], transaction['user_id']
            )
            
            user_credit = await conn.fetchval(
                "SELECT credit FROM users WHERE id = $1", transaction['user_id']
            )
        
        try:
            await query.bot.send_message(
                chat_id=transaction['telegram_id'],
                text=f"""
✅ **Pembayaran Diverifikasi!**

Credit telah berhasil ditambahkan ke akun Anda.

💎 **Credit ditambahkan:** {transaction['credit_amount']}
💎 **Total credit sekarang:** {user_credit}
🆔 **TX ID:** `{transaction['tx_id']}`

Terima kasih telah berbelanja! 🎉
                """,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to notify user: {e}")
        
        await query.answer("✅ Transaksi approved!", show_alert=True)
        await self.show_pending_transactions(query)
    
    async def reject_transaction(self, query, transaction_id: int):
        pool = await Database.get_pool()
        
        async with pool.acquire() as conn:
            transaction = await conn.fetchrow("""
                SELECT t.*, u.telegram_id
                FROM transactions t
                JOIN users u ON t.user_id = u.id
                WHERE t.id = $1
            """, transaction_id)
            
            if not transaction:
                await query.answer("❌ Transaksi tidak ditemukan!", show_alert=True)
                return
            
            await conn.execute(
                "UPDATE transactions SET status = 'rejected', updated_at = CURRENT_TIMESTAMP WHERE id = $1",
                transaction_id
            )
        
        try:
            await query.bot.send_message(
                chat_id=transaction['telegram_id'],
                text=f"""
❌ **Pembayaran Ditolak**

Maaf, pembayaran Anda untuk TX ID `{transaction['tx_id']}` telah ditolak.

**Alasan mungkin termasuk:**
• Nominal tidak sesuai
• Bukti transfer tidak valid
• Waktu transfer terlambat

Silakan hubungi admin untuk informasi lebih lanjut.
                """,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to notify user: {e}")
        
        await query.answer("❌ Transaksi rejected!", show_alert=True)
        await self.show_pending_transactions(query)
    
    async def manage_products(self, query):
        products = await get_active_products()
        
        text = "📦 **Kelola Produk**\n\n"
        
        for product in products:
            text += f"""
📦 **{product['name']}**
💎 Credit: {product['credit_amount']}
💰 Harga: Rp {product['price']:,.0f}
🆔 ID: {product['id']}

"""
        
        keyboard = [
            [InlineKeyboardButton("➕ Tambah Produk", callback_data="admin_add_product")],
            [InlineKeyboardButton("✏️ Edit Produk", callback_data="admin_edit_product")],
            [InlineKeyboardButton("🔙 Kembali", callback_data="admin_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')