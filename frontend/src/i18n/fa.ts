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
  loginSubtitle: 'برای دسترسی به کارتابل دانشجویی خود وارد شوید.',
  registerSubtitle: 'حساب بسازید و بلافاصله وارد داشبورد شوید.',
  email: 'ایمیل دانشگاهی',
  emailPlaceholder: 'student@semnan.local',
  password: 'گذرواژه',
  firstName: 'نام',
  lastName: 'نام خانوادگی',
  submitLogin: 'ورود',
  submitRegister: 'ثبت‌نام و ورود',
  toRegister: 'حساب ندارید؟ ثبت‌نام کنید',
  toLogin: 'قبلاً ثبت‌نام کرده‌اید؟ وارد شوید',
  togglePassword: 'نمایش یا پنهان کردن گذرواژه',
  logout: 'خروج از حساب',
  welcome: 'خوش آمدید',
  dashboardNote: 'محتوای داشبورد در فاز ۰۶ پیاده‌سازی می‌شود.',
  sessionRestoring: 'در حال بازیابی نشست…',
  /* Decorative column beside the auth card (UI/Login.html), honest copy only:
     no CAS/SSO/TLS claims, because this system does not implement them. */
  heroBadge: 'زیرساخت داخلی دانشگاه | نگارش ۰٫۵٫۰',
  heroTitle: 'درگاه هوشمند اسناد و دانش دانشگاه',
  heroBody:
    'ورود امن دانشجویان و اساتید به کارتابل دروس، تقویم آموزشی، امتحانات و اطلاعیه‌های دانشگاه.',
  heroVisualTitle: 'کارتابل دانشگاهی یکپارچه',
  heroVisualBody: 'دروس، امتحانات و اطلاعیه‌ها در یک صفحه.',
  /* Real Phase 03 security properties — each one verifiable in ADR-014. */
  secTitle: 'الزامات امنیتی (فاز ۰۳)',
  secHashTitle: 'هشینگ رمزنگاری',
  secHashBody: 'Argon2id با نمک منحصر‌به‌فرد',
  secRateTitle: 'محدودساز تقاضا',
  secRateBody: 'حداکثر ۱۰ درخواست ورود در دقیقه',
  secSessionTitle: 'نشست مقاوم HttpOnly',
  secSessionBody: 'چرخش توکن refresh و ابطال خانوادهٔ نشست',
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

/* ---------------------------------------------------------------------------
 * Phase 05 — application shell, navigation and page copy.
 *
 * docs/20 requires Persian navigation/buttons/forms/empty/loading states; the
 * strings mirror the wording used in the UI mockups where a mockup covers the
 * element. Admin sub-features that arrive in Phase 13 say so honestly instead
 * of pretending to work (no mock data in production paths — docs/06 section 8).
 * ------------------------------------------------------------------------- */

export const nav = {
  brand: 'دستیار هوشمند دانشگاه',
  dashboard: 'داشبورد',
  assistant: 'دستیار هوشمند',
  courses: 'دروس و پیش‌نیازها',
  professors: 'اساتید',
  calendar: 'تقویم آموزشی',
  exams: 'امتحانات',
  announcements: 'اطلاعیه‌ها',
  profile: 'پروفایل دانشجویی',
  admin: 'مدیریت',
  adminOverview: 'نمای کلی مدیریت',
  adminSoon: 'در فاز ۱۳ فعال می‌شود',
  menu: 'فهرست',
  closeMenu: 'بستن فهرست',
} as const

export const shell = {
  footerStatus: 'متصل به سرور مرکزی دانشگاه | پایگاه دانش RAG به‌روز',
  footerVersion: 'نگارش ۰٫۵٫۰',
  footerDocs: 'مستندات آیین‌نامه‌ها',
  footerSupport: 'پشتیبانی فنی سامانه',
  roleStudent: 'دانشجو',
  roleProfessor: 'استاد',
  roleAdmin: 'مدیر',
  roleSuperadmin: 'مدیر ارشد',
} as const

export const common = {
  search: 'جستجو',
  searchPlaceholder: 'جستجو…',
  loading: 'در حال بارگذاری…',
  empty: 'موردی برای نمایش وجود ندارد.',
  retry: 'تلاش دوباره',
  back: 'بازگشت',
  errorTitle: 'خطا در دریافت اطلاعات',
  notFoundTitle: 'مورد درخواستی یافت نشد',
  notFoundBody: 'آدرس واردشده معتبر نیست یا مورد حذف شده است.',
  page: 'صفحه',
  prev: 'قبلی',
  next: 'بعدی',
  resultsCount: 'نتیجه',
  soon: 'به‌زودی',
  credits: 'واحد',
  viewDetails: 'مشاهده جزییات',
  filterTerm: 'ترم',
  filterAll: 'همه',
  filterCurrent: 'ترم جاری',
  statusLabel: 'وضعیت',
  notSetFallback: '—',
} as const

