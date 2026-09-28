import feedparser
import requests
import time
from playwright.sync_api import sync_playwright

TELEGRAM_TOKEN = "8944481402:AAEe-CI0nGfA03dJkz0dBk-iNLJGE2uGEWQ"
CHAT_ID = "595651385"

# الكلمات المفتاحية المستهدفة
KEYWORDS = [
    "تحليل بيانات", "تحليل البيانات", "محلل بيانات", "محلل البيانات", "بايثون",
    "data analyst", "data analysis", "data analytics", 
    "business analyst", "power bi developer", "tableau analyst", "python",
    "داشبورد", "داش بورد", "لوحة قيادة", "dashboard", "dashboards",
    "data visualization", "تصوير البيانات", "تمثيل البيانات", "تقارير", "إكسل", "اكسل", "excel",
    "إحصاء", "احصاء", "إحصائي", "احصائي", "biostatistics", "statistics", "statistical",
    "data_analysis", "data science", "علم البيانات"
]

# الكلمات المستبعدة لتجنب الوظائف غير المخصصة
EXCLUDED_KEYWORDS = [
    "article", "content writing", "copywriting", "academic writing", 
    "blog post", "translation", "data entry", "data typist", "manual typing", "proofreading"
]

# تجميع كافة Skill IDs الخاصة بعلم وتحليل البيانات على Freelancer
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
    
    # 1. استبعاد الكلمات غير التقنية
    for ex_kw in EXCLUDED_KEYWORDS:
        if ex_kw.lower() in text_to_check:
            return False
            
    # 2. المطابقة مع كلمات البيانات
    for kw in KEYWORDS:
        if kw.lower() in text_to_check:
            return True
            
    return False

def send_telegram_message(platform, title, link, summary):
    message = (
        f"🚨 **فرصة جديدة من منصة [{platform}]**\n\n"
        f"📌 **العنوان:** {title}\n\n"
        f"📝 **الوصف:**\n{summary[:250]}...\n\n"
        f"🔗 [اضغط هنا للتقديم]({link})"
    )
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print(f"[{platform}] تم إرسال الفرصة بنجاح: {title}")
        else:
            print(f"فشل الإرسال: {response.text}")
    except Exception as e:
        print(f"خطأ أثناء الإرسال: {e}")

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
            from bs4 import BeautifulSoup
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
                channel="chrome",
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
                from bs4 import BeautifulSoup
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

def check_new_jobs():
    print(f"\n========================================================")
    print(f"   📊 تقرير فحص المنصات الحية - ({time.strftime('%H:%M:%S')})")
    print(f"========================================================")
    
    for feed_info in RSS_FEEDS:
        platform_name = feed_info["platform"]
        feed_url = feed_info["url"]
        use_browser = feed_info.get("use_browser", False)
        
        try:
            raw_data = fetch_feed_content(feed_url, use_browser=use_browser)
            if raw_data:
                feed = feedparser.parse(raw_data)
                count = len(feed.entries)
                print(f"🟢 [{platform_name:<25}]: متصل بنجاح | قرأ ({count}) عنصر حالي.")
                
                for entry in reversed(feed.entries):
                    job_id = entry.link
                    if job_id not in sent_jobs:
                        sent_jobs.add(job_id)
                        
                        title = getattr(entry, 'title', '')
                        summary_clean = getattr(entry, 'summary', '')
                        categories_text = extract_categories_and_tags(entry)
                        
                        summary_clean = (
                            summary_clean.replace('<p>', '')
                            .replace('</p>', '')
                            .replace('<br />', '\n')
                            .replace('<br>', '\n')
                        )
                        
                        if is_relevant_job(title, summary_clean, categories_text):
                            send_telegram_message(platform_name, title, entry.link, summary_clean)
            else:
                print(f"🔴 [{platform_name:<25}]: فشل الاتصال / محجوب.")
        except Exception as e:
            print(f"❌ [{platform_name:<25}]: خطأ - {e}")

    mostaql_jobs = fetch_mostaql_jobs()
    print(f"🟢 [{'مستقل':<25}]: متصل بنجاح | قرأ ({len(mostaql_jobs)}) فرصة.")
    for job in reversed(mostaql_jobs):
        job_id = job["link"]
        if job_id and job_id not in sent_jobs:
            sent_jobs.add(job_id)
            if is_relevant_job(job["title"], job["summary"], job.get("category", "")):
                send_telegram_message("مستقل", job["title"], job["link"], job["summary"])

    upwork_jobs = fetch_upwork_jobs()
    print(f"🟢 [{'Upwork':<25}]: متصل بنجاح | قرأ ({len(upwork_jobs)}) فرصة.")
    for job in reversed(upwork_jobs):
        job_id = job["link"]
        if job_id and job_id not in sent_jobs:
            sent_jobs.add(job_id)
            if is_relevant_job(job["title"], job["summary"], job.get("category", "")):
                send_telegram_message("Upwork", job["title"], job["link"], job["summary"])

    linkedin_jobs = fetch_linkedin_jobs()
    print(f"🟢 [{'LinkedIn (مصر + Remote)':<25}]: متصل بنجاح | قرأ ({len(linkedin_jobs)}) فرصة.")
    for job in reversed(linkedin_jobs):
        job_id = job["link"]
        if job_id and job_id not in sent_jobs:
            sent_jobs.add(job_id)
            if is_relevant_job(job["title"], job["summary"], job.get("category", "")):
                send_telegram_message("LinkedIn", job["title"], job["link"], job["summary"])
    
    print(f"--------------------------------------------------------\n")

def initialize():
    print("\nجاري التهيئة وتوسيع نطاق Skill IDs لـ Freelancer شاملة Power BI و Excel والـ Statistics...\n")
    
    for feed_info in RSS_FEEDS:
        try:
            raw_data = fetch_feed_content(feed_info["url"], use_browser=feed_info.get("use_browser", False))
            if raw_data:
                feed = feedparser.parse(raw_data)
                for entry in feed.entries:
                    sent_jobs.add(entry.link)
                print(f"✅ تم تأكيد الاتصال بـ: {feed_info['platform']}")
        except Exception:
            pass

    try:
        mostaql_jobs = fetch_mostaql_jobs()
        for job in mostaql_jobs:
            if job["link"]:
                sent_jobs.add(job["link"])
        print(f"✅ تم تأكيد الاتصال بـ: مستقل.")
    except Exception:
        pass
            
    try:
        upwork_jobs = fetch_upwork_jobs()
        for job in upwork_jobs:
            if job["link"]:
                sent_jobs.add(job["link"])
        print("✅ تم تأكيد الاتصال بـ: Upwork")
    except Exception:
        pass

    try:
        linkedin_jobs = fetch_linkedin_jobs()
        for job in linkedin_jobs:
            if job["link"]:
                sent_jobs.add(job["link"])
        print("✅ تم تأكيد الاتصال بـ: LinkedIn")
    except Exception:
        pass
            
    print("\nاكتملت التهيئة! البوت يغطي الآن جميع أدوات ومهارات تحليل البيانات على Freelancer...\n")

initialize()

while True:
    try:
        check_new_jobs()
    except Exception as e:
        print(f"خطأ في الحلقة الأساسية: {e}")
    time.sleep(180)