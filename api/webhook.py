import os
import json
import asyncio
from telegram import Update
from bot import setup_webhook

application = None

async def handler(request):
    global application
    
    if application is None:
        application = await setup_webhook()
    
    if request.method == 'POST':
        body = await request.text()
        data = json.loads(body)
        
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        
        return {'statusCode': 200, 'body': 'OK'}
    
    return {'statusCode': 405, 'body': 'Method Not Allowed'}

if __name__ == '__main__':
    async def main():
        app = await setup_webhook()
        await app.run_polling()
    
    asyncio.run(main())