export const dashboard = {
  welcome: 'خوش آمدید',
  currentTermActive: 'ترم جاری فعال',
  noTerm: 'ترمی فعال نیست',
  studentNumber: 'شماره دانشجویی',
  facultyLabel: 'دانشکده',
  degreeLabel: 'مقطع',
  notSet: 'ثبت‌نشده',
  gpa: 'معدل کل',
  currentTermNumber: 'ترم جاری',
  notAvailable: '—',
  passedCredits: 'واحدهای گذرانده',
  enrolledCredits: 'واحدهای اخذ شده',
  creditCap: 'سقف مجاز: ۲۰ واحد',
  todayClasses: 'کلاس‌های امروز',
  todaySessions: 'جلسه حضوری',
  noTodayClasses: 'امروز کلاسی در برنامه شما نیست.',
  upcomingExams: 'امتحانات پیش‌رو',
  examCountUnit: 'آزمون پایان‌ترم',
  noExams: 'امتحانی برای نمایش وجود ندارد.',
  daysLeft: 'روز دیگر',
  today: 'امروز',
  academicStatus: 'وضعیت تحصیلی',
  statusNormal: 'عادی',
  statusNotSet: 'در انتظار تکمیل پروفایل',
  plannerEmpty: 'هنوز درسی به برنامه ترم اضافه نکرده‌اید.',
  todaySchedule: 'برنامه امروز',
  enrolledTableTitle: 'دروس انتخابی ترم',
  colCourse: 'کد و نام درس',
  colCredits: 'واحد',
  colProfessor: 'استاد',
  colSection: 'گروه',
  colActions: 'عملیات',
  examsTitle: 'امتحانات پایان‌ترم',
  announcementsTitle: 'آخرین اطلاعیه‌ها',
  assistantBannerTitle: 'دستیار هوشمند آیین‌نامه‌های آموزشی',
  assistantBannerBody:
    'سوال یا ابهامی درباره سقف مجاز انتخاب واحد، حذف اضطراری، یا تطبیق واحدها دارید؟',
  assistantBannerAction: 'پرسش از دستیار',
  profileIncomplete: 'پروفایل دانشجویی خود را تکمیل کنید.',
  completeProfile: 'تکمیل پروفایل',
} as const

export const coursesPage = {
  title: 'دروس و پیش‌نیازها',
  subtitle: 'راهنمای دروس، پیش‌نیازها و ارائه‌های ترم جاری',
  searchPlaceholder: 'جستجوی نام یا کد درس…',
  empty: 'درسی با این جستجو یافت نشد.',
  prerequisites: 'پیش‌نیازها',
  noPrerequisites: 'پیش‌نیازی ندارد.',
  courseInfo: 'اطلاعات درس',
  courseCode: 'کد درس',
  courseType: 'نوع درس',
  department: 'گروه آموزشی',
  active: 'فعال',
  inactive: 'غیرفعال',
  offerings: 'ارائه‌های این درس',
  noOfferings: 'برای این درس ارائه‌ای ثبت نشده است.',
  section: 'گروه',
  capacity: 'ظرفیت',
  enrolled: 'ثبت‌شده',
  professor: 'استاد',
  noProfessor: 'استاد ثبت‌نشده',
  schedule: 'زمان برگزاری',
  noSchedule: 'زمان ثبت‌نشده',
  exam: 'زمان امتحان',
  noExam: 'امتحان ثبت‌نشده',
  statusOpen: 'باز',
  statusClosed: 'بسته',
  statusCancelled: 'لغوشده',
  colCourse: 'درس',
  colCredits: 'واحد',
  colType: 'نوع',
  colActions: 'عملیات',
} as const

export const professorsPage = {
  title: 'اساتید',
  subtitle: 'هیئت علمی گروه‌های آموزشی',
  searchPlaceholder: 'جستجوی نام استاد…',
  empty: 'استادی با این جستجو یافت نشد.',
  office: 'دفتر',
  email: 'ایمیل',
  website: 'وب‌گاه',
  bio: 'معرفی',
  currentOfferings: 'ارائه‌های جاری',
  noCurrentOfferings: 'ارائه جاری برای این استاد ثبت نشده است.',
  backToList: 'بازگشت به فهرست اساتید',
} as const

