'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { 
  HeartHandshake, 
  ScanLine, 
  FileCheck2, 
  ShieldCheck, 
  ArrowRight, 
  CheckCircle2, 
  UploadCloud, 
  Building2, 
  FileSpreadsheet,
  Zap,
  TrendingUp,
  Cpu,
  Layers,
  Lock,
  Heart,
  Users,
  Award,
  Sparkles,
  QrCode,
  Copy,
  Check,
  Calculator,
  ChevronRight,
  ExternalLink,
  Clock,
  FileBadge,
  BadgeAlert
} from 'lucide-react';
import { api, ReconciliationStats } from '@/lib/api';

export default function HomePage() {
  const [stats, setStats] = useState<ReconciliationStats | null>(null);
  const [calcAmount, setCalcAmount] = useState<number>(10000);
  const [taxSlab, setTaxSlab] = useState<number>(30); // 30% tax bracket
  const [copiedUpi, setCopiedUpi] = useState(false);
  const [activeCategory, setActiveCategory] = useState<'all' | 'education' | 'health' | 'hunger'>('all');

  useEffect(() => {
    api.getReconciliationStats().then(setStats).catch(() => {});
  }, []);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedUpi(true);
    setTimeout(() => setCopiedUpi(false), 2000);
  };

  // 80G calculation: 50% deduction of donation amount under Indian Income Tax Act
  const taxDeductionEligible = calcAmount * 0.5;
  const netTaxSaved = taxDeductionEligible * (taxSlab / 100);
  const effectiveCost = calcAmount - netTaxSaved;

  const campaigns = [
    {
      id: 'shiksha',
      category: 'education',
      title: 'Project Shiksha: Educate 250 Tribal Girls in Rural Maharashtra',
      ngo: 'Raise India Foundation • Education Wing',
      image: 'https://images.unsplash.com/photo-1509062522246-3755977927d7?auto=format&fit=crop&w=800&q=80',
      raised: 1185000,
      goal: 1500000,
      donors: 342,
      daysLeft: 14,
      urgency: 'Critical',
      taxBenefit: '50% Tax Saved under 80G',
      impactSummary: 'Provides 1 full year of textbooks, digital tablets, and school uniforms.',
    },
    {
      id: 'poshan',
      category: 'hunger',
      title: 'Poshan Abhiyaan: Daily Nutritious Meals for 1,200 Slum Children',
      ngo: 'Raise India Foundation • Nutrition Relief',
      image: 'https://images.unsplash.com/photo-1488521787991-ed7bbaae773c?auto=format&fit=crop&w=800&q=80',
      raised: 890000,
      goal: 1000000,
      donors: 425,
      daysLeft: 8,
      urgency: 'Active Daily Relief',
      taxBenefit: '50% Tax Saved under 80G',
      impactSummary: 'Cooks and distributes freshly prepared hot meals with vital micronutrients.',
    },
    {
      id: 'jeevan',
      category: 'health',
      title: 'Jeevan Raksha: Emergency Pediatric Surgeries & Cancer Care',
      ngo: 'Raise India Foundation • Healthcare Cell',
      image: 'https://images.unsplash.com/photo-1576765608535-5f04d1e3f289?auto=format&fit=crop&w=800&q=80',
      raised: 1950000,
      goal: 2500000,
      donors: 610,
      daysLeft: 19,
      urgency: 'Life-saving Urgent',
      taxBenefit: '50% Tax Saved under 80G',
      impactSummary: 'Funds chemotherapy cycles, ICU beds, and specialized surgeries for low-income families.',
    },
  ];

  const filteredCampaigns = activeCategory === 'all' 
    ? campaigns 
    : campaigns.filter(c => c.category === activeCategory);

  return (
    <div className="space-y-20 pb-20">
      {/* TOP TRUST & STATS TICKER BAR */}
      <div className="bg-slate-900 border-b border-slate-800 text-slate-300 py-2.5 px-4 text-xs">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1.5 font-semibold text-emerald-400">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>NITI Aayog Darpan: DL/2021/028919</span>
            </span>
            <span className="hidden sm:inline text-slate-600">•</span>
            <span className="hidden sm:inline text-slate-300">
              80G Reg No: <strong className="text-white font-mono">AAATR8291PF20214</strong>
            </span>
            <span className="hidden md:inline text-slate-600">•</span>
            <span className="hidden md:inline text-slate-300">
              12A Registered & Form 10BD Compliant
            </span>
          </div>

          <div className="flex items-center gap-4 text-slate-400">
            <span className="hidden lg:flex items-center gap-1 text-emerald-300">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
              Live Reconciliation Active
            </span>
            <Link 
              href="/admin/reconcile" 
              className="hover:text-emerald-400 flex items-center gap-1 text-slate-400 transition-colors"
            >
              <span>Admin / CA Auditor Console</span>
              <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
        </div>
      </div>

      {/* HERO SECTION */}
      <section className="relative px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto pt-6">
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-slate-900 via-emerald-950 to-slate-950 text-white p-8 sm:p-14 lg:p-16 shadow-2xl border border-slate-800/80">
          {/* Subtle Ambient Lighting */}
          <div className="absolute -top-32 -right-32 w-96 h-96 bg-emerald-500/20 rounded-full blur-3xl pointer-events-none"></div>
          <div className="absolute -bottom-32 -left-32 w-96 h-96 bg-teal-500/15 rounded-full blur-3xl pointer-events-none"></div>

          <div className="relative z-10 grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
            {/* Left Content */}
            <div className="lg:col-span-7 space-y-6">
              <div className="inline-flex items-center gap-2 bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 text-xs font-bold px-3.5 py-1.5 rounded-full uppercase tracking-wider">
                <Sparkles className="w-4 h-4 text-emerald-400" />
                <span>India's 1st AI-Reconciled NGO Platform</span>
              </div>

              <h1 className="text-3xl sm:text-5xl lg:text-6xl font-black tracking-tight leading-[1.12]">
                Every Rupee Delivers Hope. <br />
                <span className="bg-gradient-to-r from-emerald-400 via-teal-300 to-green-200 bg-clip-text text-transparent">
                  100% Verified & 80G Tax Deductible.
                </span>
              </h1>

              <p className="text-slate-300 text-sm sm:text-base lg:text-lg leading-relaxed max-w-2xl">
                Donate seamlessly via any UPI app (Google Pay, PhonePe, Paytm, BHIM). Our computer vision & banking reconciliation engine instantly matches bank credits, verifies UTRs, and auto-dispatches your official <strong>Section 80G Tax Exemption Certificate</strong> directly to WhatsApp and email.
              </p>

              {/* Action Buttons */}
              <div className="pt-2 flex flex-wrap items-center gap-3">
                <Link
                  href="/donate"
                  className="inline-flex items-center gap-2 px-7 py-4 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 text-white font-bold text-sm sm:text-base shadow-xl shadow-emerald-500/25 transition-all hover:scale-[1.02] active:scale-[0.98]"
                >
                  <Heart className="w-5 h-5 fill-white" />
                  <span>Donate via UPI & Claim 80G</span>
                  <ArrowRight className="w-4 h-4" />
                </Link>

                <Link
                  href="/donate#lookup"
                  className="inline-flex items-center gap-2 px-6 py-4 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 text-white font-semibold text-sm shadow-md transition-all hover:scale-[1.02]"
                >
                  <FileBadge className="w-5 h-5 text-emerald-400" />
                  <span>Instant 80G Receipt Lookup</span>
                </Link>
              </div>

              {/* Trust Indicators */}
              <div className="pt-4 flex flex-wrap items-center gap-6 text-xs text-slate-300 border-t border-slate-800/80">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>50% Tax Exemption (Sec 80G)</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>Annual Form 10BD Guarantee</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>100% Bank Reconciled</span>
                </div>
              </div>
            </div>

            {/* Right Interactive Live UPI & Impact Card */}
            <div className="lg:col-span-5">
              <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-2xl p-6 sm:p-7 shadow-2xl text-white space-y-6">
                <div className="flex items-center justify-between pb-4 border-b border-white/10">
                  <div className="flex items-center gap-2">
                    <QrCode className="w-5 h-5 text-emerald-400" />
                    <span className="font-bold text-sm tracking-wide">Official NGO UPI Handle</span>
                  </div>
                  <span className="bg-emerald-500/20 text-emerald-300 text-[11px] font-bold px-2 py-0.5 rounded-full border border-emerald-500/30">
                    Instant Clearance
                  </span>
                </div>

                {/* UPI Box */}
                <div className="bg-slate-900/90 rounded-xl p-4 border border-slate-700/80 space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="text-[11px] text-slate-400 uppercase tracking-wider block">Official VPA / UPI ID</span>
                      <span className="font-mono text-base font-bold text-emerald-400">raiseindia@sbi</span>
                    </div>
                    <button
                      onClick={() => copyToClipboard('raiseindia@sbi')}
                      className="px-3 py-1.5 rounded-lg bg-emerald-600/30 hover:bg-emerald-600/50 text-emerald-300 text-xs font-semibold flex items-center gap-1.5 transition-colors border border-emerald-500/40"
                    >
                      {copiedUpi ? (
                        <>
                          <Check className="w-3.5 h-3.5 text-emerald-400" />
                          <span>Copied!</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3.5 h-3.5" />
                          <span>Copy UPI</span>
                        </>
                      )}
                    </button>
                  </div>

                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    Accepted on PhonePe, Google Pay, Paytm, BHIM, Cred, and all mobile banking apps.
                  </p>
                </div>

                {/* Live Stats from Backend */}
                {stats ? (
                  <div className="grid grid-cols-2 gap-3 pt-2">
                    <div className="bg-white/5 rounded-xl p-3 border border-white/10">
                      <span className="text-[11px] text-slate-400 uppercase block">Total Impact Raised</span>
                      <span className="text-lg font-black text-white">₹{stats.total_amount_collected.toLocaleString('en-IN')}</span>
                    </div>
                    <div className="bg-white/5 rounded-xl p-3 border border-white/10">
                      <span className="text-[11px] text-emerald-400 uppercase block">Bank Reconciled</span>
                      <span className="text-lg font-black text-emerald-400">₹{stats.reconciled_amount.toLocaleString('en-IN')}</span>
                    </div>
                    <div className="bg-white/5 rounded-xl p-3 border border-white/10">
                      <span className="text-[11px] text-slate-400 uppercase block">Automated Match Rate</span>
                      <span className="text-lg font-black text-indigo-300">{stats.match_rate_percentage}%</span>
                    </div>
                    <div className="bg-white/5 rounded-xl p-3 border border-white/10">
                      <span className="text-[11px] text-slate-400 uppercase block">Verified 80G Donors</span>
                      <span className="text-lg font-black text-white">{stats.matched_count}</span>
                    </div>
                  </div>
                ) : (
                  <div className="p-4 bg-white/5 rounded-xl text-center text-xs text-slate-300">
                    Connecting to live reconciliation ledger...
                  </div>
                )}

                <Link
                  href="/donate"
                  className="w-full py-3.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 text-white font-bold text-sm text-center flex items-center justify-center gap-2 shadow-lg transition-all"
                >
                  <span>Upload Payment Screenshot</span>
                  <ArrowRight className="w-4 h-4" />
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* FEATURED CAUSES / CAMPAIGNS (GiveIndia & Milaap Style) */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-600 uppercase tracking-wider mb-1">
              <Heart className="w-4 h-4 fill-emerald-600" />
              <span>Verified High-Impact Campaigns</span>
            </div>
            <h2 className="text-2xl sm:text-3xl lg:text-4xl font-black text-slate-900 tracking-tight">
              Support Causes That Change Lives
            </h2>
            <p className="text-sm text-slate-600 mt-1 max-w-xl">
              Every campaign undergoes rigorous field verification by our social audit team. 100% of your contribution is eligible for 50% tax exemption under Section 80G.
            </p>
          </div>

          {/* Category Tabs */}
          <div className="flex items-center gap-2 bg-slate-100 p-1.5 rounded-xl border border-slate-200 self-start md:self-auto">
            <button
              onClick={() => setActiveCategory('all')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                activeCategory === 'all' 
                  ? 'bg-white text-emerald-700 shadow-xs' 
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              All Causes
            </button>
            <button
              onClick={() => setActiveCategory('education')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                activeCategory === 'education' 
                  ? 'bg-white text-emerald-700 shadow-xs' 
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Girl Education
            </button>
            <button
              onClick={() => setActiveCategory('hunger')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                activeCategory === 'hunger' 
                  ? 'bg-white text-emerald-700 shadow-xs' 
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Child Nutrition
            </button>
            <button
              onClick={() => setActiveCategory('health')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                activeCategory === 'health' 
                  ? 'bg-white text-emerald-700 shadow-xs' 
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Medical Care
            </button>
          </div>
        </div>

        {/* Campaign Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {filteredCampaigns.map((camp) => {
            const percent = Math.min(100, Math.round((camp.raised / camp.goal) * 100));

            return (
              <div 
                key={camp.id}
                className="bg-white rounded-3xl border border-slate-200/90 shadow-sm hover:shadow-xl hover:border-emerald-300 transition-all duration-300 flex flex-col overflow-hidden group"
              >
                {/* Image & Badges */}
                <div className="relative h-52 w-full overflow-hidden bg-slate-100">
                  <img 
                    src={camp.image} 
                    alt={camp.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" 
                  />
                  <div className="absolute top-3 left-3 flex flex-wrap gap-2">
                    <span className="bg-emerald-600/95 backdrop-blur-md text-white text-[11px] font-bold px-2.5 py-1 rounded-full shadow-sm flex items-center gap-1">
                      <ShieldCheck className="w-3.5 h-3.5" />
                      <span>Verified NGO</span>
                    </span>
                    <span className="bg-amber-500/95 backdrop-blur-md text-white text-[11px] font-bold px-2.5 py-1 rounded-full shadow-sm">
                      {camp.urgency}
                    </span>
                  </div>
                  <div className="absolute bottom-3 right-3 bg-slate-900/85 backdrop-blur-md text-emerald-300 text-[10px] font-bold px-2.5 py-1 rounded-full border border-emerald-500/30">
                    {camp.taxBenefit}
                  </div>
                </div>

                {/* Content */}
                <div className="p-6 flex-1 flex flex-col justify-between space-y-5">
                  <div className="space-y-2">
                    <span className="text-[11px] font-bold text-emerald-700 uppercase tracking-wider block">
                      {camp.ngo}
                    </span>
                    <h3 className="text-base font-extrabold text-slate-900 line-clamp-2 leading-snug group-hover:text-emerald-700 transition-colors">
                      {camp.title}
                    </h3>
                    <p className="text-xs text-slate-500 leading-relaxed line-clamp-2">
                      {camp.impactSummary}
                    </p>
                  </div>

                  {/* Progress Bar & Stats */}
                  <div className="space-y-3 pt-2">
                    <div className="flex items-center justify-between text-xs font-bold">
                      <span className="text-emerald-700 text-sm">
                        ₹{camp.raised.toLocaleString('en-IN')}
                      </span>
                      <span className="text-slate-400 font-normal">
                        of ₹{camp.goal.toLocaleString('en-IN')}
                      </span>
                    </div>

                    <div className="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden">
                      <div 
                        className="bg-gradient-to-r from-emerald-500 to-teal-500 h-full rounded-full transition-all duration-1000"
                        style={{ width: `${percent}%` }}
                      ></div>
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-slate-500 font-medium">
                      <span className="flex items-center gap-1">
                        <Users className="w-3.5 h-3.5 text-slate-400" />
                        <strong>{camp.donors}</strong> Donors
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5 text-slate-400" />
                        <strong>{camp.daysLeft}</strong> days left
                      </span>
                      <span className="font-bold text-emerald-700">
                        {percent}% funded
                      </span>
                    </div>
                  </div>

                  {/* Action Button */}
                  <div className="pt-2 border-t border-slate-100">
                    <Link
                      href="/donate"
                      className="w-full py-3 rounded-xl bg-emerald-50 hover:bg-emerald-600 text-emerald-700 hover:text-white font-bold text-xs sm:text-sm flex items-center justify-center gap-2 transition-all border border-emerald-200 hover:border-emerald-600 shadow-xs"
                    >
                      <HeartHandshake className="w-4 h-4" />
                      <span>Donate & Save Tax</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* INTERACTIVE 80G TAX EXEMPTION CALCULATOR */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-gradient-to-br from-emerald-900 via-slate-900 to-slate-950 text-white rounded-3xl p-8 sm:p-12 lg:p-14 border border-emerald-800/50 shadow-2xl relative overflow-hidden">
          <div className="absolute -top-24 -left-24 w-80 h-80 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none"></div>

          <div className="relative z-10 grid grid-cols-1 lg:grid-cols-12 gap-10 items-center">
            {/* Left Explanation */}
            <div className="lg:col-span-6 space-y-6">
              <div className="inline-flex items-center gap-2 bg-emerald-500/20 text-emerald-300 text-xs font-bold px-3 py-1.5 rounded-full border border-emerald-500/30">
                <Calculator className="w-4 h-4 text-emerald-400" />
                <span>Section 80G Tax Exemption Calculator</span>
              </div>

              <h2 className="text-2xl sm:text-4xl font-black tracking-tight leading-tight">
                Multiply Your Impact, <br />
                <span className="text-emerald-400">Reduce Your Income Tax.</span>
              </h2>

              <p className="text-slate-300 text-sm sm:text-base leading-relaxed">
                Under Section 80G(5)(vi) of the Indian Income Tax Act, 1961, <strong>50% of your donation amount is eligible for tax deduction</strong>. See how giving saves you real cash on your annual tax liability while funding essential programs.
              </p>

              {/* Amount Quick Presets */}
              <div className="space-y-3 pt-2">
                <span className="text-xs font-bold text-slate-300 block uppercase tracking-wider">
                  Select Donation Amount:
                </span>
                <div className="flex flex-wrap gap-2.5">
                  {[2000, 5000, 10000, 25000, 50000].map((amt) => (
                    <button
                      key={amt}
                      onClick={() => setCalcAmount(amt)}
                      className={`px-4 py-2 rounded-xl text-xs sm:text-sm font-bold transition-all border ${
                        calcAmount === amt
                          ? 'bg-emerald-500 text-white border-emerald-400 shadow-md shadow-emerald-500/30 scale-105'
                          : 'bg-white/10 text-slate-300 border-white/15 hover:bg-white/20'
                      }`}
                    >
                      ₹{amt.toLocaleString('en-IN')}
                    </button>
                  ))}
                </div>
              </div>

              {/* Tax Slab Selector */}
              <div className="space-y-3 pt-2">
                <span className="text-xs font-bold text-slate-300 block uppercase tracking-wider">
                  Your Income Tax Slab:
                </span>
                <div className="flex items-center gap-3">
                  {[
                    { label: '20% Slab', value: 20 },
                    { label: '30% Slab (Standard)', value: 30 },
                    { label: '39% (Highest with Surcharge)', value: 39 },
                  ].map((slab) => (
                    <button
                      key={slab.value}
                      onClick={() => setTaxSlab(slab.value)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all border ${
                        taxSlab === slab.value
                          ? 'bg-teal-500 text-white border-teal-400'
                          : 'bg-white/5 text-slate-400 border-white/10 hover:bg-white/15'
                      }`}
                    >
                      {slab.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Right Result Card */}
            <div className="lg:col-span-6">
              <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-2xl p-6 sm:p-8 space-y-6">
                <div className="flex items-center justify-between pb-4 border-b border-white/10">
                  <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                    Tax Savings Breakdown
                  </span>
                  <span className="bg-emerald-400/20 text-emerald-300 font-bold text-[11px] px-2.5 py-0.5 rounded-full border border-emerald-400/30">
                    Rule 18AB Compliant
                  </span>
                </div>

                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-300">Donation Amount</span>
                    <span className="text-lg font-black text-white">₹{calcAmount.toLocaleString('en-IN')}</span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-300">50% Deduction under Sec 80G</span>
                    <span className="text-base font-bold text-teal-300 font-mono">₹{taxDeductionEligible.toLocaleString('en-IN')}</span>
                  </div>

                  <div className="p-4 rounded-xl bg-emerald-500/20 border border-emerald-400/40 flex items-center justify-between">
                    <div>
                      <span className="text-xs text-emerald-300 font-bold uppercase tracking-wider block">
                        Direct Cash Tax Saved
                      </span>
                      <span className="text-[11px] text-slate-300">Net refund in your pocket</span>
                    </div>
                    <span className="text-2xl font-black text-emerald-300 font-mono">
                      ₹{Math.round(netTaxSaved).toLocaleString('en-IN')}
                    </span>
                  </div>

                  <div className="p-4 rounded-xl bg-white/5 border border-white/10 flex items-center justify-between">
                    <div>
                      <span className="text-xs text-slate-300 font-bold uppercase tracking-wider block">
                        Effective Cost to You
                      </span>
                      <span className="text-[11px] text-slate-400">Actual out-of-pocket expenditure</span>
                    </div>
                    <span className="text-xl font-black text-white font-mono">
                      ₹{Math.round(effectiveCost).toLocaleString('en-IN')}
                    </span>
                  </div>
                </div>

                <div className="pt-2">
                  <Link
                    href={`/donate?amount=${calcAmount}`}
                    className="w-full py-4 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 text-white font-bold text-sm text-center flex items-center justify-center gap-2 shadow-lg transition-all"
                  >
                    <span>Donate ₹{calcAmount.toLocaleString('en-IN')} & Claim Certificate</span>
                    <ArrowRight className="w-4 h-4" />
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* HOW THE END-TO-END AUTOMATED PIPELINE WORKS */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-10">
        <div className="text-center max-w-3xl mx-auto space-y-2">
          <div className="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-600 uppercase tracking-wider">
            <Cpu className="w-4 h-4" />
            <span>Anti-Fraud & 80G Automation</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
            How Raise India Bridges Anonymous UPI to Form 10BD
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 max-w-2xl mx-auto">
            NPCI UPI protocol strips PAN numbers and addresses during QR payments. Our portal re-connects identities through intelligent computer vision and bank ledger reconciliation.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {/* Step 1 */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs hover:border-emerald-300 transition-all flex flex-col justify-between">
            <div>
              <div className="w-10 h-10 bg-emerald-100 text-emerald-700 rounded-xl flex items-center justify-center font-bold text-sm mb-4">
                01
              </div>
              <h3 className="text-base font-bold text-slate-900 mb-2">
                Scan UPI & Submit PAN
              </h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                Donor pays using any UPI app and submits their verified PAN (enforced by regex <code className="font-mono bg-slate-100 px-1 py-0.5 rounded text-[10px]">^[A-Z]&#123;5&#125;[0-9]&#123;4&#125;[A-Z]&#123;1&#125;$</code>) along with payment screenshot.
              </p>
            </div>
            <div className="pt-4 mt-4 border-t border-slate-100">
              <Link href="/donate" className="text-xs font-bold text-emerald-600 hover:text-emerald-700 flex items-center gap-1">
                <span>Go to Donor Form</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>

          {/* Step 2 */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs hover:border-indigo-300 transition-all flex flex-col justify-between">
            <div>
              <div className="w-10 h-10 bg-indigo-100 text-indigo-700 rounded-xl flex items-center justify-center font-bold text-sm mb-4">
                02
              </div>
              <h3 className="text-base font-bold text-slate-900 mb-2">
                AI OCR & ELA Forensics
              </h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                OpenCV pre-processes screenshot. Generates SHA-256 hash to reject duplicate uploads, runs Error Level Analysis (ELA Q90) to detect Photoshopped numbers, and extracts the 12-digit UTR.
              </p>
            </div>
            <div className="pt-4 mt-4 border-t border-slate-100">
              <Link href="/admin/bulk-upload" className="text-xs font-bold text-indigo-600 hover:text-indigo-700 flex items-center gap-1">
                <span>Bulk Upload Portal</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>

          {/* Step 3 */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs hover:border-teal-300 transition-all flex flex-col justify-between">
            <div>
              <div className="w-10 h-10 bg-teal-100 text-teal-700 rounded-xl flex items-center justify-center font-bold text-sm mb-4">
                03
              </div>
              <h3 className="text-base font-bold text-slate-900 mb-2">
                Bank Statement Match
              </h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                Bank Excel statements are parsed with running balance math audits. Levenshtein fuzzy matching ranks candidate statement credits within ±2 days and ±2 edit distance.
              </p>
            </div>
            <div className="pt-4 mt-4 border-t border-slate-100">
              <Link href="/admin/bank-statement" className="text-xs font-bold text-teal-600 hover:text-teal-700 flex items-center gap-1">
                <span>View Bank Statements</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>

          {/* Step 4 */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs hover:border-amber-300 transition-all flex flex-col justify-between">
            <div>
              <div className="w-10 h-10 bg-amber-100 text-amber-700 rounded-xl flex items-center justify-center font-bold text-sm mb-4">
                04
              </div>
              <h3 className="text-base font-bold text-slate-900 mb-2">
                WhatsApp 80G & Form 10BD
              </h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                Upon verification, the system issues digitally signed Section 80G PDF receipts, dispatches them via WhatsApp, and pre-compiles official Form 10BD for Income Tax Department filing.
              </p>
            </div>
            <div className="pt-4 mt-4 border-t border-slate-100">
              <Link href="/admin/reconcile" className="text-xs font-bold text-amber-600 hover:text-amber-700 flex items-center gap-1">
                <span>Reconcile Console</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* DONOR TESTIMONIALS & TRUST */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-slate-100 rounded-3xl p-8 sm:p-12 border border-slate-200 space-y-8">
          <div className="text-center max-w-xl mx-auto">
            <span className="text-xs font-bold text-emerald-600 uppercase tracking-wider block">
              Trusted by 5,000+ Indian Donors
            </span>
            <h2 className="text-2xl font-black text-slate-900 mt-1">
              What Our Donors Say
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs space-y-3">
              <div className="flex text-amber-400 text-sm">★★★★★</div>
              <p className="text-xs text-slate-600 leading-relaxed italic">
                "Donating via Google Pay was easy, but getting the 80G receipt used to take weeks with other charities. With Raise India, I got my receipt within 2 minutes on WhatsApp with my PAN properly registered for Form 10BD."
              </p>
              <div className="pt-2 border-t border-slate-100">
                <span className="text-xs font-bold text-slate-900 block">Vikramaditya S.</span>
                <span className="text-[11px] text-slate-400">Software Architect, Bengaluru</span>
              </div>
            </div>

            <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs space-y-3">
              <div className="flex text-amber-400 text-sm">★★★★★</div>
              <p className="text-xs text-slate-600 leading-relaxed italic">
                "Our CA insisted that we only donate to NGOs that report donations under Form 10BD for seamless AIS tax matching. Raise India is the most transparent foundation in India right now."
              </p>
              <div className="pt-2 border-t border-slate-100">
                <span className="text-xs font-bold text-slate-900 block">Meenakshi Iyer</span>
                <span className="text-[11px] text-slate-400">Financial Consultant, Mumbai</span>
              </div>
            </div>

            <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs space-y-3">
              <div className="flex text-amber-400 text-sm">★★★★★</div>
              <p className="text-xs text-slate-600 leading-relaxed italic">
                "Knowing that every single rupee is reconciled with bank statements and backed by anti-fraud image audits gives our corporate CSR team total confidence in sponsoring their girl child education initiative."
              </p>
              <div className="pt-2 border-t border-slate-100">
                <span className="text-xs font-bold text-slate-900 block">Rajesh Goenka</span>
                <span className="text-[11px] text-slate-400">CSR Director, Gurugram</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CALL TO ACTION BOTTOM BANNER */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-gradient-to-r from-emerald-600 via-teal-600 to-indigo-700 rounded-3xl p-8 sm:p-12 text-white shadow-xl flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="space-y-2 max-w-xl">
            <span className="text-xs font-bold uppercase tracking-wider bg-white/20 px-3 py-1 rounded-full inline-block">
              Immediate Tax Exemption
            </span>
            <h3 className="text-2xl sm:text-3xl font-black">
              Make a Difference Today. Claim 80G Now.
            </h3>
            <p className="text-xs sm:text-sm text-emerald-100 leading-relaxed">
              Your contribution brings nutrition, education, and medical care to those who need it most. Scan UPI QR or input your reference for instant receipt generation.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 shrink-0">
            <Link
              href="/donate"
              className="px-7 py-3.5 rounded-xl bg-white text-emerald-800 hover:bg-slate-100 font-extrabold text-sm shadow-md transition-all hover:scale-105"
            >
              Donate Now
            </Link>
            <Link
              href="/donate#lookup"
              className="px-5 py-3.5 rounded-xl bg-white/10 hover:bg-white/20 border border-white/20 text-white font-bold text-sm transition-all"
            >
              Lookup 80G PDF
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
