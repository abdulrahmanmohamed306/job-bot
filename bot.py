import os
import json
import threading
import time
import feedparser
import requests
import cloudscraper
from bs4 import BeautifulSoup
from flask import Flask, request

# ========================================================
# 1. إعداد سيرفر Flask وقاعدة البيانات السحابية (JSONBin)
# ========================================================
app = Flask(__name__)

TELEGRAM_TOKEN = "8944481402:AAEe-CI0nGfA03dJkz0dBk-iNLJGE2uGEWQ"
ADMIN_CHAT_ID = "595651385"

BIN_ID = "6abbabb6ffd5d160533b52b6"
API_KEY = "$2a$10$EajWbmH5WUuF5mKv4WDsnOR9T8wJeueARqCiGkaTycmGoaFAx05w6"

# 🔑 مفتاح ScraperAPI الخاص بك
SCRAPER_API_KEY = "f98dad3c712a79bf94eacfd5884d699d"

JSONBIN_URL = f"https://api.jsonbin.io/v3/b/{BIN_ID}"
HEADERS = {
    "Content-Type": "application/json",
    "X-Master-Key": API_KEY
}

scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'desktop': True
    }
)

def load_users():
    try:
        res = requests.get(f"{JSONBIN_URL}/latest", headers=HEADERS, timeout=10)
        if res.status_code == 200:
            data = res.json().get("record", [])
            return set(str(uid) for uid in data)
        else:
            print(f"تنبيه JSONBin: استجابة برقم {res.status_code}", flush=True)
    except Exception as e:
        print(f"خطأ في قراءة قاعدة البيانات السحابية: {e}", flush=True)
    return {ADMIN_CHAT_ID}

def save_users(users_set):
    try:
        payload = list(users_set)
        res = requests.put(JSONBIN_URL, json=payload, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            print(f"✅ تم تحديث قائمة المستخدمين بالسحاب ({len(payload)} مستخدم)", flush=True)
    except Exception as e:
        print(f"خطأ في حفظ المستخدمين في السحاب: {e}", flush=True)

users = load_users()

@app.route('/')
def health_check():
    return f"Job Scraper Bot is running live 24/7! Total Cloud Users: {len(users)}", 200

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
                welcome_msg = (
                    "أهلاً بك! 🎉 تم تفعيل اشتراكك بنجاح.\n\n"
                    "🤖 **يقوم هذا البوت برصد وجلب أحدث فرص وتحليلات البيانات (Data Analysis) فور نشرها من المنصات التالية:**\n"
                    "• 🟢 **Upwork**\n"
                    "• 🟢 **LinkedIn** (مصر و Remote)\n"
                    "• 🟢 **Wuzzuf** (وظف - مصر و Remote)\n"
                    "• 🟢 **Freelancer**\n"
                    "• 🟢 **مستقل (Mostaql)**\n"
                    "• 🟢 **نفذلي (Nafazly)**\n"
                    "• 🟢 **خمسات (Khamsat)**\n"
                    "• 🟢 **كفيل (Kafiil)**\n"
                    "• 🟢 **PeoplePerHour**\n"
                    "• 🟢 **We Work Remotely & Guru**\n\n"
                    "⚡️ ستصلك الإشعارات فور توفر أي فرصة جديدة!"
                )
                send_direct_message(chat_id, welcome_msg)
                send_direct_message(ADMIN_CHAT_ID, f"🔔 **مشترك جديد انضم للبوت!**\nID: `{chat_id}`\nإجمالي المشتركين الآن: **{len(users)}**")
            else:
                send_direct_message(chat_id, "أنت مشترك بالفعل في البوت! ستصلك الفرص فور توفرها.")
                
        elif text in ["/stop", "/unsubscribe"]:
            if chat_id in users:
                users.remove(chat_id)
                save_users(users)
                send_direct_message(chat_id, "تم إلغاء إشتراكك بنجاح. لن تصلك إشعارات جديدة.")
                send_direct_message(ADMIN_CHAT_ID, f"⚠️ **مشترك ألغى اشتراكه.**\nإجمالي المشتركين الآن: **{len(users)}**")
            else:
                send_direct_message(chat_id, "أنت غير مشترك في البوت حالياً.")

        elif text == "/stats" and chat_id == ADMIN_CHAT_ID:
            send_direct_message(ADMIN_CHAT_ID, f"📊 **إحصائيات البوت:**\n\nعدد المشتركين الدائمين (السحاب): **{len(users)}** مستخدم.")

    return "OK", 200

def set_webhook_auto():
    time.sleep(3)
    webhook_url = f"https://job-bot-bfhd.onrender.com/{TELEGRAM_TOKEN}"
    try:
        res = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook?url={webhook_url}")
        print(f"✅ نتيجة ربط الـ Webhook: {res.json()}", flush=True)
    except Exception as e:
        print(f"خطأ في إعداد Webhook: {e}", flush=True)

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=set_webhook_auto, daemon=True).start()
    app.run(host="0.0.0.0", port=port)

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