export const calendarPage = {
  title: 'تقویم آموزشی',
  subtitle: 'رویدادهای ثبت‌نام، امتحانات و مناسبت‌های آموزشی',
  empty: 'رویدادی برای نمایش وجود ندارد.',
  eventType: 'نوع رویداد',
  from: 'از',
  to: 'تا',
  allTypes: 'همه انواع',
} as const

export const examsPage = {
  title: 'امتحانات',
  subtitle: 'برنامه امتحانات پایان‌ترم',
  empty: 'امتحانی برای نمایش وجود ندارد.',
  colExam: 'امتحان',
  colDate: 'تاریخ',
  colTime: 'ساعت',
  colClassroom: 'سالن',
  noClassroom: 'سالن ثبت‌نشده',
  daysLeft: 'روز مانده',
  today: 'امروز',
  past: 'برگزار شده',
  statusScheduled: 'زمان‌بندی‌شده',
  statusHeld: 'برگزارشده',
  statusCancelled: 'لغوشده',
} as const

export const announcementsPage = {
  title: 'اطلاعیه‌ها',
  subtitle: 'آخرین اطلاعیه‌های آموزشی',
  empty: 'اطلاعیه‌ای برای نمایش وجود ندارد.',
  priorityHigh: 'مهم',
  priorityNormal: 'عادی',
  publishedAt: 'تاریخ انتشار',
  expiresAt: 'انقضا',
  noExpiry: 'بدون تاریخ انقضا',
  audience: 'مخاطب',
  audienceAll: 'همه دانشجویان',
} as const

export const profilePage = {
  title: 'پروفایل دانشجویی',
  subtitle: 'مشخصات تحصیلی شما',
  edit: 'ویرایش مشخصات',
  save: 'ذخیره تغییرات',
  cancel: 'انصراف',
  saved: 'تغییرات با موفقیت ذخیره شد.',
  studentNumber: 'کد دانشجویی',
  department: 'رشته تحصیلی',
  faculty: 'دانشکده',
  degreeLevel: 'مقطع',
  entryYear: 'سال ورود',
  currentGpa: 'معدل جاری',
  currentTermNumber: 'ترم جاری (شماره)',
  notAvailable: '—',
  onboardingNotice:
    'برای استفاده از برنامه‌ریزی، ابتدا کد دانشجویی و رشته تحصیلی خود را ثبت کنید.',
  required: 'این فیلد الزامی است.',
  invalidYear: 'سال ورود باید عدد ۴ رقمی باشد.',
} as const

export const assistantPage = {
  title: 'دستیار هوشمند و آیین‌نامه‌ها',
  subtitle: 'پرسش و پاسخ بر اساس منابع رسمی دانشگاه',
  newChat: 'گفتگوی جدید',
  history: 'تاریخچه گفتگوها',
  noHistory: 'هنوز گفتگویی ندارید.',
  welcomeTitle: 'چطور می‌توانم کمک کنم؟',
  welcomeBody:
    'درباره دروس، پیش‌نیازها، آیین‌نامه‌ها و مقررات آموزشی بپرسید؛ پاسخ‌ها بر اساس منابع رسمی داده می‌شوند.',
  composerPlaceholder: 'سوال خود را بنویسید…',
  send: 'ارسال',
  notReadyTitle: 'سرویس گفتگو هنوز فعال نشده است',
  notReadyBody:
    'پشتیبان گفتگو (تاریخچه و پاسخ هوشمند) در فاز ۱۰ راه‌اندازی می‌شود؛ تا آن زمان پاسخ‌ها از همین صفحه در دسترس نیستند.',
  sending: 'در حال ارسال…',
} as const

export const adminPage = {
  title: 'نمای کلی مدیریت',
  subtitle: 'آمار زنده سامانه از داده‌های واقعی',
  kpiUsers: 'کاربران',
  kpiStudents: 'دانشجویان',
  kpiCourses: 'درس‌ها',
  kpiProfessors: 'اساتید',
  kpiTerms: 'ترم‌های آموزشی',
  kpiAnnouncements: 'اطلاعیه‌ها',
  kpiOfferings: 'ارائه‌های جاری',
  kpiEnrollments: 'ثبت‌نام‌ها',
  quickLinks: 'دسترسی سریع',
  liveCount: 'برگرفته از API واقعی',
  listAll: 'مشاهده فهرست',
  currentTermOnly: 'فقط ترم جاری',
  stubSection: 'بخش مدیریت داده',
  stubBody:
    'جدول مدیریتی این بخش روی APIهای نوشته‌شده پیاده می‌شود؛ آمار زنده و دسترسی سریع از نمای کلی مدیریت در دسترس است.',
} as const