# Backend إدارة احمد ال علي TV

خدمة Python تجمع بين **Telegram Bot** للإدارة و **FastAPI** للتطبيق. لا توجد بيانات Xtream داخل APK؛ بيانات Username/Password تُشفّر بـFernet داخل SQLite، والتطبيق يحصل على كتالوج القنوات من `/api/channels`.

## التشغيل

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python3 - <<'PY'
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
PY
# ضع المفتاح الناتج في FERNET_KEY، وأنشئ BOT_TOKEN وAPP_API_KEY
uvicorn app.api:app --host 0.0.0.0 --port 8000
# في طرفية ثانية:
python run.py
```

أوامر المدير: `/addxtream`, `/servers`, `/editxtream <id> <url> <user> <password> <name>`, `/update [id]`, `/delete <id>`, `/status`.

## API للتطبيق

- `GET /health` فحص الخدمة.
- `GET /api/channels` مع ترويسة `X-API-Key` يعيد القنوات وروابط تشغيل opaque مثل `/api/stream/{id}`.
- `GET /api/categories` مع ترويسة `X-API-Key`.
- `/api/stream/{id}` يحول الطلب إلى مسار Xtream بعد فك التشفير على الخادم.

للتطوير استخدم `backend_base_url` و`backend_api_key` في `strings.xml`. في الإنتاج استبدلهما بقيم بيئة الإصدار ولا تستخدم HTTP غير المشفر.

## ملاحظات أمنية

- لا تسجل كلمات المرور ولا ترسلها إلى التطبيق.
- غيّر `APP_API_KEY` و`FERNET_KEY` قبل التشغيل.
- احفظ `.env` و`data/` خارج Git؛ استخدم HTTPS وreverse proxy في الإنتاج.
- البوت يقبل أوامر الإدارة من Telegram ID `6803988521` فقط.
