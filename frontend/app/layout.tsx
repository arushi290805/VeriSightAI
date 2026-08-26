import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'BusinessIntelligence.ai',
  description: 'KPI intelligence-to-action engine',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-900 text-slate-50">
        <main className="container mx-auto p-4">
          <nav className="flex gap-4 mb-8 border-b border-slate-700 pb-4">
            <a href="/" className="hover:text-blue-400 font-bold">Dashboard</a>
            <a href="/upload" className="hover:text-blue-400">Upload Data</a>
          </nav>
          {children}
        </main>
      </body>
    </html>
  )
}
