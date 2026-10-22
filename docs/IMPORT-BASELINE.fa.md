# انتقال امن بسته کد محلی به GitHub

مخزن آنلاین فعلاً ممکن است فقط اسناد تصمیم‌گیری داشته باشد. فایل‌های اجرایی در بسته BazaarCompass-GitHub-Ready.zip از گفتگو وجود دارند و باید جداگانه منتقل شوند. GitHub connector در این محیط فایل باینری ZIP را مستقیماً آپلود نمی‌کند.

## روش امن (ترمینال سیستم شخصی)
۱. نسخه ZIP را استخراج کنید؛ هیچ فایل .env، دیتاست zip/csv، node_modules یا venv نباید داخل آن باشد.
۲. clone مخزن:
    git clone https://github.com/afakhari/shopping_agent.git
    cd shopping_agent
    git switch -c bootstrap/import-existing-code
۳. **محتویات استخراج‌شده** را بدون پوشه .git به ریشه clone کپی کنید. اسناد موجود در مخزن را با نسخه قدیمی جایگزین نکنید مگر بعد از diff؛ README/AGENTS.md را با احتیاط merge کنید.
۴. وضعیت فایل‌ها را ببینید:
    git status --short
    git diff --stat
    git diff --check
    git ls-files
۵. با gitignore و scanner محلی مطمئن شوید secret و dataset در stage نیستند.
۶. تغییرات را commit و push کنید:
    git add -A
    git diff --cached --check
    git commit -m "chore: import sanitized Bazaar Compass baseline"
    git push -u origin bootstrap/import-existing-code
۷. Pull Request به main بسازید، CI را رفع کنید، سپس merge.

**فایل‌های محافظت‌شده:** .env، API keys، credential، database dump، دیتاست مسابقه، پوشه .git دیگر و node_modules. هیچ‌وقت main را force-push نکنید.
