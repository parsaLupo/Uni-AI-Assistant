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
  selection: 'انتخاب درس',
  notifications: 'یادآوری‌ها',
  profile: 'پروفایل دانشجویی',
  admin: 'مدیریت',
  adminOverview: 'نمای کلی مدیریت',
  adminSoon: 'در فاز ۱۳ فعال می‌شود',
  menu: 'فهرست',
  closeMenu: 'بستن فهرست',
} as const

export const selectionPage = {
  title: 'دستیار انتخاب واحد',
  subtitle:
    'بررسی قطعی شرایط برداشتن هر درس بر پایه پیش‌نیاز، ارائه ترم جاری، سقف واحد و برنامه فعلی شما.',
  courseCodeLabel: 'کد درس',
  courseCodePlaceholder: 'مثلاً 1916003',
  extrasLabel: 'درس‌های فرضی (اختیاری)',
  extrasPlaceholder: 'مثلاً 1916001، 1916002',
  extrasHint: 'برای محاسبه «اگر این درس‌ها را هم بردارم»، کدها را با کاما جدا کنید.',
  check: 'بررسی کنم',
  checking: 'در حال بررسی…',
  eligibleBadge: 'مجاز',
  ineligibleBadge: 'غیرمجاز',
  creditUnit: 'واحد',
  termLabel: 'ترم',
  resultAria: 'نتیجه بررسی انتخاب درس',
  explanationTitle: 'توضیح',
  reasonsTitle: 'دلایل تأیید نشدن',
  totalsTitle: 'جمع واحدهای ترم',
  totalsPlanned: 'واحدهای برنامه فعلی',
  totalsCandidate: 'این درس',
  totalsExtra: 'درس‌های فرضی',
  totalsTotal: 'جمع با درس‌های فرضی',
  totalsLimit: 'سقف مجاز ترم',
  overLimit: 'بیشتر از سقف مجاز',
  engineLabel: 'نسخه موتور قواعد',
  emptyHint:
    'کد درس را وارد کنید و «بررسی کنم» را بزنید؛ نتیجه مستقیماً از موتور قاعده‌محور سامانه می‌آید.',
} as const

export const notificationsPage = {
  title: 'یادآوری‌ها',
  subtitle: 'اطلاعیه‌های منتشرشده برای شما و یادآوری‌های سامانه، همیشه به‌روز.',
  unreadOnly: 'فقط ناخوانده‌ها',
  markAllRead: 'علامت‌گذاری همه به‌عنوان خوانده‌شده',
  markRead: 'خواندم',
  unreadBadge: 'ناخوانده',
  typeAnnouncement: 'اطلاعیه',
  typeDeadline: 'مهلت',
  typeExam: 'امتحان',
  typeSystem: 'سیستمی',
  empty: 'یادآوری فعالی ندارید.',
  emptyHint: 'اطلاعیه‌ها و یادآوری‌های سامانه به‌محض انتشار خودکار همین‌جا ظاهر می‌شوند.',
  expiresAt: 'انقضا',
  noExpiry: 'بدون انقضا',
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
  clearFilters: 'پاک کردن فیلترها',
  statusLabel: 'وضعیت',
  notSetFallback: '—',
  // Phase 13 — shared admin CRUD furniture
  create: 'افزودن',
  edit: 'ویرایش',
  remove: 'حذف',
  save: 'ذخیره',
  cancel: 'انصراف',
  closeDialog: 'بستن پنجره',
  confirmDelete: 'حذف',
  confirmDeleteTitle: 'تأیید حذف',
  confirmDeleteBody: 'این عملیات قابل بازگردانی نیست؛ برای ادامه تأیید کنید.',
  requiredField: 'این فیلد الزامی است.',
  invalidNumber: 'عدد معتبر وارد کنید.',
  saving: 'در حال ذخیره…',
  created: 'با موفقیت ثبت شد.',
  updated: 'تغییرات ذخیره شد.',
  deleted: 'با موفقیت حذف شد.',
  active: 'فعال',
  inactive: 'غیرفعال',
  activeAll: 'همه',
  actions: 'عملیات',
  publishedAt: 'تاریخ انتشار',
  expiresAt: 'تاریخ انقضا',
  audience: 'مخاطب',
  priority: 'اولویت',
  titleField: 'عنوان',
  bodyField: 'متن',
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
  examNotAnnounced: 'تاریخ امتحان اعلام نشده است',
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
  credits: 'واحد',
  creditsAll: 'همه واحدها',
  courseTypeAll: 'همه انواع',
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
  departmentAll: 'همه گروه‌ها',
  emptyHint: 'عبارت جستجو را کوتاه‌تر کنید یا فیلترهای واحد/نوع درس را بردارید.',
  noOfferingsHint: 'ترم دیگری را انتخاب کنید یا بعداً دوباره سر بزنید.',
  offeringsHint: 'زمان کلاس و امتحان هر ارائه در همین جدول آمده است.',
  resultsSummary: 'درس یافت شد',
  termAll: 'همه ترم‌ها',
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
  term: 'ترم',
  termAll: 'همه‌الترم‌ها',
  department: 'گروه آموزشی',
  departmentAll: 'همه‌گروه‌ها',
  emptyHint: 'نام استاد را کوتاه‌تر کنید یا فیلتر ترم/گروه را بردارید.',
  departmentRequired: 'برای نمایش اساتید، ابتدا گروه آموزشی خود را در پروفایل تکمیل کنید.',
  departmentRequiredHint: 'فهرست اساتید بر اساس گروه آموزشی ثبت‌شده در پروفایل شما نمایش داده می‌شود.',
  offerings: 'ارائه‌های استاد',
  noOfferings: 'برای این استاد در ترم انتخاب‌شده ارائه‌ای ثبت نشده است.',
  schedule: 'زمان',
} as const