# القائمة المنقاة بعناية للوظائف
RSS_FEEDS = [
    {
        "platform": "Upwork (Data Analyst)",
        "url": "https://www.upwork.com/ab/feed/jobs/rss?q=data%20analyst&sort=recency",
        "use_proxy": True
    },
    {
        "platform": "Freelancer (All Data Skills)",
        "url": f"https://www.freelancer.com/rss.xml?{freelancer_skills_query}",
        "use_proxy": False
    },
    {
        "platform": "Guru",
        "url": "https://www.guru.com/rss/jobs/q/data-analysis/",
        "use_proxy": True
    },
    {
        "platform": "We Work Remotely (Data)",
        "url": "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss",
        "use_proxy": False
    },
    {
        "platform": "PeoplePerHour",
        "url": "https://www.peopleperhour.com/rss/freelance-data-analysis-jobs",
        "use_proxy": True
    }
]

sent_jobs = set()

# ========================================================
# 3. الدوال المساعدة والفلترة والإرسال الجماعي
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
        print(f"خطأ إرسال فردي لـ {chat_id}: {e}", flush=True)

def send_telegram_message_to_all(platform, title, link, summary):
    message = (
        f"🚨 **فرصة جديدة من منصة [{platform}]**\n\n"
        f"📌 **العنوان:** {title}\n\n"
        f"📝 **الوصف:**\n{summary[:250]}...\n\n"
        f"🔗 [اضغط هنا للتقديم]({link})"
    )
    
    current_users = list(users)
    print(f"[{platform}] جاري إرسال الفرصة لـ {len(current_users)} مشترك: {title}", flush=True)
    
    for u_id in current_users:
        send_direct_message(u_id, message)

# ========================================================
# 4. دوال جلب الوظائف المحسنة مع دعم ScraperAPI
# ========================================================
def fetch_feed_content(url, use_proxy=False):
    try:
        if use_proxy:
            api_url = f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={requests.utils.quote(url)}"
            res = requests.get(api_url, timeout=25)
        else:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            res = scraper.get(url, headers=headers, timeout=12)
            
        if res.status_code == 200:
            return res.content
        else:
            print(f"⚠ [RSS Feed Error] {url} returned status: {res.status_code}", flush=True)
    except Exception as e:
        print(f"❌ [RSS Feed Exception] {url}: {e}", flush=True)
    return None

