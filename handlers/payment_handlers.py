import uuid
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils.database import get_user, create_transaction, get_active_products, update_user_credit, Database
from utils.payment_utils import generate_tx_id, get_qris_image

logger = logging.getLogger(__name__)

class PaymentHandlers:
    async def show_topup_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        products = await get_active_products()
        
        text = "💰 **Top-up Credit**\n\nPilih paket credit yang diinginkan:"
        
        keyboard = []
        for product in products:
            keyboard.append([
                InlineKeyboardButton(
                    f"{product['name']} - Rp {product['price']:,.0f}",
                    callback_data=f"topup_{product['id']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🏠 Menu Utama", callback_data="main_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def handle_topup_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        product_id = int(query.data.replace('topup_', ''))
        
        products = await get_active_products()
        selected_product = next((p for p in products if p['id'] == product_id), None)
        
        if not selected_product:
            await query.edit_message_text("❌ Produk tidak ditemukan!")
            return
        
        user = await get_user(query.from_user.id)
        tx_id = generate_tx_id()
        
        context.user_data['pending_transaction'] = {
            'product_id': product_id,
            'tx_id': tx_id,
            'amount': float(selected_product['price']),
            'credit_amount': selected_product['credit_amount']
        }
        
        text = f"""
💳 **Konfirmasi Top-up**

📦 **Paket:** {selected_product['name']}
💎 **Credit:** {selected_product['credit_amount']}
💰 **Harga:** Rp {selected_product['price']:,.0f}
🆔 **TX ID:** `{tx_id}`

**Instruksi Pembayaran:**
1. Scan QRIS di bawah ini
2. Transfer tepat **Rp {selected_product['price']:,.0f}**
3. Klik tombol **"Saya Sudah Bayar"**
4. Kirim screenshot bukti transfer

⚠️ **Pastikan TX ID sesuai:** `{tx_id}`
        """
        
        qris_image_path = get_qris_image(selected_product['price'])
        
        keyboard = [
            [InlineKeyboardButton("✅ Saya Sudah Bayar", callback_data="confirm_payment_proof")],
            [InlineKeyboardButton("🔙 Kembali", callback_data="topup_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if qris_image_path:
            with open(qris_image_path, 'rb') as photo:
                await query.message.reply_photo(
                    photo=photo,
                    caption=text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
        else:
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def handle_confirm_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        context.user_data['awaiting_payment_proof'] = True
        
        text = f"""
📸 **Kirim Bukti Transfer**

Silakan kirim screenshot bukti transfer Anda.

Pastikan bukti transfer menunjukkan:
• Nominal yang sesuai
• Waktu transfer
• Status berhasil

⚠️ **TX ID:** `{context.user_data['pending_transaction']['tx_id']}`
        """
        
        keyboard = [
            [InlineKeyboardButton("🔙 Batalkan", callback_data="topup_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def handle_payment_proof(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.user_data.get('awaiting_payment_proof'):
            return
        
        user = await get_user(update.effective_user.id)
        transaction_data = context.user_data.get('pending_transaction')
        
        if not transaction_data:
            await update.message.reply_text("❌ Data transaksi tidak ditemukan!")
            return
        
        photo = update.message.photo[-1]
        photo_file = await photo.get_file()
        
        transaction = await create_transaction(
            user_id=user['id'],
            product_id=transaction_data['product_id'],
            tx_id=transaction_data['tx_id'],
            amount=transaction_data['amount']
        )
        
        await self.notify_admin(update, context, transaction, photo_file)
        
        context.user_data['awaiting_payment_proof'] = False
        context.user_data['pending_transaction'] = None
        
        text = f"""
✅ **Bukti Transfer Diterima**

Terima kasih! Bukti transfer Anda telah kami terima.

📦 **TX ID:** `{transaction_data['tx_id']}`
⏰ **Status:** Menunggu verifikasi admin

Admin akan memverifikasi pembayaran Anda dalam 1-15 menit. Anda akan mendapat notifikasi ketika credit sudah ditambahkan.
        """
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def notify_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE, transaction, photo_file):
        from utils.database import get_active_products
        from handlers.admin_handlers import AdminHandlers
        
        products = await get_active_products()
        product = next((p for p in products if p['id'] == transaction['product_id']), None)
        
        if not product:
            return
        
        user = update.effective_user
        
        text = f"""
🆕 **Pembayaran Baru**

👤 **User:** {user.full_name} (@{user.username})
🆔 **User ID:** {user.id}
📦 **Paket:** {product['name']}
💎 **Credit:** {product['credit_amount']}
💰 **Amount:** Rp {transaction['amount']:,.0f}
🆔 **TX ID:** `{transaction['tx_id']}`
        """
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"admin_approve_{transaction['id']}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"admin_reject_{transaction['id']}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        admin_ids = [6027790623]
        
        for admin_id in admin_ids:
            try:
                await context.bot.send_photo(
                    chat_id=admin_id,
                    photo=photo_file.file_id,
                    caption=text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id}: {e}")