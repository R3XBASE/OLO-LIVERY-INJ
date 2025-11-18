import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils.database import get_user, Database
from utils.livery_service import LiveryService

logger = logging.getLogger(__name__)

class AccountHandlers:
    def __init__(self):
        self.livery_service = LiveryService()
    
    async def show_account_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = await get_user(update.effective_user.id)
        
        text = "🔐 **Account Management**\n\n"
        
        if user.get('auth_token'):
            text += "✅ **Account Linked:** Yes\n"
            if user.get('playfab_id'):
                text += f"🆔 **PlayFab ID:** {user['playfab_id']}\n"
        else:
            text += "❌ **Account Linked:** No\n\n"
            text += "Anda perlu menghubungkan akun Offroad League terlebih dahulu untuk menggunakan layanan injeksi livery."
        
        keyboard = [
            [InlineKeyboardButton("🔗 Link Account", callback_data="link_account")],
            [InlineKeyboardButton("🔄 Update Token", callback_data="update_token")],
            [InlineKeyboardButton("🗑️ Remove Account", callback_data="remove_account")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def start_link_account(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        text = """
🔗 **Link Offroad League Account**

Untuk menghubungkan akun Offroad League, ikuti langkah berikut:

1. **Dapatkan Auth Token:**
   - Buka game Offroad League
   - Gunakan tool seperti HTTP Canary untuk intercept traffic
   - Cari request ke `playfabapi.com`
   - Copy nilai `X-Authorization` header

2. **Kirim Token:**
   - Klik tombol "Send Token" di bawah
   - Kirim token Anda dalam format:
     `/set_token YOUR_AUTH_TOKEN_HERE`

⚠️ **Keamanan:**
- Token hanya disimpan di database aman
- Hanya digunakan untuk injeksi livery
- Dapat dihapus kapan saja

🔒 **Privasi terjamin!**
        """
        
        keyboard = [
            [InlineKeyboardButton("📤 Send Token", callback_data="send_token_instruction")],
            [InlineKeyboardButton("🔙 Back", callback_data="account_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def handle_set_token(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        args = context.args
        
        if not args or len(args) == 0:
            await update.message.reply_text(
                "❌ **Usage:** `/set_token YOUR_AUTH_TOKEN`\n\nContoh: `/set_token ABC123XYZ...`",
                parse_mode='Markdown'
            )
            return
        
        auth_token = args[0]
        
        await update.message.reply_text("🔄 **Validating token...**")
        
        is_valid, playfab_id = await self.livery_service.validate_account(auth_token)
        
        if not is_valid:
            await update.message.reply_text(
                "❌ **Token tidak valid!**\n\nPastikan token benar dan akun Offroad League aktif.",
                parse_mode='Markdown'
            )
            return
        
        pool = await Database.get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET auth_token = $1, playfab_id = $2 WHERE telegram_id = $3",
                auth_token, playfab_id, user_id
            )
        
        success_text = f"""
✅ **Account Berhasil Dihubungkan!**

🆔 **PlayFab ID:** `{playfab_id}`
🔐 **Status:** Linked and Valid

Sekarang Anda dapat menggunakan layanan injeksi livery!
        """
        
        keyboard = [
            [InlineKeyboardButton("🎨 Inject Livery", callback_data="livery_menu")],
            [InlineKeyboardButton("💎 Check Credit", callback_data="check_credit")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(success_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def remove_account(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        user_id = query.from_user.id
        
        pool = await Database.get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET auth_token = NULL, playfab_id = NULL WHERE telegram_id = $1",
                user_id
            )
        
        await query.answer("✅ Account unlinked successfully!", show_alert=True)
        await self.show_account_menu(update, context)
    
    async def handle_account_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        callback_data = query.data
        
        if callback_data == "account_menu":
            await self.show_account_menu(update, context)
        elif callback_data == "link_account":
            await self.start_link_account(update, context)
        elif callback_data == "send_token_instruction":
            await query.edit_message_text(
                "📤 **Kirim Token Anda**\n\nGunakan command:\n`/set_token YOUR_AUTH_TOKEN_HERE`\n\nContoh: `/set_token ABC123XYZ...`",
                parse_mode='Markdown'
            )
        elif callback_data == "update_token":
            await self.start_link_account(update, context)
        elif callback_data == "remove_account":
            await self.remove_account(update, context)