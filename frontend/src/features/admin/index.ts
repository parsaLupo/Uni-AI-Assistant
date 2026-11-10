/**
 * Admin feature barrel (docs/20 admin route group).
 *
 * `ADMIN_LINKS` lives in `links.ts` (not here) so the router, the overview and
 * the barrel can all import it without a circular import. Every management
 * section is a real Phase 13 CRUD screen backed by `api/admin.ts`.
 */

import { AdminAnalyticsPage } from './AdminAnalyticsPage'
import { AdminAnnouncementsPage } from './AdminAnnouncementsPage'
import { AdminCoursesPage } from './AdminCoursesPage'
import { AdminDocumentsPage } from './AdminDocumentsPage'
import { AdminExamsPage } from './AdminExamsPage'
import { AdminOverviewPage } from './AdminOverviewPage'
import { AdminProfessorsPage } from './AdminProfessorsPage'
import { AdminTermsPage } from './AdminTermsPage'
import { AdminUsersPage } from './AdminUsersPage'

export { ADMIN_LINKS, type AdminLink } from './links'
export {
  AdminAnalyticsPage,
  AdminAnnouncementsPage,
  AdminCoursesPage,
  AdminDocumentsPage,
  AdminExamsPage,
  AdminOverviewPage,
  AdminProfessorsPage,
  AdminTermsPage,
  AdminUsersPage,
}
