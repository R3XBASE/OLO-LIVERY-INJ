import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils.database import get_user, update_user_credit, Database
from utils.livery_service import LiveryService

logger = logging.getLogger(__name__)

class UserHandlers:
    def __init__(self):
        self.livery_service = LiveryService()
    
    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        db_user = await get_user(user.id)
        
        welcome_text = f"""
🤖 **Livery Injection Bot**

Halo {user.full_name}! Selamat datang di Livery Injection Bot.

🔹 **Fitur:**
• Inject livery ke akun Offroad League
• Sistem kredit yang mudah
• Top-up cepat dan aman

💎 **Credit Anda:** {db_user['credit']}

Gunakan menu di bawah untuk mulai:
        """
        
        keyboard = [
            [InlineKeyboardButton("🎨 Inject Livery", callback_data="livery_menu")],
            [InlineKeyboardButton("💎 Cek Credit", callback_data="check_credit")],
            [InlineKeyboardButton("💰 Top-up Credit", callback_data="topup_menu")],
            [InlineKeyboardButton("🔗 Account Setup", callback_data="account_menu")],
            [InlineKeyboardButton("ℹ️ Bantuan", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        user = await get_user(query.from_user.id)
        
        text = f"""
🏠 **Menu Utama**

💎 **Credit Anda:** {user['credit']}
🔐 **Account:** {'✅ Linked' if user.get('auth_token') else '❌ Not Linked'}

Pilih opsi di bawah:
        """
        
        keyboard = [
            [InlineKeyboardButton("🎨 Inject Livery", callback_data="livery_menu")],
            [InlineKeyboardButton("💎 Cek Credit", callback_data="check_credit")],
            [InlineKeyboardButton("💰 Top-up Credit", callback_data="topup_menu")],
            [InlineKeyboardButton("🔗 Account Setup", callback_data="account_menu")],
            [InlineKeyboardButton("ℹ️ Bantuan", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_credit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = await get_user(update.effective_user.id)
        
        text = f"""
💎 **Credit Information**

**Credit saat ini:** {user['credit']}
**User ID:** {user['telegram_id']}

Setiap inject livery membutuhkan 1 credit.
        """
        
        keyboard = [
            [InlineKeyboardButton("💰 Top-up Credit", callback_data="topup_menu")],
            [InlineKeyboardButton("🎨 Inject Livery", callback_data="livery_menu")],
            [InlineKeyboardButton("🏠 Menu Utama", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_livery_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = await get_user(update.effective_user.id)
        
        if user['credit'] < 1:
            text = "❌ **Credit tidak cukup!**\n\nAnda membutuhkan minimal 1 credit untuk inject livery."
            keyboard = [
                [InlineKeyboardButton("💰 Top-up Credit", callback_data="topup_menu")],
                [InlineKeyboardButton("💎 Cek Credit", callback_data="check_credit")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if update.callback_query:
                await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
            else:
                await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
            return
        
        if not user.get('auth_token'):
            text = "❌ **Account belum terhubung!**\n\nAnda perlu menghubungkan akun Offroad League terlebih dahulu."
            keyboard = [
                [InlineKeyboardButton("🔗 Link Account", callback_data="account_menu")],
                [InlineKeyboardButton("🏠 Menu Utama", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if update.callback_query:
                await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
            else:
                await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
            return
        
        cars = self.livery_service.get_cars()
        
        text = "🚗 **Pilih Mobil**\n\nPilih mobil untuk melihat available liveries:"
        
        keyboard = []
        car_list = list(cars.items())[:8]
        
        for i in range(0, len(car_list), 2):
            row = []
            for car_code, car_data in car_list[i:i+2]:
                car_name = car_data.get('carName', 'Unknown')
                row.append(InlineKeyboardButton(
                    f"🚗 {car_name}", 
                    callback_data=f"livery_car_{car_code}"
                ))
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("🔍 Search Liveries", callback_data="search_liveries")])
        keyboard.append([InlineKeyboardButton("🏠 Menu Utama", callback_data="main_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_car_liveries(self, query, car_code: str):
        car_data = self.livery_service.get_car_data(car_code)
        if not car_data:
            await query.edit_message_text("❌ Mobil tidak ditemukan!")
            return
        
        liveries = car_data.get('liveries', [])
        car_name = car_data.get('carName', 'Unknown')
        
        text = f"🎨 **Liveries untuk {car_name}**\n\n"
        text += f"Total liveries: {len(liveries)}\n\n"
        
        keyboard = []
        for livery in liveries:
            livery_name = livery.get('name', 'Unknown')
            livery_id = livery.get('id')
            price = livery.get('price', {}).get('MN', 0)
            
            keyboard.append([
                InlineKeyboardButton(
                    f"🎨 {livery_name} ({price} MN)", 
                    callback_data=f"inject_livery_{livery_id}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Kembali ke Daftar Mobil", callback_data="livery_menu")])
        keyboard.append([InlineKeyboardButton("🏠 Menu Utama", callback_data="main_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def inject_livery(self, query, livery_id: str):
        user = await get_user(query.from_user.id)
        
        if user['credit'] < 1:
            await query.edit_message_text(
                "❌ **Credit tidak cukup!**\n\nSilakan top-up credit terlebih dahulu.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💰 Top-up", callback_data="topup_menu")],
                    [InlineKeyboardButton("🏠 Menu Utama", callback_data="main_menu")]
                ])
            )
            return
        
        if not user.get('auth_token'):
            await query.edit_message_text(
                "❌ **Account belum terhubung!**\n\nHubungkan akun Offroad League terlebih dahulu.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔗 Link Account", callback_data="account_menu")],
                    [InlineKeyboardButton("🏠 Menu Utama", callback_data="main_menu")]
                ])
            )
            return
        
        livery_data = self.livery_service.get_livery_data(livery_id)
        if not livery_data:
            await query.edit_message_text("❌ Livery tidak ditemukan!")
            return
        
        livery_name = livery_data['name']
        car_name = livery_data['car_name']
        
        injecting_text = f"""
🔄 **Injecting Livery...**

🎨 **Livery:** {livery_name}
🚗 **Mobil:** {car_name}
⏳ **Status:** Processing...

Harap tunggu, proses mungkin membutuhkan waktu beberapa detik.
        """
        
        await query.edit_message_text(injecting_text, parse_mode='Markdown')
        
        try:
            success, result = await self.livery_service.inject_livery(livery_id, user['auth_token'])
            
            if success:
                await update_user_credit(user['telegram_id'], -1)
                
                pool = await Database.get_pool()
                async with pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO user_liveries (user_id, livery_id, livery_name, car_name) 
                        VALUES ($1, $2, $3, $4)
                    """, user['id'], livery_id, livery_name, car_name)
                
                success_text = f"""
✅ **Livery Berhasil Diinject!**

🎨 **Livery:** {livery_name}
🚗 **Mobil:** {car_name}
💎 **Credit digunakan:** 1
💎 **Sisa credit:** {user['credit'] - 1}

Livery sudah ditambahkan ke akun Offroad League Anda. Silakan buka game untuk melihatnya!
                """
                
                keyboard = [
                    [InlineKeyboardButton("🎨 Inject Lainnya", callback_data="livery_menu")],
                    [InlineKeyboardButton("💎 Cek Credit", callback_data="check_credit")],
                    [InlineKeyboardButton("🏠 Menu Utama", callback_data="main_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(success_text, reply_markup=reply_markup, parse_mode='Markdown')
                
            else:
                error_msg = result.get('error', 'Unknown error')
                error_text = f"""
❌ **Gagal Inject Livery!**

🎨 **Livery:** {livery_name}
🚗 **Mobil:** {car_name}
❌ **Error:** {error_msg}

**Kemungkinan penyebab:**
- Token expired
- Server sedang maintenance
- Koneksi bermasalah

Silakan coba lagi atau hubungi admin.
                """
                
                keyboard = [
                    [InlineKeyboardButton("🔙 Coba Lagi", callback_data=f"inject_livery_{livery_id}")],
                    [InlineKeyboardButton("🔄 Update Token", callback_data="account_menu")],
                    [InlineKeyboardButton("🏠 Menu Utama", callback_data="main_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(error_text, reply_markup=reply_markup, parse_mode='Markdown')
                
        except Exception as e:
            logger.error(f"Injection error: {e}")
            error_text = f"""
❌ **Error System!**

Terjadi kesalahan sistem saat melakukan injeksi.

**Error:** {str(e)}

Silakan coba lagi nanti atau hubungi admin.
            """
            
            await query.edit_message_text(error_text, parse_mode='Markdown')
    
    async def handle_livery_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        callback_data = query.data
        
        if callback_data.startswith('livery_car_'):
            car_code = callback_data.replace('livery_car_', '')
            await self.show_car_liveries(query, car_code)
        
        elif callback_data.startswith('inject_livery_'):
            livery_id = callback_data.replace('inject_livery_', '')
            await self.inject_livery(query, livery_id)
        
        elif callback_data == "search_liveries":
            await self.show_search_liveries(query)
    
    async def show_search_liveries(self, query):
        text = "🔍 **Search Liveries**\n\nKetik nama livery atau mobil yang ingin dicari.\n\nContoh: `Thunder`, `Hunter`, `Shadow`"
        
        keyboard = [
            [InlineKeyboardButton("🔙 Kembali", callback_data="livery_menu")],
            [InlineKeyboardButton("🏠 Menu Utama", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def handle_search_liveries(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        search_query = update.message.text
        results = self.livery_service.search_liveries(search_query)
        
        if not results:
            await update.message.reply_text(
                f"❌ Tidak ditemukan livery untuk pencarian: `{search_query}`",
                parse_mode='Markdown'
            )
            return
        
        text = f"🔍 **Hasil Pencarian: {search_query}**\n\n"
        text += f"Ditemukan {len(results)} livery:\n\n"
        
        limited_results = results[:10]
        
        keyboard = []
        for result in limited_results:
            keyboard.append([
                InlineKeyboardButton(
                    f"🎨 {result['name']} ({result['car_name']})", 
                    callback_data=f"inject_livery_{result['id']}"
                )
            ])
        
        if len(results) > 10:
            text += f"Menampilkan 10 dari {len(results)} hasil\n\n"
        
        keyboard.append([InlineKeyboardButton("🔍 Search Lagi", callback_data="search_liveries")])
        keyboard.append([InlineKeyboardButton("🏠 Menu Utama", callback_data="main_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = update.message.text
        
        if context.user_data.get('searching_liveries'):
            await self.handle_search_liveries(update, context)
        elif message.lower() in ['menu', 'main menu']:
            await self.show_main_menu(update, context)
        elif 'credit' in message.lower():
            await self.show_credit(update, context)
        elif 'topup' in message.lower() or 'top-up' in message.lower():
            from handlers.payment_handlers import PaymentHandlers
            await PaymentHandlers().show_topup_menu(update, context)
        elif 'inject' in message.lower() or 'livery' in message.lower():
            await self.show_livery_menu(update, context)
        elif 'account' in message.lower() or 'token' in message.lower():
            from handlers.account_handlers import AccountHandlers
            await AccountHandlers().show_account_menu(update, context)
        else:
            await update.message.reply_text(
                "Gunakan menu command atau button untuk berinteraksi dengan bot.\n\n"
                "Gunakan /start untuk melihat menu utama."
            )