export const calendarPage = {
  title: 'تقویم آموزشی',
  subtitle: 'رویدادهای ثبت‌نام، امتحانات و مناسبت‌های آموزشی',
  empty: 'رویدادی برای نمایش وجود ندارد.',
  eventType: 'نوع رویداد',
  from: 'از',
  to: 'تا',
  allTypes: 'همه انواع',
  emptyHint: 'ترم یا نوع رویداد دیگری را انتخاب کنید.',
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
  term: 'ترم',
  termCurrent: 'ترم جاری',
  termAll: 'همه‌الترم‌ها',
  course: 'درس',
  section: 'گروه',
  courseCode: 'کد درس',
  courseCodePlaceholder: 'مثلاً ۱۹۱۶۰۰۱',
  onlyMine: 'فقط امتحانات دروس من',
  studentNote: 'نمایش فقط امتحانات دروس شما',
  emptyHint: 'ترم دیگری را انتخاب کنید، کد درس را بردارید یا «فقط دروس من» را خاموش کنید.',
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
  emptyHint: 'ترم دیگری را انتخاب کنید یا چند دقیقه بعد دوباره سر بزنید.',
} as const

export const profilePage = {
  title: 'پروفایل دانشجویی',
  subtitle: 'مشخصات تحصیلی شما',
  readOnlyNotice:
    'اطلاعات تحصیلی توسط مدیریت آموزشی ثبت می‌شود و برای دانشجو فقط‌خواندنی است.',
  incompleteNotice:
    'اطلاعات تحصیلی شما توسط مدیریت آموزشی ثبت می‌شود؛ برای تکمیل پروفایل با مدیریت تماس بگیرید.',
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
  changePasswordTitle: 'تغییر گذرواژه',
  changePasswordHint: 'برای امنیت حساب، گذرواژهٔ قوی و یکتا انتخاب کنید.',
  currentPassword: 'گذرواژهٔ فعلی',
  newPassword: 'گذرواژه جدید',
  confirmNewPassword: 'تکرار گذرواژه جدید',
  passwordChanged: 'گذرواژه با موفقیت تغییر کرد.',
  passwordMismatch: 'تکرار گذرواژه با گذرواژه جدید یکسان نیست.',
  passwordShort: 'گذرواژه حداقل ۸ نویسه است.',
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
  welcome: 'خوش آمدید',
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
  // Phase 13 — analytics dashboard (all values aggregate-only, Persian UI)
  analyticsTitle: 'تحلیل و آمار',
  analyticsSubtitle: 'شاخص‌های واقعی استفاده از سامانه؛ فقط داده تجمعی، بدون متن گفتگوها',
  activeUsers: 'کاربران فعال',
  recentlyActive: 'فعال در ۷ روز اخیر',
  questionsTotal: 'پرسش‌های هوشمند',
  questionsLast7Days: 'پرسش در ۷ روز اخیر',
  answersTotal: 'پاسخ‌های تولیدشده',
  insufficientEvidence: 'پاسخ‌های با شواهد ناکافی',
  aiRequests: 'درخواست‌های هوش مصنوعی',
  aiErrors: 'خطاهای هوش مصنوعی',
  avgLatency: 'میانگین تأخیر (میلی‌ثانیه)',
  topicDistribution: 'توزیع حالت پاسخ (موضوع پرسش‌ها)',
  topDocuments: 'پرتکرارترین اسناد دانش‌پشتیبان',
  documentsTotal: 'اسناد موجود',
  citationCount: 'تعداد ارجاع',
  mostUsed: 'پرتکرارترین',
  roleCounts: 'کاربران بر پایه نقش',
  auditLogTitle: 'گزارش حسابرسی',
  auditLogSubtitle: 'گزارش فقط-خواندنی اقدامات مدیریتی (منبع افزودنی)',
  auditEntity: 'موجودیت',
  auditAction: 'اقدام',
  auditActor: 'کاربر',
  auditAt: 'زمان',
  auditAllActions: 'همه اقدامات',
  auditCreate: 'ایجاد',
  auditUpdate: 'ویرایش',
  auditDelete: 'حذف',
  auditEmpty: 'رویداد حسابرسی‌ای ثبت نشده است.',
  documentColumn: 'سند',
  routingMode: 'حالت پاسخ',
  // UI refinement — administrator overview (all values from real endpoints)
  overviewSubtitle: 'نمای کلی وضعیت سامانه بر پایه داده‌های واقعی',
  systemStatus: 'وضعیت سامانه',
  systemActive: 'سامانه فعال',
  systemIssue: 'اختلال در سامانه',
  serviceStatusLabel: 'وضعیت سرویس',
  dbLatencyMs: 'میلی‌ثانیه',
  databaseLabel: 'پایگاه داده',
  databaseOk: 'فعال',
  databaseUnavailable: 'در دسترس نیست',
  aiProviderLabel: 'سرویس هوش مصنوعی',
  aiProviderNotConfigured: 'پیکربندی نشده',
  activeDocuments: 'اسناد فعال',
  errorsShort: 'خطاها',
  recentActivities: 'آخرین اقدامات مدیریتی',
  recentActivitiesHint: 'رویدادهای اخیر گزارش حسابرسی',
  viewAllAudit: 'مشاهده همه',
  failedDocsWarningTitle: 'اسناد ناموفق در پردازش',
  failedDocsWarningBody:
    'سند در خط پردازش ناموفق بوده است؛ از صفحه اسناد، تلاش مجدد یا بررسی خطا را انجام دهید.',
} as const

