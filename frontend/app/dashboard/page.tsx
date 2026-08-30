import { Suspense } from 'react';
import DashboardClient from './DashboardClient';

export default function DashboardPage() {
  return (
    <Suspense fallback={<p className="text-[var(--muted)]">Loading dashboard…</p>}>
      <DashboardClient />
    </Suspense>
  );
}
