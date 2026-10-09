'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  HeartHandshake, 
  ScanLine, 
  FileCheck2, 
  Building2, 
  FileSpreadsheet, 
  ShieldCheck, 
  UploadCloud,
  CheckCircle2,
  TrendingUp
} from 'lucide-react';
import { api, ReconciliationStats } from '@/lib/api';

export default function Navbar() {
  const pathname = usePathname();
  const [stats, setStats] = useState<ReconciliationStats | null>(null);

  useEffect(() => {
    api.getReconciliationStats()
      .then(setStats)
      .catch(() => {});
  }, [pathname]);

  const navLinks = [
    { href: '/donate', label: 'Public Donor Portal', icon: HeartHandshake, badge: '80G Claim' },
    { href: '/admin/reconcile', label: 'Reconciliation Dashboard', icon: ScanLine },
    { href: '/admin/bulk-upload', label: 'Bulk OCR Upload', icon: UploadCloud },
    { href: '/admin/bank-statement', label: 'Bank Statements', icon: Building2 },
  ];

  return (
    <header className="sticky top-0 z-50 bg-white/90 dark:bg-slate-900/90 backdrop-blur-md border-b border-slate-200 dark:border-slate-800 shadow-xs">
      {/* Top NGO Compliance Banner */}
      <div className="bg-gradient-to-r from-emerald-700 via-teal-700 to-indigo-800 text-white text-xs px-4 py-1.5 font-medium">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="flex h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>Raise India Foundation • Regd. NGO under Sec 80G(5)(vi) Income Tax Act</span>
            <span className="hidden md:inline bg-emerald-500/30 px-2 py-0.5 rounded text-[11px] font-mono">
              80G Reg: AAATR8291PF20214
            </span>
            <span className="hidden lg:inline bg-white/20 px-2 py-0.5 rounded text-[11px] font-mono">
              PAN: AAATR8291P
            </span>
          </div>

          {stats && (
            <div className="flex items-center gap-3 text-xs">
              <span className="flex items-center gap-1 text-emerald-200">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Reconciled: ₹{stats.reconciled_amount.toLocaleString('en-IN')}</span>
              </span>
              <span className="bg-emerald-400/20 text-emerald-100 px-2 py-0.5 rounded-full font-semibold">
                Match Rate: {stats.match_rate_percentage}%
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Main Navbar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Brand */}
          <Link href="/" className="flex items-center gap-3 group">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-500 flex items-center justify-center text-white shadow-md shadow-emerald-500/20 group-hover:scale-105 transition-transform">
              <HeartHandshake className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-extrabold text-lg text-slate-900 dark:text-white tracking-tight">
                  Raise India
                </span>
                <span className="text-[10px] font-bold uppercase tracking-wider bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-400 px-1.5 py-0.5 rounded">
                  Reconcile AI
                </span>
              </div>
              <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-none">
                Automated UPI Donation & 80G Portal
              </p>
            </div>
          </Link>

          {/* Nav Items */}
          <nav className="hidden md:flex items-center gap-1">
            {navLinks.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href));
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 font-semibold shadow-xs'
                      : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? 'text-emerald-600 dark:text-emerald-400' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                  {item.badge && (
                    <span className="text-[10px] bg-emerald-600 text-white font-bold px-1.5 py-0.2 rounded-full">
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </nav>

          {/* Quick Actions */}
          <div className="flex items-center gap-2">
            <Link
              href="/donate"
              className="inline-flex items-center gap-1.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white text-sm font-semibold px-4 py-2 rounded-lg shadow-sm shadow-emerald-500/20 hover:shadow-md transition-all"
            >
              <HeartHandshake className="w-4 h-4" />
              <span>Donate & Claim 80G</span>
            </Link>
          </div>
        </div>
      </div>
    </header>
  );
}