/* ---------------------------------------------------------------------------
 * Phase 13 — admin management screens (docs/api/admin.md CRUD surfaces).
 * ------------------------------------------------------------------------- */

export const adminUsersPage = {
  title: 'مدیریت کاربران',
  subtitle: 'حساب‌ها، نقش‌ها و وضعیت دسترسی',
  searchPlaceholder: 'جستجوی ایمیل یا نام…',
  colEmail: 'ایمیل',
  colName: 'نام و نام خانوادگی',
  colRole: 'نقش',
  colActive: 'وضعیت',
  filterRole: 'نقش',
  filterState: 'وضعیت حساب',
  stateAll: 'همه',
  stateActive: 'فعال',
  stateInactive: 'غیرفعال',
  createTitle: 'افزودن کاربر',
  editTitle: 'ویرایش کاربر',
  selectRole: 'انتخاب نقش…',
  selectRoleRequired: 'نقش کاربر را انتخاب کنید.',
  password: 'گذرواژه',
  passwordHint: 'حداقل طبق سیاست گذرواژهٔ سامانه؛ پس از ثبت قابل مشاهده نیست.',
  roleHint:
    'ایجاد کاربر ADMIN/SUPERADMIN یا تغییر نقش به نقش‌های مدیریتی فقط با حساب SUPERADMIN ممکن است.',
  roleDeniedNotice: 'برای این تغییر نقش، حساب شما باید سطح دسترسی کافی داشته باشد.',
  deactivateTitle: 'غیرفعال‌سازی حساب',
  deactivateBody:
    'با غیرفعال‌سازی، ورود این کاربر مسدود می‌شود و ردیف حساب باقی می‌ماند (حذف نرم).',
  deactivateSelf: 'حساب خودتان؛ غیرفعال‌سازی مجاز نیست.',
  empty: 'کاربری با این جستجو یافت نشد.',
  emptyHint: 'فیلتر نقش یا وضعیت را تغییر دهید یا با «افزودن کاربر» حساب بسازید.',
  studentSection: 'اطلاعات تحصیلی دانشجو',
  studentNumber: 'کد دانشجویی',
  studentDepartment: 'رشته تحصیلی / گروه آموزشی',
  studentDegreeLevel: 'مقطع تحصیلی',
  studentEntryYear: 'سال ورود',
  studentEntryYearHint:
    'سال ورود، نسخهٔ برنامهٔ درسی و قواعد پیش‌نیاز دانشجو را تعیین می‌کند.',
  passedCourses: 'دروس پاس‌شده',
  passedCoursesHint:
    'برای هر درس انتخاب‌شده، یک سابقهٔ تحصیلی تاریخی با وضعیت «پاس‌شده» ثبت می‌شود.',
  currentCourses: 'دروس اخذ‌شده ترم جاری',
  currentCoursesHint:
    'فقط ارائه‌های واقعی ترم جاریِ رشتهٔ انتخاب‌شده نمایش داده می‌شود؛ دروس پاس‌شده حذف می‌شوند.',
  searchCoursePlaceholder: 'جستجوی کد یا نام درس…',
  noCourseOptions: 'درسی برای نمایش نیست.',
  noOfferingOptions: 'ارائه‌ای از این رشته در ترم جاری ثبت نشده است.',
  selectedCourses: 'انتخاب‌شده‌ها',
  clearSelection: 'حذف همه',
  creditsUnit: 'واحد',
  groupUnit: 'گروه',
  loadingOptions: 'در حال بارگذاری…',
  pickDepartmentFirst: 'ابتدا رشته تحصیلی را انتخاب کنید.',
  studentNumberRequired: 'کد دانشجویی الزامی است.',
  departmentRequired: 'رشته تحصیلی الزامی است.',
  degreeLevelRequired: 'مقطع تحصیلی الزامی است.',
  entryYearRequired: 'سال ورود الزامی است.',
  invalidEntryYear: 'سال ورود باید عدد ۴ رقمی باشد.',
} as const

