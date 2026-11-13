"""Golden dataset for AI evaluation (Phase 08 seed, Phase 14 expansion).

Categories follow ``docs/15`` §3 (regulations, course prerequisites, exam
schedule, academic calendar, professors, hybrid queries, unsupported
questions) plus the extra registration/scholarship/thesis groups introduced
by the Phase 08 seed.

Item shape follows ``docs/08`` §4: every case defines the query, the expected
retrieval source(s), and — for grounded items — the facts a correct answer may
contain and claims it must never invent:

* ``question``         — the Persian query.
* ``expected_title``   — the document title retrieval must surface in top-k
                          (``None`` for unsupported/refusal cases).
* ``category``         — one of the docs/15 §3 groups (+ extras).
* ``expected_facts``   — substrings a grounded answer must include (docs/15
                          §2 "factual consistency"/"completeness").
* ``forbidden``        — substrings that would indicate an invented fact
                          (docs/15 §2 "refusal/insufficiency behaviour").
* ``spell_variant``    — an alternate spelling of the same question (ی/ي, ک/ك,
                          نیم‌فاصله) that must retrieve the same chunk (docs/15
                          §2 "language quality"; the Phase 08 normalizer keeps
                          variants equivalent).
"""

from __future__ import annotations


def _item(question: str, expected_title: str | None, category: str, **extra) -> dict:
    item = {
        "question": question,
        "expected_title": expected_title,
        "category": category,
    }
    item.update(extra)
    return item

GOLDEN_DATASET: list[dict] = [
    # --- regulations (docs/15 §3) -------------------------------------------
    _item("شرایط مشروطی چیست؟", "آیین‌نامه آموزشی", "regulation",
          expected_facts=["مشروط"], forbidden=["3.5", "معدل بالای ۱۸"]),
    _item("نحوه انصراف از تحصیل چگونه است؟", "آیین‌نامه آموزشی", "regulation",
          expected_facts=["انصراف"]),
    _item("حداقل واحد برای ترم مشروط چقدر است؟", "آیین‌نامه آموزشی", "regulation"),
    _item("چه کسانی می‌توانند مرخصی تحصیلی بگیرند؟", "آیین‌نامه آموزشی", "regulation"),
    _item("سقف واحد برای دانشجویان ترم اول چقدر است؟", "آیین‌نامه آموزشی", "regulation",
          expected_facts=["سقف", "واحد"], forbidden=["۲۰ واحد بدون استثناء"]),
    _item("شرایط اخذ درس بدون پیش‌نیاز چیست؟", "آیین‌نامه آموزشی", "regulation"),
    _item("نحوه محاسبه معدل ترم چگونه است؟", "آیین‌نامه آموزشی", "regulation"),
    _item("شرایط انتقالی چیست؟", "آیین‌نامه آموزشی", "regulation"),
    _item("حداقل نمره قبولی درس چند است؟", "آیین‌نامه آموزشی", "regulation"),
    _item("نحوه اعتراض به نمره چگونه است؟", "آیین‌نامه آموزشی", "regulation"),
    _item("شرایط مهمان شدن در دانشگاه دیگر چیست؟", "آیین‌نامه آموزشی", "regulation"),
    # Persian spelling variants must retrieve the same source (docs/15 §2).
    _item("شرايط مشروطی چیست؟", "آیین‌نامه آموزشی", "regulation",
          spell_variant="شرایط مشروطی چیست؟"),
    # --- course prerequisites ------------------------------------------------
    _item("پیش‌نیاز درس کارگاه کامپیوتر چیست؟", "سیلابس درس", "prerequisite",
          expected_facts=["پایه"]),
    _item("درس پایه پیش‌نیاز کدام درس‌ها است؟", "سیلابس درس", "prerequisite"),
    _item("برای اخذ مبانی برنامه‌نویسی چه پیش‌نیازی لازم است؟", "سیلابس درس", "prerequisite"),
    # --- exam schedule ---------------------------------------------------------
    _item("امتحان میان‌ترم چه تاریخی برگزار می‌شود؟", "برنامه امتحانات", "exam"),
    _item("امتحان پایان‌ترم کدام درس‌ها است؟", "برنامه امتحانات", "exam"),
    _item("سالن برگزاری امتحان کجاست؟", "برنامه امتحانات", "exam"),
    # --- academic calendar -----------------------------------------------------
    _item("مهلت حذف و اضافه چه زمانی است؟", "تقویم آموزشی", "calendar"),
    _item("کلاس‌های جبرانی چه زمانی برگزار می‌شود؟", "تقویم آموزشی", "calendar"),
    _item("شروع کلاس‌ها چه تاریخی است؟", "تقویم آموزشی", "calendar"),
    # --- professors --------------------------------------------------------------
    _item("استاد درس مبانی برنامه‌نویسی کیست؟", "فهرست اساتید", "professor"),
    _item("استاد درس پایه کیست؟", "فهرست اساتید", "professor"),
    _item("اعضای هیئت علمی گروه کامپیوتر چه کسانی هستند؟", "فهرست اساتید", "professor"),
    # --- hybrid queries ----------------------------------------------------------
    _item("پاسخ ترکیبی: با توجه به آیین‌نامه و دروس پاس‌شده چه درس‌هایی را می‌توانم بردارم؟",
          "آیین‌نامه آموزشی", "hybrid"),
    _item("با توجه به پیش‌نیازها و آیین‌نامه سقف واحد، آیا می‌توانم مبانی برنامه‌نویسی را بردارم؟",
          "آیین‌نامه آموزشی", "hybrid"),
    _item("با توجه به تقویم آموزشی و برنامه امتحانات، در بازه حذف و اضافه کدام امتحان برگزار می‌شود؟",
          "برنامه امتحانات", "hybrid"),
    # --- registration guide ------------------------------------------------------
    _item("نحوه ثبت‌نام در کارگاه‌ها چگونه است؟", "راهنمای ثبت‌نام", "registration"),
    _item("امکان تغییر گروه درسی وجود دارد؟", "راهنمای ثبت‌نام", "registration"),
    # --- scholarship --------------------------------------------------------------
    _item("شرایط بورسیه تحصیلی چیست؟", "آیین‌نامه بورسیه", "scholarship"),
    # --- thesis --------------------------------------------------------------------
    _item("مدارک لازم برای دفاع پایان‌نامه چیست؟", "راهنمای پایان‌نامه", "thesis"),
    # --- unsupported: must refuse, never invent ------------------------------------
    _item("هواشناسی چیست؟", None, "unsupported",
          forbidden=["دانشگاه", "نیمسال"]),
    _item("قیمت بلیط هواپیما به استانبول چقدر است؟", None, "unsupported"),
    _item("فوتبال چه روزی بازی است؟", None, "unsupported"),
]
