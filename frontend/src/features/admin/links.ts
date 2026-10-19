/** The eight guarded admin sub-routes (docs/20 admin group).
 *  Single source for the router (App.tsx) and the overview quick-links.
 *  Titles are Persian product copy (AGENTS.md §8 → i18n/fa). */
export interface AdminLink {
  path: string
  title: string
}

export const ADMIN_LINKS: AdminLink[] = [
  { path: 'users', title: 'کاربران' },
  { path: 'courses', title: 'دروس' },
  { path: 'professors', title: 'اساتید' },
  { path: 'terms', title: 'ترم‌ها' },
  { path: 'exams', title: 'امتحانات' },
  { path: 'documents', title: 'اسناد' },
  { path: 'announcements', title: 'اطلاعیه‌ها' },
  { path: 'analytics', title: 'تحلیل و آمار' },
]