def fetch_wuzzuf_jobs():
    jobs = []
    urls = [
        "https://wuzzuf.net/search/jobs/?q=data+analyst&a=hpb",
        "https://wuzzuf.net/search/jobs/?q=data+analysis&a=hpb"
    ]
    for url in urls:
        try:
            api_url = f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url={requests.utils.quote(url)}"
            res = requests.get(api_url, timeout=25)
            print(f"🔍 [Wuzzuf via ScraperAPI] Status Code: {res.status_code}", flush=True)
            
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                job_cards = soup.select('div[class*="css-"]') or soup.find_all('article')
                for card in job_cards:
                    a_tag = card.find('a', href=True)
                    if a_tag and '/jobs/p/' in a_tag['href']:
                        title = a_tag.text.strip()
                        link = a_tag['href']
                        if not link.startswith('http'):
                            link = f"https://wuzzuf.net{link}"
                        jobs.append({"title": title, "link": link, "summary": "وظيفة تحليل بيانات على منصة Wuzzuf", "category": "Wuzzuf"})
        except Exception as e:
            print(f"❌ [Wuzzuf Error]: {e}", flush=True)
    return jobs

def fetch_nafazly_jobs():
    jobs = []
    try:
        url = "https://nafazly.com/projects"
        res = scraper.get(url, timeout=12)
        print(f"🔍 [نفذلي] Status Code: {res.status_code}", flush=True)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            cards = soup.find_all('div', class_='project-card') or soup.select('.project-item, div[class*="project"]')
            for card in cards:
                a_tag = card.find('a', href=True)
                if a_tag and '/project/' in a_tag['href']:
                    title = a_tag.text.strip()
                    link = a_tag['href']
                    if not link.startswith('http'):
                        link = f"https://nafazly.com{link}"
                    desc_elem = card.find('p') or card.find('div', class_='description')
                    summary = desc_elem.text.strip() if desc_elem else "مشروع جديد على منصة نفذلي"
                    jobs.append({"title": title, "link": link, "summary": summary, "category": "نفذلي"})
    except Exception as e:
        print(f"❌ [نفذلي Error]: {e}", flush=True)
    return jobs

def fetch_mostaql_jobs():
    jobs = []
    try:
        url = "https://mostaql.com/projects"
        res = scraper.get(url, timeout=12)
        print(f"🔍 [مستقل] Status Code: {res.status_code}", flush=True)
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
    except Exception as e:
        print(f"❌ [مستقل Error]: {e}", flush=True)
    return jobs

def fetch_khamsat_jobs():
    jobs = []
    try:
        url = "https://khamsat.com/community/requests"
        res = scraper.get(url, timeout=12)
        print(f"🔍 [خمسات] Status Code: {res.status_code}", flush=True)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            links = soup.select('a[href*="/community/requests/"]')
            for a_tag in links:
                title = a_tag.text.strip()
                link = a_tag['href']
                if title and len(title) > 5:
                    if not link.startswith('http'):
                        link = f"https://khamsat.com{link}"
                    jobs.append({"title": title, "link": link, "summary": "طلب خدمة جديد في مجتمع خمسات", "category": "خمسات"})
    except Exception as e:
        print(f"❌ [خمسات Error]: {e}", flush=True)
    return jobs

def fetch_kafiil_jobs():
    jobs = []
    try:
        url = "https://kafiil.com/projects"
        res = scraper.get(url, timeout=12)
        print(f"🔍 [كفيل] Status Code: {res.status_code}", flush=True)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            cards = soup.find_all('div', class_='project-item') or soup.find_all('a', class_='title')
            for card in cards:
                a_tag = card if card.name == 'a' else card.find('a', href=True)
                if a_tag and '/project/' in a_tag.get('href', ''):
                    title = a_tag.text.strip()
                    link = a_tag['href']
                    if not link.startswith('http'):
                        link = f"https://kafiil.com{link}"
                    jobs.append({"title": title, "link": link, "summary": "مشروع جديد على منصة كفيل", "category": "كفيل"})
    except Exception as e:
        print(f"❌ [كفيل Error]: {e}", flush=True)
    return jobs