export const adminCoursesPage = {
  title: 'مدیریت دروس',
  subtitle: 'دروس، پیش‌نیازها و ارائه‌های آموزشی',
  searchPlaceholder: 'جستجوی کد یا نام درس…',
  colCode: 'کد درس',
  colTitle: 'نام درس',
  colCredits: 'واحد',
  colDepartment: 'گروه',
  colState: 'وضعیت',
  filterDepartment: 'گروه آموزشی',
  departmentAll: 'همه گروه‌ها',
  createTitle: 'افزودن درس',
  editTitle: 'ویرایش درس',
  courseCode: 'کد درس',
  courseTitle: 'نام درس',
  units: 'تعداد واحد',
  unitsRange: 'بین ۱ تا ۲۰ واحد',
  courseType: 'نوع درس (اختیاری)',
  departmentField: 'گروه آموزشی',
  isActive: 'درس فعال',
  prereqHeading: 'پیش‌نیازهای درس',
  prereqAdd: 'افزودن پیش‌نیاز',
  prereqSelect: 'درس پیش‌نیاز',
  prereqSelf: 'یک درس نمی‌تواند پیش‌نیاز خودش باشد.',
  prereqAddedToast: 'پیش‌نیاز افزوده شد.',
  prereqEmpty: 'پیش‌نیاز ثبت نشده است.',
  offeringsHeading: 'ارائه‌های این درس',
  offeringAdd: 'افزودن ارائه',
  offeringTerm: 'ترم',
  offeringProfessor: 'استاد',
  offeringProfessorNone: 'بدون استاد',
  offeringSection: 'شماره گروه',
  offeringCapacity: 'ظرفیت',
  offeringStatus: 'وضعیت ارائه',
  offeringEnrolled: 'ثبت‌نام‌شده',
  scheduleHeading: 'زمان‌های کلاس',
  scheduleAdd: 'افزودن زمان',
  scheduleWeekday: 'روز هفته',
  scheduleStart: 'شروع',
  scheduleEnd: 'پایان',
  scheduleTimeError: 'ساعت پایان باید بعد از ساعت شروع باشد.',
  scheduleClassroom: 'کلاس (اختیاری)',
  scheduleEmpty: 'زمان کلاسی ثبت نشده است.',
  deleteCourseBody:
    'حذف درس فقط در صورتی ممکن است که ارائه‌ای نداشته باشد؛ در غیر این صورت درس را غیرفعال کنید.',
  deleteOfferingBody: 'ارائه و زمان‌های کلاس آن حذف می‌شود؛ در مورد ترم گذشته مجاز نیست.',
  empty: 'درسی با این جستجو یافت نشد.',
  emptyHint: 'جستجو را کوتاه‌تر کنید یا فیلتر گروه را بردارید، یا درس تازه ثبت کنید.',
} as const

