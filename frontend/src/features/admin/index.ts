/**
 * Admin feature barrel (docs/20 admin route group).
 *
 * `ADMIN_LINKS` lives in `links.ts` (not here) so the router, the overview and
 * the barrel can all import it without a circular import.
 */

import { AdminOverviewPage } from './AdminOverviewPage'
import { AdminStubPage } from './AdminStubPage'

export { ADMIN_LINKS, type AdminLink } from './links'
export { AdminOverviewPage, AdminStubPage }

