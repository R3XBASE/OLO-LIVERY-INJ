# Livery Injection Bot

Bot Telegram untuk injeksi livery Offroad League Online dengan sistem kredit.

## Fitur

- ✅ Sistem kredit untuk injeksi livery
- ✅ Integrasi dengan database Neon PostgreSQL
- ✅ Top-up dengan QRIS
- ✅ Admin panel untuk approve transaksi
- ✅ Real livery injection menggunakan PlayFab API
- ✅ Support semua liveries dari database asli

## Deployment

1. Setup database Neon PostgreSQL
2. Update environment variables di `.env`
3. Deploy ke Vercel
4. Set webhook Telegram

## Environment Variables

- `BOT_TOKEN`: Token bot Telegram
- `DATABASE_URL`: Connection string PostgreSQL
- `ADMIN_IDS`: ID Telegram admin (pisahkan dengan koma)

## Command

- `/start` - Menu utama
- `/credit` - Cek credit
- `/topup` - Top-up credit
- `/set_token` - Set auth token PlayFab
- `/admin` - Panel admin