def fetch_linkedin_jobs():
    jobs = []
    urls = [
        "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=Data%20Analyst&location=Egypt&f_TPR=r86400&start=0",
        "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=Data%20Analyst&f_WT=2&f_TPR=r86400&start=0"
    ]
    for url in urls:
        try:
            response = scraper.get(url, timeout=12)
            print(f"🔍 [LinkedIn] Status Code: {response.status_code}", flush=True)
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
        except Exception as e:
            print(f"❌ [LinkedIn Error]: {e}", flush=True)
    return jobs

# ========================================================
# 5. حلقة الفحص الدوري المقسمة بدقة بحسب رصيد ScraperAPI
# ========================================================
def check_new_jobs(cycle_count):
    # فحص منصات ScraperAPI مرة كل 80 دورة (كل 4 ساعات)
    run_proxy_platforms = (cycle_count % 80 == 1)
    
    print(f"\n========================================================", flush=True)
    print(f"   📊 تقرير فحص المنصات الحية - (الدورة: #{cycle_count}) - ({time.strftime('%H:%M:%S')})", flush=True)
    print(f"   🎯 فحص منصات البروكسي (ScraperAPI): {'نعم ✅' if run_proxy_platforms else 'تخطي للحفاظ على الرصيد الشهري ⏳'}", flush=True)
    print(f"========================================================", flush=True)
    
    for feed_info in RSS_FEEDS:
        platform_name = feed_info["platform"]
        use_proxy = feed_info.get("use_proxy", False)

        if use_proxy and not run_proxy_platforms:
            continue

        try:
            raw_data = fetch_feed_content(feed_info["url"], use_proxy=use_proxy)
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
            print(f"❌ [{platform_name}]: خطأ - {e}", flush=True)

    custom_sources = []
    
    if run_proxy_platforms:
        custom_sources.append(("Wuzzuf", fetch_wuzzuf_jobs))

    custom_sources.extend([
        ("مستقل", fetch_mostaql_jobs),
        ("نفذلي", fetch_nafazly_jobs),
        ("خمسات", fetch_khamsat_jobs),
        ("كفيل", fetch_kafiil_jobs),
        ("LinkedIn", fetch_linkedin_jobs)
    ])

    for name, fetch_fn in custom_sources:
        try:
            jobs_list = fetch_fn()
            for job in reversed(jobs_list):
                job_id = job["link"]
                if job_id and job_id not in sent_jobs:
                    sent_jobs.add(job_id)
                    if is_relevant_job(job["title"], job["summary"], job.get("category", "")):
                        send_telegram_message_to_all(name, job["title"], job["link"], job["summary"])
        except Exception as e:
            print(f"❌ [{name}]: خطأ - {e}", flush=True)

def initialize():
    print("\nجاري بدء البوت وتسجيل الوظائف الحالية صامتاً لمنع التكرار عند التشغيل...\n", flush=True)
    
    for feed_info in RSS_FEEDS:
        try:
            raw_data = fetch_feed_content(feed_info["url"], use_proxy=feed_info.get("use_proxy", False))
            if raw_data:
                feed = feedparser.parse(raw_data)
                for entry in feed.entries:
                    if hasattr(entry, 'link'):
                        sent_jobs.add(entry.link)
        except Exception:
            pass

    custom_sources = [
        fetch_wuzzuf_jobs, fetch_mostaql_jobs, fetch_nafazly_jobs, 
        fetch_khamsat_jobs, fetch_kafiil_jobs, fetch_linkedin_jobs
    ]
    for fetch_fn in custom_sources:
        try:
            for job in fetch_fn():
                if job.get("link"):
                    sent_jobs.add(job["link"])
        except Exception:
            pass

    print(f"\nاكتملت التهيئة بنجاح! تم حظر {len(sent_jobs)} رابط سابق. البوت يرصد الفرص الجديدة فقط...\n", flush=True)

initialize()

cycle_count = 0

while True:
    try:
        cycle_count += 1
        check_new_jobs(cycle_count)
    except Exception as e:
        print(f"خطأ في الحلقة الأساسية: {e}", flush=True)
    
    time.sleep(180)