export const adminProfessorsPage = {
  title: 'مدیریت اساتید',
  subtitle: 'هیئت علمی گروه‌های آموزشی',
  searchPlaceholder: 'جستجوی نام استاد…',
  colName: 'نام و نام خانوادگی',
  colTitle: 'مرتبه علمی',
  colDepartment: 'گروه',
  colEmail: 'ایمیل',
  filterDepartment: 'گروه آموزشی',
  departmentAll: 'همه گروه‌ها',
  firstName: 'نام',
  lastName: 'نام خانوادگی',
  academicTitle: 'مرتبه علمی (اختیاری)',
  emailField: 'ایمیل (اختیاری)',
  office: 'دفتر (اختیاری)',
  website: 'وب‌گاه (اختیاری)',
  bio: 'معرفی (اختیاری)',
  isActive: 'استاد فعال',
  createTitle: 'افزودن استاد',
  editTitle: 'ویرایش استاد',
  deleteBody: 'اطلاعات این استاد از فهرست حذف می‌شود.',
  empty: 'استادی با این جستجو یافت نشد.',
  emptyHint: 'فیلتر گروه را بردارید یا استاد تازه ثبت کنید.',
} as const

export const adminTermsPage = {
  title: 'مدیریت ترم‌های آموزشی',
  subtitle: 'نیمسال‌ها و ترم جاری سامانه',
  colName: 'ترم',
  colYear: 'سال تحصیلی',
  colSemester: 'نیمسال',
  colDates: 'بازه',
  colCurrent: 'جاری',
  nameField: 'نام ترم',
  namePlaceholder: 'مثلاً ترم اول ۱۴۰۵-۱۴۰۶',
  academicYear: 'سال تحصیلی',
  yearPlaceholder: 'مثلاً ۱۴۰۵-۱۴۰۶',
  semesterType: 'نیمسال',
  startsAt: 'تاریخ شروع',
  endsAt: 'تاریخ پایان',
  datesOrder: 'تاریخ شروع باید قبل از تاریخ پایان باشد.',
  isCurrent: 'ترم جاری',
  isCurrentHint:
    'در هر لحظه فقط یک ترم جاری مجاز است؛ ابتدا ترم فعلی را از حالت جاری خارج کنید.',
  currentChip: 'ترم جاری',
  pastHint: 'ترم گذشته تاریخی است و قابل ویرایش نیست.',
  deleteNotSupported: 'حذف ترم از طریق سامانه انجام نمی‌شود (منع قراردادی).',
  createTitle: 'افزودن ترم',
  editTitle: 'ویرایش ترم',
  empty: 'ترمی ثبت نشده است.',
  emptyHint: 'با «افزودن ترم» نیمسال آموزشی بسازید.',
} as const

