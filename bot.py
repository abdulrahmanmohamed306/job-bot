import os
import json
import threading
import time
import feedparser
import requests
from bs4 import BeautifulSoup
from flask import Flask, request
from playwright.sync_api import sync_playwright

# ========================================================
# 1. إعداد سيرفر Flask والـ Webhook
# ========================================================
app = Flask(__name__)

TELEGRAM_TOKEN = "8944481402:AAEe-CI0nGfA03dJkz0dBk-iNLJGE2uGEWQ"
ADMIN_CHAT_ID = "595651385"  # معرّفك الخاص للتحكم بـ /stats
USERS_FILE = "users.json"

# دالة تحميل قائمة المستخدمين
def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r") as f:
                return set(json.load(f))
        except Exception:
            return {ADMIN_CHAT_ID}
    return {ADMIN_CHAT_ID}

# دالة حفظ قائمة المستخدمين
def save_users(users_set):
    try:
        with open(USERS_FILE, "w") as f:
            json.dump(list(users_set), f)
    except Exception as e:
        print(f"خطأ في حفظ المستخدمين: {e}")

users = load_users()

@app.route('/')
def health_check():
    return f"Job Scraper Bot is running live 24/7! Total Users: {len(users)}", 200

# لاستقبال أوامر /start و /stats من تليجرام تلقائياً
@app.route(f'/{TELEGRAM_TOKEN}', methods=['POST'])
def telegram_webhook():
    update = request.get_json()
    if update and "message" in update:
        message = update["message"]
        chat_id = str(message.get("chat", {}).get("id"))
        text = message.get("text", "").strip()

        if text == "/start":
            if chat_id not in users:
                users.add(chat_id)
                save_users(users)
                send_direct_message(chat_id, "أهلاً بك! 🎉 تم تفعيل اشتراكك بنجاح. ستصلك إشعارات فورية بأحدث وظائف تحليل البيانات والداتا فور نشرها.")
            else:
                send_direct_message(chat_id, "أنت مشترك بالفعل في البوت! ستصلك الفرص فور توفرها.")
                
        elif text == "/stats" and chat_id == ADMIN_CHAT_ID:
            send_direct_message(ADMIN_CHAT_ID, f"📊 **إحصائيات البوت:**\n\nعدد المشتركين الحاليين: **{len(users)}** مستخدم.")

    return "OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    # ضبط الـ Webhook مع تليجرام تلقائياً
    render_url = os.environ.get("RENDER_EXTERNAL_URL")
    if render_url:
        webhook_url = f"{render_url}/{TELEGRAM_TOKEN}"
        try:
            requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook?url={webhook_url}")
            print(f"✅ تم تفعيل Webhook التليجرام: {webhook_url}")
        except Exception as e:
            print(f"خطأ في إعداد Webhook: {e}")
            
    app.run(host="0.0.0.0", port=port)

# تشغيل السيرفر في خيط مستقل
threading.Thread(target=run_flask, daemon=True).start()

# ========================================================
# 2. إعدادات الفلترة والبيانات الأساسية
# ========================================================
KEYWORDS = [
    "تحليل بيانات", "تحليل البيانات", "محلل بيانات", "محلل البيانات", "بايثون",
    "data analyst", "data analysis", "data analytics", 
    "business analyst", "power bi developer", "tableau analyst", "python",
    "داشبورد", "داش بورد", "لوحة قيادة", "dashboard", "dashboards",
    "data visualization", "تصوير البيانات", "تمثيل البيانات", "تقارير", "إكسل", "اكسل", "excel",
    "إحصاء", "احصاء", "إحصائي", "احصائي", "biostatistics", "statistics", "statistical",
    "data_analysis", "data science", "علم البيانات"
]

EXCLUDED_KEYWORDS = [
    "article", "content writing", "copywriting", "academic writing", 
    "blog post", "translation", "data entry", "data typist", "manual typing", "proofreading"
]

FREELANCER_SKILLS = [1042, 326, 110, 322, 2033, 1900, 44, 2182, 127, 439, 269, 889, 1282]
freelancer_skills_query = "&".join([f"jobs[]={s}" for s in FREELANCER_SKILLS])

RSS_FEEDS = [
    {
        "platform": "Freelancer (All Data Skills)",
        "url": f"https://www.freelancer.com/rss.xml?{freelancer_skills_query}",
        "use_browser": False
    },
    {
        "platform": "Guru",
        "url": "https://www.guru.com/rss/jobs/q/data-analysis/",
        "use_browser": True
    }
]

