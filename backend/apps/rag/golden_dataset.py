"""Seed golden dataset for retrieval evaluation (Phase 08 / V-09)."""

from __future__ import annotations

GOLDEN_DATASET = [
    {"question": "شرایط مشروطی چیست؟", "expected_title": "آیین‌نامه آموزشی", "category": "regulation"},
    {"question": "نحوه انصراف از تحصیل چگونه است؟", "expected_title": "آیین‌نامه آموزشی", "category": "regulation"},
    {"question": "حداقل واحد برای ترم مشروط چقدر است؟", "expected_title": "آیین‌نامه آموزشی", "category": "regulation"},
    {"question": "پیش‌نیاز درس کارگاه کامپیوتر چیست؟", "expected_title": "سیلابس درس", "category": "prerequisite"},
    {"question": "چه کسانی می‌توانند مرخصی تحصیلی بگیرند؟", "expected_title": "آیین‌نامه آموزشی", "category": "regulation"},
    {"question": "مهلت حذف و اضافه چه زمانی است؟", "expected_title": "تقویم آموزشی", "category": "calendar"},
    {"question": "امتحان میان‌ترم چه تاریخی برگزار می‌شود؟", "expected_title": "برنامه امتحانات", "category": "exam"},
    {"question": "استاد درس مبانی برنامه‌نویسی کیست؟", "expected_title": "فهرست اساتید", "category": "professor"},
    {"question": "سقف واحد برای دانشجویان ترم اول چقدر است؟", "expected_title": "آیین‌نامه آموزشی", "category": "regulation"},
    {"question": "شرایط اخذ درس بدون پیش‌نیاز چیست؟", "expected_title": "آیین‌نامه آموزشی", "category": "regulation"},
    {"question": "نحوه محاسبه معدل ترم چگونه است؟", "expected_title": "آیین‌نامه آموزشی", "category": "regulation"},
    {"question": "کلاس‌های جبرانی چه زمانی برگزار می‌شود؟", "expected_title": "تقویم آموزشی", "category": "calendar"},
    {"question": "شرایط انتقالی چیست؟", "expected_title": "آیین‌نامه آموزشی", "category": "regulation"},
    {"question": "حداقل نمره قبولی درس چند است؟", "expected_title": "آیین‌نامه آموزشی", "category": "regulation"},
    {"question": "نحوه ثبت‌نام در کارگاه‌ها چگونه است؟", "expected_title": "راهنمای ثبت‌نام", "category": "registration"},
    {"question": "امکان تغییر گروه درسی وجود دارد؟", "expected_title": "راهنمای ثبت‌نام", "category": "registration"},
    {"question": "شرایط بورسیه تحصیلی چیست؟", "expected_title": "آیین‌نامه بورسیه", "category": "scholarship"},
    {"question": "مدارک لازم برای دفاع پایان‌نامه چیست؟", "expected_title": "راهنمای پایان‌نامه", "category": "thesis"},
    {"question": "نحوه اعتراض به نمره چگونه است؟", "expected_title": "آیین‌نامه آموزشی", "category": "regulation"},
    {"question": "شرایط مهمان شدن در دانشگاه دیگر چیست؟", "expected_title": "آیین‌نامه آموزشی", "category": "regulation"},
    {"question": "پاسخ ترکیبی: با توجه به آیین‌نامه و دروس پاس‌شده چه درس‌هایی را می‌توانم بردارم؟", "expected_title": "آیین‌نامه آموزشی", "category": "hybrid"},
    {"question": "هواشناسی چیست؟", "expected_title": None, "category": "unsupported"},
]
