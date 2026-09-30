/**
 * Phase 00 baseline shell — intentionally not a feature screen.
 *
 * Phase 00 non-goals forbid UI implementation; this placeholder only proves the
 * React + TypeScript build pipeline works and that the document renders in RTL
 * as required by docs/20-ui-navigation.md. Real screens (routes in
 * docs/20-ui-navigation.md) arrive in later phases.
 */
export function App() {
  return (
    <main style={{ fontFamily: 'system-ui', padding: '2rem' }}>
      <h1>دستیار هوشمند دانشگاه</h1>
      <p>
        اسکلت پایهٔ فرانت‌اند ساخته شده است. رابط کاربری در فازهای بعدی پیاده‌سازی
        می‌شود.
      </p>
    </main>
  )
}