sent_jobs = set()

# ========================================================
# 3. الدوال المساعدة والفلترة وإرسال الجماعي
# ========================================================
def extract_categories_and_tags(entry):
    categories = []
    if hasattr(entry, 'tags'):
        for tag in entry.tags:
            if hasattr(tag, 'term') and tag.term:
                categories.append(tag.term)
            elif hasattr(tag, 'label') and tag.label:
                categories.append(tag.label)
    if hasattr(entry, 'category') and entry.category:
        categories.append(entry.category)
    return " ".join(categories)

def is_relevant_job(title, summary, categories=""):
    text_to_check = f"{title} {summary} {categories}".lower()
    for ex_kw in EXCLUDED_KEYWORDS:
        if ex_kw.lower() in text_to_check:
            return False
    for kw in KEYWORDS:
        if kw.lower() in text_to_check:
            return True
    return False

def send_direct_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"خطأ إرسال فردي لـ {chat_id}: {e}")

def send_telegram_message_to_all(platform, title, link, summary):
    message = (
        f"🚨 **فرصة جديدة من منصة [{platform}]**\n\n"
        f"📌 **العنوان:** {title}\n\n"
        f"📝 **الوصف:**\n{summary[:250]}...\n\n"
        f"🔗 [اضغط هنا للتقديم]({link})"
    )
    
    current_users = list(users)
    print(f"[{platform}] جاري إرسال الفرصة لـ {len(current_users)} مشترك: {title}")
    
    for u_id in current_users:
        send_direct_message(u_id, message)

# ========================================================
# 4. دوال جلب الوظائف
# ========================================================
def fetch_feed_content(url, use_browser=False):
    if not use_browser:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        try:
            res = requests.get(url, headers=headers, timeout=15)
            return res.content if res.status_code == 200 else None
        except Exception:
            return None
    else:
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                )
                page = context.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                content = page.content()
                browser.close()
                return content
        except Exception:
            return None

def fetch_mostaql_jobs():
    jobs = []
    try:
        url = "https://mostaql.com/projects"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            rows = soup.find_all('tr', class_='project-row') or soup.find_all('div', class_='project-card')
            if not rows:
                rows = soup.select("table.table-projects tbody tr, div.mrg--b-0")
            for row in rows:
                a_tag = row.find('a', href=True)
                if a_tag and '/project/' in a_tag['href']:
                    title = a_tag.text.strip()
                    link = a_tag['href']
                    if not link.startswith('http'):
                        link = f"https://mostaql.com{link}"
                    desc_tag = row.find('p') or row.find('td', class_='project-brief')
                    summary = desc_tag.text.strip() if desc_tag else title
                    jobs.append({"title": title, "link": link, "summary": summary, "category": "مستقل"})
    except Exception:
        pass
    return jobs

