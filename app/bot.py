from __future__ import annotations
import os, logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, ContextTypes, filters
from .db import connect, encrypt, init_db
from .xtream import clean_url, sync_server

logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
ADMIN_ID = int(os.getenv('ADMIN_ID', '6803988521'))
URL, USER, PASSWORD, NAME = range(4)

def is_admin(update: Update) -> bool:
    return bool(update.effective_user and update.effective_user.id == ADMIN_ID)
async def guard(update: Update) -> bool:
    if not is_admin(update):
        if update.effective_message: await update.effective_message.reply_text('غير مصرح لك باستخدام هذا البوت.')
        return False
    return True
async def start(update, context):
    if not await guard(update): return
    await update.message.reply_text('لوحة إدارة احمد ال علي TV\n/addxtream إضافة\n/servers عرض\n/update تحديث القنوات\n/delete حذف\n/editxtream تعديل\n/status الحالة')
async def add_start(update, context):
    if not await guard(update): return ConversationHandler.END
    await update.message.reply_text('أرسل رابط السيرفر:'); return URL
async def add_url(update, context): context.user_data['url']=clean_url(update.message.text); await update.message.reply_text('أرسل Username:'); return USER
async def add_user(update, context): context.user_data['username']=update.message.text.strip(); await update.message.reply_text('أرسل Password:'); return PASSWORD
async def add_password(update, context): context.user_data['password']=update.message.text.strip(); await update.message.reply_text('أرسل اسمًا للسيرفر:'); return NAME
async def add_name(update, context):
    d=context.user_data; name=update.message.text.strip()
    with connect() as con:
        cur=con.execute('INSERT INTO servers(name,url,username_enc,password_enc) VALUES(?,?,?,?)',(name,d['url'],encrypt(d['username']),encrypt(d['password']))); sid=cur.lastrowid
    await update.message.reply_text(f'تمت إضافة السيرفر #{sid}. استخدم /update {sid} لجلب القنوات.'); context.user_data.clear(); return ConversationHandler.END
async def cancel(update, context): context.user_data.clear(); await update.message.reply_text('تم الإلغاء.'); return ConversationHandler.END
async def servers(update, context):
    if not await guard(update): return
    with connect() as con: rows=con.execute('SELECT id,name,url,enabled,last_sync FROM servers ORDER BY id').fetchall()
    await update.message.reply_text('\n'.join(f"#{r['id']} — {r['name']} — {r['url']} — {'مفعل' if r['enabled'] else 'معطل'} — {r['last_sync'] or 'لم يحدث'}" for r in rows) or 'لا توجد سيرفرات.')
async def edit_cmd(update, context):
    if not await guard(update): return
    if len(context.args)!=5: await update.message.reply_text('الاستخدام: /editxtream <id> <url> <username> <password> <name>'); return
    sid,url,user,pwd,name=context.args
    with connect() as con:
        cur=con.execute('UPDATE servers SET url=?,username_enc=?,password_enc=?,name=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',(clean_url(url),encrypt(user),encrypt(pwd),name,int(sid)))
    await update.message.reply_text('تم تعديل السيرفر.' if cur.rowcount else 'السيرفر غير موجود.')
async def update_cmd(update, context):
    if not await guard(update): return
    with connect() as con: ids=[int(context.args[0])] if context.args else [r['id'] for r in con.execute('SELECT id FROM servers WHERE enabled=1')]
    results=[]
    for sid in ids:
        try: result=sync_server(sid); results.append(f'#{sid}: تم تحديث {result["channels"]} قناة')
        except Exception as e:
            with connect() as con: con.execute('UPDATE servers SET last_error=? WHERE id=?',(str(e)[:500],sid))
            results.append(f'#{sid}: فشل — {e}')
    await update.message.reply_text('\n'.join(results) or 'لا توجد سيرفرات.')
async def delete_cmd(update, context):
    if not await guard(update): return
    if not context.args: await update.message.reply_text('الاستخدام: /delete <server_id>'); return
    with connect() as con: cur=con.execute('DELETE FROM servers WHERE id=?',(int(context.args[0]),))
    await update.message.reply_text('تم الحذف.' if cur.rowcount else 'السيرفر غير موجود.')
async def status(update, context):
    if not await guard(update): return
    with connect() as con:
        s=con.execute('SELECT COUNT(*) c FROM servers').fetchone()['c']; c=con.execute('SELECT COUNT(*) c FROM channels').fetchone()['c']; e=con.execute('SELECT COUNT(*) c FROM servers WHERE last_error IS NOT NULL').fetchone()['c']
    await update.message.reply_text(f'الحالة: تعمل\nالسيرفرات: {s}\nالقنوات: {c}\nأخطاء مزامنة: {e}')
def run_bot():
    init_db(); token=os.getenv('BOT_TOKEN')
    if not token: raise RuntimeError('BOT_TOKEN is required')
    app=Application.builder().token(token).build()
    conv=ConversationHandler(entry_points=[CommandHandler('addxtream',add_start)],states={URL:[MessageHandler(filters.TEXT & ~filters.COMMAND,add_url)],USER:[MessageHandler(filters.TEXT & ~filters.COMMAND,add_user)],PASSWORD:[MessageHandler(filters.TEXT & ~filters.COMMAND,add_password)],NAME:[MessageHandler(filters.TEXT & ~filters.COMMAND,add_name)]},fallbacks=[CommandHandler('cancel',cancel)])
    for handler in [conv,CommandHandler('start',start),CommandHandler('servers',servers),CommandHandler('editxtream',edit_cmd),CommandHandler('update',update_cmd),CommandHandler('delete',delete_cmd),CommandHandler('status',status)]: app.add_handler(handler)
    app.run_polling(close_loop=False)
