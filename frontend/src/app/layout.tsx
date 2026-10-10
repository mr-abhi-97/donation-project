import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Raise India | VerifyAI Reconciliation Engine",
  description: "Automated UPI Payment Proof Forensics & Bank Statement Reconciler",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full" suppressHydrationWarning>
      <body
        className="min-h-full bg-slate-50 text-slate-900 antialiased selection:bg-indigo-600 selection:text-white"
        suppressHydrationWarning
      >
        {children}
      </body>
    </html>
  );
}
