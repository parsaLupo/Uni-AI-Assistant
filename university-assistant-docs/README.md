# University Smart Assistant

سامانه دستیار هوشمند دانشگاهی برای پاسخ‌گویی به پرسش‌های دانشجویان با تکیه بر داده‌های رسمی دانشگاه، داده‌های ساختاریافته و معماری RAG.

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React + TypeScript |
| Backend | Django + Django REST Framework |
| Database | PostgreSQL |
| Vector Search | pgvector |
| AI | LLM API through backend |
| Authentication | JWT-based authentication |
| Containerization | Docker / Docker Compose |
| Production OS | Linux server |

## Core idea

```text
Student
   |
   v
React Frontend
   |
   | REST / JSON
   v
Django + DRF
   |
   +---- PostgreSQL -------- structured academic data
   |
   +---- RAG / pgvector ---- university documents
   |
   +---- AI Service -------- LLM provider
   |
   v
Answer + Sources
   |
   v
React
```

## Documentation map

- `AGENTS.md` — قوانین و قراردادهای اجرایی برای AI Agent
- `docs/00-project-overview.md` — تعریف پروژه و دامنه
- `docs/01-requirements.md` — نیازمندی‌های عملکردی و غیرعملکردی
- `docs/02-system-architecture.md` — معماری سیستم
- `docs/03-database-design.md` — طراحی دیتابیس و ERD
- `docs/04-api-specification.md` — قرارداد کلی API
- `docs/05-authentication.md` — احراز هویت و مجوزها
- `docs/06-ai-rag-architecture.md` — معماری AI/RAG
- `docs/07-security.md` — الزامات امنیتی
- `docs/08-testing-strategy.md` — استراتژی تست
- `docs/09-deployment.md` — استقرار
- `docs/10-development-workflow.md` — گردش کار توسعه
- `docs/11-non-functional-requirements.md` — NFRها
- `docs/12-error-handling-observability.md` — خطا و مانیتورینگ
- `docs/13-project-scope.md` — مرزبندی MVP و آینده
- `docs/phases/` — برنامه اجرایی فازبه‌فاز
- `docs/decisions/` — تصمیمات معماری (ADR)
- `docs/api/` — جزئیات endpointها

## Development principle

فازها باید ترتیبی اجرا شوند و هر فاز باید در پایان یک وضعیت پایدار و قابل تست تحویل دهد. Agent نباید چند فاز را همزمان بدون دلیل روشن پیاده‌سازی کند.

## Local development target

در حالت توسعه محلی باید بتوان کل stack را با Docker Compose یا با ابزارهای استاندارد پروژه بالا آورد و endpoint سلامت backend و اتصال دیتابیس را بررسی کرد.

## MVP definition

MVP شامل احراز هویت، داده‌های آموزشی، استاد، تقویم، امتحانات، مدیریت اسناد، RAG، چت هوشمند و تاریخچه مکالمات است. Recommendation/Selection Intelligence و اعلان‌های پیشرفته بعد از MVP پیاده‌سازی می‌شوند.