export const adminExamsPage = {
  title: 'مدیریت امتحانات',
  subtitle: 'زمان‌بندی امتحان هر ارائه و ثبت یا ویرایش آن',
  colCourse: 'درس',
  colSection: 'گروه',
  colTerm: 'ترم',
  colDate: 'تاریخ امتحان',
  colTime: 'ساعت',
  colClassroom: 'سالن',
  colStatus: 'وضعیت',
  filterTerm: 'ترم',
  createTitle: 'ثبت امتحان برای ارائه',
  editTitle: 'ویرایش امتحان',
  offeringSelect: 'ارائه درس',
  offeringHint: 'ابتدا ترم را انتخاب کنید سپس ارائه را برگزینید؛ هر ارائه فقط یک امتحان دارد.',
  configure: 'ثبت/ویرایش امتحان',
  startsAt: 'شروع امتحان',
  endsAt: 'پایان امتحان',
  classroom: 'سالن (اختیاری)',
  timeOrder: 'ساعت پایان باید بعد از شروع باشد.',
  pickOffering: 'برای ذخیره، ارائه را انتخاب کنید.',
  historicalNotice: 'امتحان ترم گذشته تاریخی است و قابل تغییر نیست.',
  saveNew: 'ثبت امتحان',
  saveExisting: 'ذخیره تغییرات',
  examExists: 'برای این ارائه امتحان ثبت شده است؛ ویرایش می‌کنید.',
  statusScheduled: 'زمان‌بندی‌شده',
  statusChanged: 'تغییریافته',
  statusCancelled: 'لغوشده',
  empty: 'امتحانی برای این فیلتر ثبت نشده است.',
  emptyHint: 'ترم دیگری را انتخاب کنید یا با «ثبت امتحان برای ارائه» زمان‌بندی بسازید.',
} as const

export const adminDocumentsPage = {
  title: 'مدیریت اسناد',
  subtitle: 'بارگذاری، پردازش و چرخهٔ عمر اسناد رسمی',
  uploadTitle: 'بارگذاری سند',
  colTitle: 'سند',
  colType: 'نوع',
  colYear: 'سال',
  colVersion: 'نسخه',
  colStatus: 'وضعیت',
  colUploaded: 'بارگذاری',
  filterStatus: 'وضعیت',
  filterType: 'نوع سند',
  typeAll: 'همه انواع',
  yearPlaceholder: 'سال تحصیلی (اختیاری)',
  titleField: 'عنوان سند',
  documentType: 'نوع سند (اختیاری)',
  academicYear: 'سال تحصیلی (اختیاری)',
  effectiveFrom: 'تاریخ اثرگذاری از (اختیاری)',
  effectiveTo: 'تاریخ اثرگذاری تا (اختیاری)',
  fileField: 'فایل PDF',
  fileHint: 'فقط PDF، حداکثر ۱۰ مگابایت.',
  uploadSubmit: 'بارگذاری و پردازش',
  uploading: 'در حال بارگذاری…',
  statusChange: 'تغییر وضعیت',
  activate: 'فعال‌سازی',
  activateBody: 'این نسخه فعال می‌شود و نسخه فعال قبلی همان سند «جایگزین‌شده» می‌گردد.',
  retry: 'تلاش مجدد پردازش',
  editTitle: 'ویرایش سند',
  processingError: 'خطای پردازش',
  attempts: 'تلاش‌ها',
  empty: 'سندی یافت نشد.',
  emptyHint: 'سند رسمی را با «بارگذاری سند» اضافه کنید.',
  versionOf: 'نسخه',
} as const

export const adminAnnouncementsPage = {
  title: 'مدیریت اطلاعیه‌ها',
  subtitle: 'انتشار اطلاعیه‌ها برای دانشجویان با هدف‌گیری دانشکده/گروه',
  createTitle: 'اطلاعیه جدید',
  editTitle: 'ویرایش اطلاعیه',
  titleField: 'عنوان',
  bodyField: 'متن اطلاعیه',
  priorityField: 'اولویت',
  termField: 'ترم (اختیاری)',
  audienceFaculty: 'مخاطب دانشکده (اختیاری)',
  audienceDepartment: 'مخاطب گروه (اختیاری)',
  audienceHint: 'خالی بودن هر دو یعنی اطلاعیه برای همه دانشجویان.',
  expiresHint: 'پس از انقضا، اطلاعیه از نمایش عمومی حذف می‌شود.',
  isPublished: 'منتشر شده',
  publishNotice:
    'انتشار یا انتشار مجدد، یادآوری اطلاعیه را برای دانشجویان واجد شرایط می‌فرستد.',
  colPublished: 'انتشار',
  colAudience: 'مخاطب',
  colPriority: 'اولویت',
  colExpires: 'انقضا',
  audienceEveryone: 'همه',
  deleteBody: 'اطلاعیه حذف می‌شود؛ یادآوری‌های ارسال‌شده حذف نمی‌شوند.',
  empty: 'اطلاعیه‌ای ثبت نشده است.',
  emptyHint: 'با «اطلاعیه جدید» نخستین اطلاعیه را بسازید.',
  filterState: 'وضعیت انتشار',
  statePublished: 'منتشرشده',
  stateDraft: 'پیش‌نویس',
} as const