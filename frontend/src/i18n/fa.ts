/**
 * Persian (fa-IR) user-facing strings.
 *
 * AGENTS.md ("Language & Localization") makes Persian the UI language and
 * `docs/20-ui-navigation.md` requires Persian navigation, buttons, forms,
 * notifications, error, empty and loading states. `docs/02-system-architecture.md`
 * additionally forbids scattering user-facing strings through components, so they
 * live here instead. No i18n package is added: AGENTS.md rule 10 blocks new
 * dependencies a phase does not need yet, and only one locale exists today
 * (see docs/21-open-assumptions.md, OA-21).
 *
 * API field names and error codes stay English on purpose (AGENTS.md allows
 * English for identifiers); only text shown to a human is translated.
 */

export const appShell = {
  title: 'دستیار هوشمند دانشگاه',
  baselineNote:
    'اسکلت پایهٔ فرانت‌اند ساخته شده است. رابط کاربری در فازهای بعدی پیاده‌سازی می‌شود.',
  loading: 'در حال بارگذاری…',
  empty: 'موردی برای نمایش وجود ندارد.',
  retry: 'تلاش دوباره',
} as const

/** Phase 03 authentication screens (docs/20-ui-navigation.md section 2). */
export const auth = {
  loginTitle: 'ورود به حساب',
  registerTitle: 'ساخت حساب دانشجویی',
  email: 'ایمیل دانشگاهی',
  password: 'گذرواژه',
  firstName: 'نام',
  lastName: 'نام خانوادگی',
  submitLogin: 'ورود',
  submitRegister: 'ثبت‌نام و ورود',
  toRegister: 'حساب ندارید؟ ثبت‌نام کنید',
  toLogin: 'قبلاً ثبت‌نام کرده‌اید؟ وارد شوید',
  logout: 'خروج از حساب',
  welcome: 'خوش آمدید',
  dashboardNote: 'محتوای داشبورد در فاز ۰۶ پیاده‌سازی می‌شود.',
  sessionRestoring: 'در حال بازیابی نشست…',
} as const

/**
 * Persian display text for the codes in docs/12-error-handling-observability.md
 * section 1. The UI branches on `error.code`, never on the raw server message
 * (docs/12 section 2), so this map is the presentation half of that contract.
 */
export const errorMessages: Record<string, string> = {
  VALIDATION_ERROR: 'اطلاعات واردشده معتبر نیست.',
  AUTHENTICATION_REQUIRED: 'برای ادامه باید وارد حساب خود شوید.',
  PERMISSION_DENIED: 'دسترسی شما به این بخش مجاز نیست.',
  NOT_FOUND: 'مورد درخواستی یافت نشد.',
  METHOD_NOT_ALLOWED: 'این عملیات برای این درخواست مجاز نیست.',
  REQUEST_FAILED: 'درخواست انجام نشد. لطفاً دوباره تلاش کنید.',
  CONFLICT: 'این عملیات با وضعیت فعلی داده‌ها تعارض دارد.',
  RATE_LIMITED: 'تعداد درخواست‌ها بیش از حد مجاز است؛ لطفاً کمی بعد تلاش کنید.',
  AI_PROVIDER_ERROR: 'سرویس هوش مصنوعی در حال حاضر در دسترس نیست.',
  RETRIEVAL_ERROR: 'بازیابی اطلاعات از منابع انجام نشد.',
  DOCUMENT_PROCESSING_ERROR: 'پردازش سند انجام نشد.',
  INTERNAL_ERROR: 'خطای غیرمنتظره‌ای رخ داد؛ لطفاً کمی بعد تلاش کنید.',
}

export const fallbackErrorMessage = 'خطای غیرمنتظره‌ای رخ داد؛ لطفاً کمی بعد تلاش کنید.'

const PERSIAN_SCRIPT = /[\u0600-\u06ff]/

export function isPersianText(value: string): boolean {
  return PERSIAN_SCRIPT.test(value)
}

/**
 * Text to show the user for a failed request.
 *
 * Prefers the stable code mapping, falls back to the server message only when it
 * is already Persian, and otherwise to the generic Persian sentence so the UI can
 * never display an English string.
 */
export function persianErrorText(code: string, serverMessage?: string): string {
  const mapped = errorMessages[code]
  if (mapped) {
    return mapped
  }
  if (serverMessage && isPersianText(serverMessage)) {
    return serverMessage
  }
  return fallbackErrorMessage
}