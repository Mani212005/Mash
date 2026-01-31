import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Sidebar } from '@/components/layout/sidebar';
import { Header } from '@/components/layout/header';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Mash Voice - AI Customer Service Platform',
  description: 'Modular Full-Stack Voice Agent Platform with WhatsApp Integration',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <div className="flex h-screen bg-background">
          {/* Sidebar */}
          <Sidebar />
          
          {/* Main content area */}
          <div className="flex flex-col flex-1 overflow-hidden">
            {/* Header */}
            <Header />
            
            {/* Page content */}
            <main className="flex-1 overflow-auto p-6">
              {children}
            </main>
          </div>
        </div>
      </body>
    </html>
  );
}
