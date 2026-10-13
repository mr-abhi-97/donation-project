import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Raise India Foundation - Donation Reconciliation & OCR Portal",
  description: "Automated UPI Payment Proof Forensics & Bank Statement Reconciler for Raise India Foundation",
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "any" },
      { url: "/icon.png", type: "image/png" },
    ],
    shortcut: "/favicon.ico",
    apple: "/icon.png",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full" suppressHydrationWarning>
      <head>
        <link rel="icon" href="/favicon.ico" sizes="any" />
        <link rel="icon" href="/icon.png" type="image/png" />
        <link rel="apple-touch-icon" href="/icon.png" />
      </head>
      <body
        className="min-h-full bg-slate-50 text-slate-900 antialiased selection:bg-indigo-600 selection:text-white"
        suppressHydrationWarning
      >
        {children}
      </body>
    </html>
  );
}

