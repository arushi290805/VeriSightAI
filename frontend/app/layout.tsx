import { Source_Sans_3, Fraunces } from 'next/font/google'
import './globals.css'
import type { Metadata } from 'next'

const sans = Source_Sans_3({
  subsets: ['latin'],
  variable: '--font-sans',
  display: 'swap',
})

const serif = Fraunces({
  subsets: ['latin'],
  variable: '--font-serif',
  display: 'swap',
})

export const metadata: Metadata = {
  title: 'VeriSight AI',
  description: 'KPI intelligence-to-action engine',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={`${sans.variable} ${serif.variable}`}>
      <body>
        <header className="site-header">
          <div className="site-header-inner">
            <a href="/" className="brand">
              VeriSight
            </a>
            <nav className="nav-links">
              <a href="/">Projects</a>
              <a href="/dashboard">Dashboard</a>
              <a href="/upload">Upload</a>
            </nav>
          </div>
        </header>
        <main className="page-shell">{children}</main>
      </body>
    </html>
  )
}
