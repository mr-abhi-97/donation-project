import type { Metadata } from 'next';
import './globals.css';
import Navbar from '@/components/Navbar';

export const metadata: Metadata = {
  title: 'Raise India - Automated Donation Reconciliation & 80G OCR Portal',
  description: 'Automated UPI QR code donation reconciliation, OCR receipt verification, and instant 80G tax certificate issuance portal for Raise India Foundation.',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full">
      <body className="min-h-full flex flex-col bg-slate-50 text-slate-900 antialiased selection:bg-emerald-500 selection:text-white">
        <Navbar />
        <main className="flex-1">
          {children}
        </main>
        <footer className="bg-white border-t border-slate-200 py-8 text-xs text-slate-500">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <span className="font-bold text-slate-800">Raise India Foundation</span>
              <span>• Registered Trust under Indian Trusts Act, 1882</span>
            </div>
            <div className="flex flex-wrap items-center gap-4">
              <span>Section 80G(5)(vi) Approved</span>
              <span>• Form 10BD Compliant</span>
              <span>• Automated UPI UTR Verification</span>
            </div>
            <div>
              <span>© {new Date().getFullYear()} Raise India Foundation. All rights reserved.</span>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