def fetch_upwork_jobs():
    jobs = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                viewport={'width': 1366, 'height': 768}
            )
            page = context.new_page()
            page.route("**/*.{png,jpg,jpeg,svg,webp}", lambda route: route.abort())
            
            url = "https://www.upwork.com/nx/search/jobs/?q=data%20analyst&sort=recency"
            page.goto(url, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(3000)
            page.evaluate("window.scrollBy(0, 600)")
            
            job_cards = page.query_selector_all("article, section[data-test='JobTile'], div[data-test='JobTile']")
            for card in job_cards:
                title_elem = card.query_selector("h2 a, h3 a, a[aria-label]")
                desc_elem = card.query_selector("span[data-test='job-description'], div[class*='description'], p")
                if title_elem:
                    title = title_elem.inner_text().strip()
                    href = title_elem.get_attribute("href")
                    link = f"https://www.upwork.com{href}" if href and not href.startswith("http") else (href or "")
                    summary = desc_elem.inner_text().strip() if desc_elem else "اضغط على الرابط لمشاهدة التفاصيل..."
                    jobs.append({"title": title, "link": link, "summary": summary, "category": "Data Analysis"})
            browser.close()
    except Exception:
        pass
    return jobs

def fetch_linkedin_jobs():
    jobs = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    urls = [
        "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=Data%20Analyst&location=Egypt&f_TPR=r86400&start=0",
        "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=Data%20Analyst&f_WT=2&f_TPR=r86400&start=0"
    ]
    for url in urls:
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                posts = soup.find_all('li')
                for post in posts:
                    title_elem = post.find('h3', class_='base-search-card__title')
                    link_elem = post.find('a', class_='base-card__full-link')
                    company_elem = post.find('h4', class_='base-search-card__subtitle')
                    location_elem = post.find('span', class_='job-search-card__location')
                    if title_elem and link_elem:
                        title = title_elem.text.strip()
                        link = link_elem['href'].split('?')[0]
                        company = company_elem.text.strip() if company_elem else "LinkedIn"
                        location = location_elem.text.strip() if location_elem else "مصر/عن بُعد"
                        summary = f"شركة: {company} | المكان: {location} | فرصة تحليل بيانات من LinkedIn."
                        jobs.append({"title": title, "link": link, "summary": summary, "category": "Data Analytics"})
        except Exception:
            pass
    return jobs

# ========================================================
# 5. حلقة الفحص الدوري
# ========================================================
def check_new_jobs():
    print(f"\n========================================================")
    print(f"   📊 تقرير فحص المنصات الحية - ({time.strftime('%H:%M:%S')}) - المشتركين: {len(users)}")
    print(f"========================================================")
    
    for feed_info in RSS_FEEDS:
        platform_name = feed_info["platform"]
        try:
            raw_data = fetch_feed_content(feed_info["url"], use_browser=feed_info.get("use_browser", False))
            if raw_data:
                feed = feedparser.parse(raw_data)
                for entry in reversed(feed.entries):
                    job_id = entry.link
                    if job_id not in sent_jobs:
                        sent_jobs.add(job_id)
                        title = getattr(entry, 'title', '')
                        summary_clean = getattr(entry, 'summary', '')
                        categories_text = extract_categories_and_tags(entry)
                        summary_clean = summary_clean.replace('<p>', '').replace('</p>', '').replace('<br />', '\n').replace('<br>', '\n')
                        if is_relevant_job(title, summary_clean, categories_text):
                            send_telegram_message_to_all(platform_name, title, entry.link, summary_clean)
        except Exception as e:
            print(f"❌ [{platform_name}]: خطأ - {e}")

    mostaql_jobs = fetch_mostaql_jobs()
    for job in reversed(mostaql_jobs):
        job_id = job["link"]
        if job_id and job_id not in sent_jobs:
            sent_jobs.add(job_id)
            if is_relevant_job(job["title"], job["summary"], job.get("category", "")):
                send_telegram_message_to_all("مستقل", job["title"], job["link"], job["summary"])

    upwork_jobs = fetch_upwork_jobs()
    for job in reversed(upwork_jobs):
        job_id = job["link"]
        if job_id and job_id not in sent_jobs:
            sent_jobs.add(job_id)
            if is_relevant_job(job["title"], job["summary"], job.get("category", "")):
                send_telegram_message_to_all("Upwork", job["title"], job["link"], job["summary"])

    linkedin_jobs = fetch_linkedin_jobs()
    for job in reversed(linkedin_jobs):
        job_id = job["link"]
        if job_id and job_id not in sent_jobs:
            sent_jobs.add(job_id)
            if is_relevant_job(job["title"], job["summary"], job.get("category", "")):
                send_telegram_message_to_all("LinkedIn", job["title"], job["link"], job["summary"])

def initialize():
    print("\nجاري التهيئة وتخزين الوظائف السابقة لتجنب التكرار...\n")
    for feed_info in RSS_FEEDS:
        try:
            raw_data = fetch_feed_content(feed_info["url"], use_browser=feed_info.get("use_browser", False))
            if raw_data:
                feed = feedparser.parse(raw_data)
                for entry in feed.entries:
                    sent_jobs.add(entry.link)
        except Exception:
            pass

    try:
        for job in fetch_mostaql_jobs():
            if job["link"]: sent_jobs.add(job["link"])
    except Exception: pass
    try:
        for job in fetch_upwork_jobs():
            if job["link"]: sent_jobs.add(job["link"])
    except Exception: pass
    try:
        for job in fetch_linkedin_jobs():
            if job["link"]: sent_jobs.add(job["link"])
    except Exception: pass
    print("\nاكتملت التهيئة بنجاح! البوت جاهز ويستقبل المشتركين...\n")

initialize()

while True:
    try:
        check_new_jobs()
    except Exception as e:
        print(f"خطأ في الحلقة الأساسية: {e}")
    time.sleep(180)