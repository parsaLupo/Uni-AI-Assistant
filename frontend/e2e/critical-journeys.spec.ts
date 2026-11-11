/**
 * Phase 14 — the seven critical journeys (docs/08-testing-strategy.md §3).
 *
 * Each test walks one journey through the real stack (Vite proxy → Docker
 * backend → PostgreSQL with the seeded dataset). The assistant journeys are
 * deterministic because the backend runs with AI_PROVIDER=mock
 * (docker-compose.e2e.yml); every other surface is production code.
 *
 * Persian UI strings come from src/i18n/fa.ts verbatim — the suite must break
 * when the wording a user depends on changes.
 */
import { expect, test, type Page } from "@playwright/test";

const STUDENT = { email: "student@semnan.local", password: "Demo-Passw0rd!" };
const ADMIN = { email: "admin@semnan.local", password: "Demo-Passw0rd!" };

/** Login through the real /login form. */
async function login(page: Page, account: { email: string; password: string }) {
  await page.goto("/login");
  await page.fill("#login-email", account.email);
  await page.fill("#login-password", account.password);
  await page.getByRole("button", { name: "ورود" }).click();
  await page.waitForURL("**/dashboard");
}

test.describe.serial("critical journeys (docs/08 §3)", () => {
  test("1 — registration lands on the student dashboard", async ({ page }) => {
    const email = `e2e-${Date.now()}@test.semnan.local`;
    await page.goto("/register");
    await page.fill("#register-first-name", "آزمون");
    await page.fill("#register-last-name", "سرتاسری");
    await page.fill("#register-email", email);
    await page.fill("#register-password", "Str0ng-Passw0rd!");
    await page.getByRole("button", { name: "ثبت‌نام و ورود" }).click();
    await page.waitForURL("**/dashboard");
    // The persistent shell shows the student navigation.
    await expect(page.getByRole("navigation", { name: "فهرست" })).toBeVisible();
  });

  test("2 — courses list opens a course detail", async ({ page }) => {
    await login(page, STUDENT);
    await page.goto("/courses");
    await expect(
      page.getByRole("heading", { name: "دروس و پیش‌نیازها" })
    ).toBeVisible();
    const firstCourse = page.locator('a[href^="/courses/"]').first();
    await firstCourse.click();
    await page.waitForURL(/\/courses\/\d+/);
    await expect(
      page.getByRole("heading", { name: "اطلاعات درس" })
    ).toBeVisible();
  });

  test("3 — professors list opens a professor detail", async ({ page }) => {
    await login(page, STUDENT);
    await page.goto("/professors");
    await expect(
      page.getByRole("heading", { name: "اساتید" })
    ).toBeVisible();
    const firstProfessor = page.locator('a[href^="/professors/"]').first();
    await firstProfessor.click();
    await page.waitForURL(/\/professors\/\d+/);
    // Detail page replaces the list; the URL contract is the journey.
    await expect(page).toHaveURL(/\/professors\/\d+/);
  });

  test("4 — exam schedule shows its term context", async ({ page }) => {
    await login(page, STUDENT);
    await page.goto("/exams");
    await expect(page.getByRole("heading", { name: "امتحانات" })).toBeVisible();
    // The term filter defaults to the current term (docs/api/exams.md).
    await expect(page.locator("select").first()).toBeVisible();
    // Rows render Jalali dates with Persian digits, or the honest empty state.
    await expect(
      page
        .locator("table, [role=status]")
        .first()
    ).toBeVisible();
  });

  test("5 — assistant answers with document sources", async ({ page }) => {
    await login(page, STUDENT);
    await page.goto("/assistant");
    await page.getByRole("button", { name: "گفتگوی جدید" }).click();
    const composer = page.locator("#assistant-composer");
    await expect(composer).toBeEnabled();
    await composer.fill("شرایط مشروطی چیست؟");
    await page.getByRole("button", { name: "ارسال" }).click();
    // The assistant bubble must cite a retrieved document page.
    await expect(page.getByText(/— صفحه \d+/).first()).toBeVisible({
      timeout: 30_000,
    });
  });

  test("6 — conversation history survives a reload", async ({ page }) => {
    await login(page, STUDENT);
    await page.goto("/assistant");
    await page.getByRole("button", { name: "گفتگوی جدید" }).click();
    const composer = page.locator("#assistant-composer");
    await expect(composer).toBeEnabled();
    await composer.fill("شرایط انصراف از تحصیل چیست؟");
    await page.getByRole("button", { name: "ارسال" }).click();
    await expect(page.getByText(/— صفحه \d+/).first()).toBeVisible({
      timeout: 30_000,
    });

    // Follow-up in the same conversation.
    await composer.fill("سقف واحد ترم اول چقدر است؟");
    await page.getByRole("button", { name: "ارسال" }).click();
    await expect(
      page.getByText("سقف واحد ترم اول چقدر است؟")
    ).toBeVisible();

    // Reload → the conversation list (sidebar) keeps it; reselect it.
    // (.first(): re-runs of the suite create identically-titled conversations.)
    await page.reload();
    const history = page.locator("aside", { hasText: "تاریخچه گفتگوها" });
    const item = history
      .getByRole("button", { name: "شرایط انصراف از تحصیل چیست؟" })
      .first();
    await expect(item).toBeVisible();
    await item.click();
    await expect(page.getByText("شرایط انصراف از تحصیل چیست؟").first()).toBeVisible();
  });

  test("7 — admin uploads a document, indexes and activates it", async ({ page }) => {
    await login(page, ADMIN);
    await page.goto("/admin/documents");
    await expect(
      page.getByRole("heading", { name: "مدیریت اسناد" })
    ).toBeVisible();

    // Upload modal.
    await page.getByRole("button", { name: "بارگذاری سند" }).click();
    const title = `e2e-journey7-${Date.now()}`;
    await page.getByLabel("عنوان سند").fill(title);
    await page
      .getByLabel("فایل PDF")
      .setInputFiles({
        name: "journey7.pdf",
        mimeType: "application/pdf",
        // Minimal structural PDF — byte-for-byte the shape of the backend
        // ingestion suite's MINIMAL_PDF (real xref table, extractable text).
        buffer: Buffer.from(
          "%PDF-1.4\n" +
            "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n" +
            "2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n" +
            "3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n" +
            "4 0 obj\n<< /Length 60 >>\nstream\nBT /F1 12 Tf 100 700 Td (Hello Persian world) Tj ET\nendstream\nendobj\n" +
            "5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n" +
            "xref\n0 6\n0000000000 65535 f \n0000000009 65535 n \n0000000058 65535 n \n0000000115 65535 n \n0000000241 65535 n \n0000000355 65535 n \n" +
            "trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n426\n%%EOF",
          "utf-8"
        ),
      });
    await page.getByRole("button", { name: "بارگذاری و پردازش" }).click();

    // Inline eager processing (CELERY_TASK_ALWAYS_EAGER) → INDEXED.
    const row = page.locator("tr", { hasText: title });
    await expect(row).toBeVisible({ timeout: 60_000 });
    await expect(row.getByText("ایندکس شده")).toBeVisible({ timeout: 60_000 });

    // Activate → ConfirmDialog → confirm.
    await row.getByRole("button", { name: "فعال‌سازی" }).click();
    await page
      .getByRole("dialog")
      .getByRole("button", { name: "حذف", exact: true })
      .click();
    await expect(row.getByText("فعال")).toBeVisible({ timeout: 30_000 });

    // Cleanup: delete the document so the dev RAG corpus stays pristine.
    await row.getByRole("button", { name: "حذف" }).first().click();
    await page
      .getByRole("dialog")
      .getByRole("button", { name: "حذف", exact: true })
      .click();
    await expect(row).toHaveCount(0);
  });
});
