import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from handlers.user_handlers import UserHandlers
from handlers.admin_handlers import AdminHandlers
from handlers.payment_handlers import PaymentHandlers
from handlers.account_handlers import AccountHandlers
from utils.database import create_tables

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class LiveryBot:
    def __init__(self):
        self.token = os.getenv('BOT_TOKEN')
        self.application = None
        self.user_handlers = UserHandlers()
        self.admin_handlers = AdminHandlers()
        self.payment_handlers = PaymentHandlers()
        self.account_handlers = AccountHandlers()
        
    async def init_db(self):
        try:
            await create_tables()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.user_handlers.handle_start(update, context)

    async def set_token(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.account_handlers.handle_set_token(update, context)

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        callback_data = query.data
        
        if callback_data.startswith('topup_'):
            await self.payment_handlers.handle_topup_callback(update, context)
        elif callback_data.startswith('confirm_payment_'):
            await self.payment_handlers.handle_confirm_payment(update, context)
        elif callback_data.startswith('admin_'):
            await self.admin_handlers.handle_admin_callback(update, context)
        elif callback_data.startswith('livery_') or callback_data.startswith('inject_livery_'):
            await self.user_handlers.handle_livery_callback(update, context)
        elif callback_data.startswith('account_'):
            await self.account_handlers.handle_account_callback(update, context)
        elif callback_data == 'main_menu':
            await self.user_handlers.show_main_menu(update, context)
        elif callback_data == 'check_credit':
            await self.user_handlers.show_credit(update, context)
        elif callback_data == 'livery_menu':
            await self.user_handlers.show_livery_menu(update, context)
        elif callback_data == 'topup_menu':
            await self.payment_handlers.show_topup_menu(update, context)
        elif callback_data == 'account_menu':
            await self.account_handlers.show_account_menu(update, context)
        elif callback_data == 'help':
            await self.show_help(update, context)
        else:
            logger.warning(f"Unknown callback data: {callback_data}")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = update.message
        
        if message.text.startswith('/'):
            return
        
        if message.photo and context.user_data.get('awaiting_payment_proof'):
            await self.payment_handlers.handle_payment_proof(update, context)
        else:
            await self.user_handlers.handle_text_message(update, context)

    async def show_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = """
🤖 **Livery Injection Bot - Help**

**Commands:**
/start - Mulai bot dan lihat menu utama
/credit - Cek credit Anda
/topup - Top-up credit
/set_token [token] - Set PlayFab auth token
/admin - Admin panel (admin only)

**Cara Menggunakan:**
1. **Setup Account** - Hubungkan akun Torque Drift dengan /set_token
2. **Top-up Credit** - Beli credit untuk injeksi livery
3. **Inject Livery** - Pilih livery yang ingin diinjeksi

**Pricing:**
- 1 Credit = 1 Livery injection
- Harga credit mulai dari Rp 5.000

**Support:**
Jika mengalami masalah, hubungi admin.
        """
        
        keyboard = [
            [InlineKeyboardButton("🏠 Menu Utama", callback_data="main_menu")],
            [InlineKeyboardButton("🔗 Account Setup", callback_data="account_menu")],
            [InlineKeyboardButton("💰 Top-up", callback_data="topup_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')

    def setup_handlers(self):
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("credit", self.user_handlers.show_credit))
        self.application.add_handler(CommandHandler("inject", self.user_handlers.show_livery_menu))
        self.application.add_handler(CommandHandler("topup", self.payment_handlers.show_topup_menu))
        self.application.add_handler(CommandHandler("admin", self.admin_handlers.admin_menu))
        self.application.add_handler(CommandHandler("set_token", self.set_token))
        self.application.add_handler(CommandHandler("help", self.show_help))
        
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_message))

    async def run_webhook(self):
        await self.init_db()
        self.application = Application.builder().token(self.token).build()
        self.setup_handlers()
        
        logger.info("Bot started successfully in webhook mode")
        return self.application

bot = LiveryBot()
application = None

async def setup_webhook():
    global application
    application = await bot.run_webhook()
    return application