'use client';

import React, { useState, useEffect, useRef } from 'react';
import confetti from 'canvas-confetti';
import { 
  ScanLine, 
  CheckCircle2, 
  AlertTriangle, 
  XCircle, 
  FileSpreadsheet, 
  ZoomIn, 
  ZoomOut, 
  RotateCw, 
  Maximize2, 
  Edit3, 
  Save, 
  Check, 
  X, 
  Download, 
  Building2, 
  User, 
  CreditCard, 
  Calendar, 
  Search, 
  RefreshCw, 
  Link2, 
  Unlink, 
  Eye,
  SlidersHorizontal,
  ChevronRight,
  ShieldCheck,
  ShieldAlert,
  Fingerprint,
  Activity,
  Layers,
  FileKey2,
  TrendingUp,
  FileCheck2
} from 'lucide-react';
import { api, Donation, BankStatementEntry, FuzzyCandidate, ReconciliationStats } from '@/lib/api';

export default function ReconcilePage() {
  const [donations, setDonations] = useState<Donation[]>([]);
  const [selectedDonation, setSelectedDonation] = useState<Donation | null>(null);
  const [stats, setStats] = useState<ReconciliationStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeFilter, setActiveFilter] = useState<'ALL' | 'FLAGGED_REVIEW' | 'EXTRACTED' | 'MATCHED' | 'REJECTED'>('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  // Edit form state
  const [isEditing, setIsEditing] = useState(false);
  const [editUtr, setEditUtr] = useState('');
  const [editAmount, setEditAmount] = useState('');
  const [savingEdit, setSavingEdit] = useState(false);

  // CA Audit & Verification state
  const [auditorUser, setAuditorUser] = useState('ca_auditor@raiseindia.org');
  const [auditNotes, setAuditNotes] = useState('');
  const [matchedMode, setMatchedMode] = useState('MANUAL_OVERRIDE');

  // ELA / Forensic View Mode state
  const [viewMode, setViewMode] = useState<'original' | 'ela'>('original');

  // Fuzzy candidates state
  const [candidates, setCandidates] = useState<FuzzyCandidate[]>([]);
  const [loadingCandidates, setLoadingCandidates] = useState(false);

  // Image viewer zoom / pan / rotate state
  const [zoomLevel, setZoomLevel] = useState(1);
  const [rotation, setRotation] = useState(0);
  const [panPosition, setPanPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  // Action status message
  const [actionMessage, setActionMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const [donationsData, statsData] = await Promise.all([
        api.getDonations(activeFilter, searchQuery),
        api.getReconciliationStats(),
      ]);
      setDonations(donationsData);
      setStats(statsData);

      // Select first donation if none selected or not in list
      if (donationsData.length > 0) {
        if (!selectedDonation || !donationsData.some(d => d.id === selectedDonation.id)) {
          selectDonationItem(donationsData[0]);
        } else {
          // Refresh selected
          const updated = donationsData.find(d => d.id === selectedDonation.id);
          if (updated) selectDonationItem(updated);
        }
      } else {
        setSelectedDonation(null);
      }
    } catch (err: any) {
      console.error('Error fetching data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, [activeFilter]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchDashboardData();
  };

  const selectDonationItem = async (donation: Donation) => {
    setSelectedDonation(donation);
    setIsEditing(false);
    setEditUtr(donation.extracted_utr || '');
    setEditAmount(donation.extracted_amount ? String(donation.extracted_amount) : '');
    setViewMode('original');
    setAuditorUser(donation.verified_by_user || 'ca_auditor@raiseindia.org');
    setAuditNotes(donation.admin_audit_notes || '');
    setMatchedMode(donation.bank_matched_mode || 'MANUAL_OVERRIDE');
    // Reset zoom
    setZoomLevel(1);
    setRotation(0);
    setPanPosition({ x: 0, y: 0 });

    // Fetch fuzzy candidates if flagged or not verified
    if (!donation.is_verified) {
      setLoadingCandidates(true);
      try {
        const cands = await api.getFuzzyCandidates(donation.id);
        setCandidates(cands);
      } catch (err) {
        setCandidates([]);
      } finally {
        setLoadingCandidates(false);
      }
    } else {
      setCandidates([]);
    }
  };

  // Zoom controls
  const handleZoomIn = () => setZoomLevel(prev => Math.min(prev + 0.25, 3.5));
  const handleZoomOut = () => setZoomLevel(prev => Math.max(prev - 0.25, 0.5));
  const handleResetZoom = () => {
    setZoomLevel(1);
    setPanPosition({ x: 0, y: 0 });
    setRotation(0);
  };
  const handleRotate = () => setRotation(prev => (prev + 90) % 360);

  // Mouse pan handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - panPosition.x, y: e.clientY - panPosition.y });
  };
  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging) {
      setPanPosition({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      });
    }
  };
  const handleMouseUp = () => setIsDragging(false);

  // Edit & Save handler
  const handleSaveEdit = async () => {
    if (!selectedDonation) return;
    try {
      setSavingEdit(true);
      const updated = await api.updateDonation(selectedDonation.id, {
        extracted_utr: editUtr.trim(),
        extracted_amount: editAmount ? parseFloat(editAmount) : undefined,
      });
      setIsEditing(false);
      setActionMessage({ type: 'success', text: 'OCR fields updated and re-evaluated successfully!' });
      await fetchDashboardData();
      selectDonationItem(updated);
    } catch (err: any) {
      setActionMessage({ type: 'error', text: err.message || 'Failed to update fields' });
    } finally {
      setSavingEdit(false);
    }
  };

  // Mark as verified handler
  const handleVerify = async () => {
    if (!selectedDonation) return;
    try {
      const verified = await api.verifyDonation(selectedDonation.id, {
        verified_by_user: auditorUser.trim() || 'ca_auditor@raiseindia.org',
        admin_audit_notes: auditNotes.trim() || undefined,
        bank_matched_mode: matchedMode || 'MANUAL_OVERRIDE',
      });
      setActionMessage({ type: 'success', text: 'Donation certified & verified! Section 80G Tax Receipt generated & WhatsApp dispatch queued.' });
      confetti({ particleCount: 70, spread: 60, origin: { y: 0.6 } });
      await fetchDashboardData();
      selectDonationItem(verified);
    } catch (err: any) {
      setActionMessage({ type: 'error', text: err.message || 'Failed to verify donation' });
    }
  };

  // Reject handler
  const handleReject = async () => {
    if (!selectedDonation) return;
    if (!confirm('Are you sure you want to reject this payment screenshot as invalid/duplicate?')) return;
    try {
      const rejected = await api.rejectDonation(selectedDonation.id, 'Marked invalid by admin during reconciliation');
      setActionMessage({ type: 'success', text: 'Donation marked as REJECTED.' });
      await fetchDashboardData();
      selectDonationItem(rejected);
    } catch (err: any) {
      setActionMessage({ type: 'error', text: err.message || 'Failed to reject donation' });
    }
  };

  // Manual Link handler
  const handleManualLink = async (statementId: string) => {
    if (!selectedDonation) return;
    try {
      const linked = await api.manualLinkAndVerify(selectedDonation.id, statementId, {
        verified_by_user: auditorUser.trim() || 'ca_auditor@raiseindia.org',
        admin_audit_notes: auditNotes.trim() || undefined,
        bank_matched_mode: 'AUTO_FUZZY',
      });
      setActionMessage({ type: 'success', text: 'Linked with bank credit, CA audit logged & 80G certificate issued!' });
      confetti({ particleCount: 70, spread: 60, origin: { y: 0.6 } });
      await fetchDashboardData();
      selectDonationItem(linked);
    } catch (err: any) {
      setActionMessage({ type: 'error', text: err.message || 'Failed to link entry' });
    }
  };

  // Unlink handler
  const handleUnlink = async () => {
    if (!selectedDonation) return;
    try {
      const unlinked = await api.unlinkDonation(selectedDonation.id);
      setActionMessage({ type: 'success', text: 'Unlinked from bank statement entry.' });
      await fetchDashboardData();
      selectDonationItem(unlinked);
    } catch (err: any) {
      setActionMessage({ type: 'error', text: err.message || 'Failed to unlink' });
    }
  };

  // Trigger auto reconciliation
  const handleRunReconciliation = async () => {
    try {
      setLoading(true);
      const res = await api.triggerReconciliation();
      setActionMessage({
        type: 'success',
        text: `Reconciliation finished! Exact matches: ${res.details.exact_matches}, Fuzzy matches: ${res.details.fuzzy_matches}, Flagged: ${res.details.duplicates_flagged}`,
      });
      await fetchDashboardData();
    } catch (err: any) {
      setActionMessage({ type: 'error', text: 'Failed to run reconciliation' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="py-6 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto space-y-6">
      {/* Top Banner & Stats */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              Reconciliation & Audit Console
            </h1>
            <span className="text-xs bg-emerald-100 text-emerald-800 font-bold px-2.5 py-0.5 rounded-full">
              Live Bank Matching
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Split-screen verification: Inspect UPI screenshot OCR against official bank statement credits.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={handleRunReconciliation}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow-xs transition-all cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Run Auto-Reconciliation</span>
          </button>

          <a
            href={api.getForm10BdExportUrl()}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-xs transition-all"
          >
            <FileSpreadsheet className="w-3.5 h-3.5" />
            <span>Export Form 10BD (Excel)</span>
          </a>
        </div>
      </div>

      {/* KPI Cards */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Total Donated</span>
            <div className="text-lg font-bold text-slate-900 mt-0.5">
              ₹{stats.total_amount_collected.toLocaleString('en-IN')}
            </div>
            <span className="text-[11px] text-slate-500">{stats.total_donations} submissions</span>
          </div>

          <div className="bg-white p-4 rounded-xl border border-emerald-200 shadow-2xs bg-emerald-50/20">
            <span className="text-[11px] font-semibold text-emerald-700 uppercase tracking-wider">Reconciled</span>
            <div className="text-lg font-bold text-emerald-800 mt-0.5">
              ₹{stats.reconciled_amount.toLocaleString('en-IN')}
            </div>
            <span className="text-[11px] text-emerald-600 font-medium">{stats.matched_count} verified</span>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Match Rate</span>
            <div className="text-lg font-bold text-indigo-700 mt-0.5">
              {stats.match_rate_percentage}%
            </div>
            <span className="text-[11px] text-slate-500">Auto + manual</span>
          </div>

          <div className="bg-white p-4 rounded-xl border border-amber-200 shadow-2xs bg-amber-50/20">
            <span className="text-[11px] font-semibold text-amber-700 uppercase tracking-wider">Review Needed</span>
            <div className="text-lg font-bold text-amber-800 mt-0.5">
              {stats.flagged_count}
            </div>
            <span className="text-[11px] text-amber-600 font-medium">Fuzzy or duplicate</span>
          </div>

          <div className="bg-white p-4 rounded-xl border border-red-200 shadow-2xs bg-red-50/30">
            <span className="text-[11px] font-semibold text-red-700 uppercase tracking-wider flex items-center gap-1">
              <ShieldAlert className="w-3 h-3 text-red-600" />
              <span>Fraud Alert</span>
            </span>
            <div className="text-lg font-bold text-red-800 mt-0.5">
              {stats.fraud_flagged_count ?? 0}
            </div>
            <span className="text-[11px] text-red-600 font-medium">Tampered / Dupes</span>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Bank Unreconciled</span>
            <div className="text-lg font-bold text-slate-700 mt-0.5">
              {stats.unreconciled_statement_count}
            </div>
            <span className="text-[11px] text-slate-500">Awaiting proofs</span>
          </div>
        </div>
      )}

      {/* Action Notification */}
      {actionMessage && (
        <div className={`p-3.5 rounded-xl text-xs font-medium flex items-center justify-between ${
          actionMessage.type === 'success'
            ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
            : 'bg-red-50 text-red-800 border border-red-200'
        }`}>
          <span>{actionMessage.text}</span>
          <button onClick={() => setActionMessage(null)} className="hover:opacity-75">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Main Container: Queue Left + Split-Screen Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* LEFT COLUMN: DONATION QUEUE (4 Cols on desktop) */}
        <div className="lg:col-span-4 bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden flex flex-col h-[750px]">
          {/* Filter Tabs */}
          <div className="p-3 border-b border-slate-200 bg-slate-50/50 space-y-2">
            <form onSubmit={handleSearch} className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Search UTR, Donor Name, PAN..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 rounded-lg border border-slate-300 text-xs focus:ring-1 focus:ring-emerald-500 outline-hidden bg-white"
              />
            </form>

            <div className="flex flex-wrap gap-1">
              {[
                { id: 'ALL', label: 'All' },
                { id: 'FLAGGED_REVIEW', label: 'Review' },
                { id: 'EXTRACTED', label: 'Pending' },
                { id: 'MATCHED', label: 'Verified' },
                { id: 'REJECTED', label: 'Rejected' },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveFilter(tab.id as any)}
                  className={`text-[11px] font-semibold px-2.5 py-1 rounded-md transition-all cursor-pointer ${
                    activeFilter === tab.id
                      ? 'bg-slate-900 text-white shadow-2xs'
                      : 'bg-white text-slate-600 hover:bg-slate-100 border border-slate-200'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          {/* Queue List */}
          <div className="flex-1 overflow-y-auto divide-y divide-slate-100">
            {loading ? (
              <div className="p-8 text-center text-xs text-slate-400 flex items-center justify-center gap-2">
                <RefreshCw className="w-4 h-4 animate-spin text-emerald-600" />
                <span>Loading donations queue...</span>
              </div>
            ) : donations.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-400">
                No donation records found matching criteria.
              </div>
            ) : (
              donations.map((d) => {
                const isSelected = selectedDonation?.id === d.id;
                return (
                  <div
                    key={d.id}
                    onClick={() => selectDonationItem(d)}
                    className={`p-3.5 transition-all cursor-pointer hover:bg-slate-50 flex items-center justify-between gap-3 ${
                      isSelected
                        ? d.is_flagged_fraud
                          ? 'bg-red-50/70 border-l-4 border-red-600'
                          : 'bg-emerald-50/60 border-l-4 border-emerald-600'
                        : d.is_flagged_fraud
                        ? 'bg-red-50/20'
                        : ''
                    }`}
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1.5 mb-1">
                        <span className="font-bold text-xs text-slate-900 truncate">
                          {d.donor?.full_name || 'Anonymous Donor'}
                        </span>
                        {/* Status Badge */}
                        {d.is_flagged_fraud ? (
                          <span className="bg-red-100 text-red-800 text-[10px] font-bold px-1.5 py-0.2 rounded-sm shrink-0 flex items-center gap-0.5 border border-red-200">
                            <ShieldAlert className="w-2.5 h-2.5 text-red-600" />
                            FRAUD
                          </span>
                        ) : d.status === 'MATCHED' ? (
                          <span className="bg-emerald-100 text-emerald-800 text-[10px] font-bold px-1.5 py-0.2 rounded-sm shrink-0">
                            MATCHED
                          </span>
                        ) : d.status === 'FLAGGED_REVIEW' ? (
                          <span className="bg-amber-100 text-amber-800 text-[10px] font-bold px-1.5 py-0.2 rounded-sm shrink-0">
                            REVIEW
                          </span>
                        ) : d.status === 'EXTRACTED' ? (
                          <span className="bg-blue-100 text-blue-800 text-[10px] font-bold px-1.5 py-0.2 rounded-sm shrink-0">
                            EXTRACTED
                          </span>
                        ) : (
                          <span className="bg-red-100 text-red-800 text-[10px] font-bold px-1.5 py-0.2 rounded-sm shrink-0">
                            REJECTED
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-2 text-[11px] text-slate-500 font-mono">
                        <span>UTR: {d.extracted_utr || 'Unread'}</span>
                        <span>•</span>
                        <span className="font-bold text-slate-800 font-sans">
                          {d.extracted_amount ? `₹${d.extracted_amount.toLocaleString('en-IN')}` : '—'}
                        </span>
                      </div>
                    </div>

                    <ChevronRight className={`w-4 h-4 text-slate-400 shrink-0 ${isSelected ? 'text-emerald-600' : ''}`} />
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* RIGHT COLUMN: SPLIT SCREEN VERIFICATION VIEW (8 Cols on desktop) */}
        <div className="lg:col-span-8 bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden h-[750px] flex flex-col">
          {selectedDonation ? (
            <div className="flex-1 grid grid-cols-1 md:grid-cols-12 h-full divide-y md:divide-y-0 md:divide-x divide-slate-200 overflow-hidden">
              {/* SPLIT PANE 1: ZOOMABLE IMAGE VIEWER (6 cols on md) */}
              <div className="md:col-span-6 flex flex-col h-full bg-slate-900 relative overflow-hidden select-none">
                {/* Image Toolbar */}
                <div className="bg-slate-950/80 backdrop-blur-xs text-white px-3 py-2 flex items-center justify-between text-xs border-b border-slate-800 z-10">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[11px] text-slate-300">
                      Zoom: {Math.round(zoomLevel * 100)}%
                    </span>
                    {selectedDonation.ela_heatmap_url && (
                      <div className="flex items-center bg-slate-800 rounded p-0.5 text-[10px]">
                        <button
                          onClick={() => setViewMode('original')}
                          className={`px-2 py-0.5 rounded cursor-pointer transition-all ${
                            viewMode === 'original' ? 'bg-emerald-600 text-white font-bold' : 'text-slate-400 hover:text-white'
                          }`}
                        >
                          Original
                        </button>
                        <button
                          onClick={() => setViewMode('ela')}
                          className={`px-2 py-0.5 rounded cursor-pointer flex items-center gap-1 transition-all ${
                            viewMode === 'ela' ? 'bg-amber-600 text-white font-bold' : 'text-slate-400 hover:text-white'
                          }`}
                        >
                          <Activity className="w-3 h-3" />
                          <span>ELA Heatmap</span>
                        </button>
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={handleZoomIn}
                      className="p-1 hover:bg-slate-800 rounded text-slate-300 hover:text-white"
                      title="Zoom In"
                    >
                      <ZoomIn className="w-4 h-4" />
                    </button>
                    <button
                      onClick={handleZoomOut}
                      className="p-1 hover:bg-slate-800 rounded text-slate-300 hover:text-white"
                      title="Zoom Out"
                    >
                      <ZoomOut className="w-4 h-4" />
                    </button>
                    <button
                      onClick={handleRotate}
                      className="p-1 hover:bg-slate-800 rounded text-slate-300 hover:text-white"
                      title="Rotate 90deg"
                    >
                      <RotateCw className="w-4 h-4" />
                    </button>
                    <button
                      onClick={handleResetZoom}
                      className="p-1 hover:bg-slate-800 rounded text-slate-300 hover:text-white"
                      title="Reset Fit"
                    >
                      <Maximize2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Canvas / Image Container */}
                <div
                  onMouseDown={handleMouseDown}
                  onMouseMove={handleMouseMove}
                  onMouseUp={handleMouseUp}
                  onMouseLeave={handleMouseUp}
                  className={`flex-1 overflow-hidden relative flex items-center justify-center p-4 cursor-${
                    isDragging ? 'grabbing' : 'grab'
                  }`}
                >
                  <div
                    style={{
                      transform: `translate(${panPosition.x}px, ${panPosition.y}px) scale(${zoomLevel}) rotate(${rotation}deg)`,
                      transition: isDragging ? 'none' : 'transform 0.15s ease-out',
                    }}
                    className="relative max-h-full max-w-full flex items-center justify-center"
                  >
                    <img
                      src={
                        viewMode === 'ela' && selectedDonation.ela_heatmap_url
                          ? selectedDonation.ela_heatmap_url
                          : api.getScreenshotUrl(selectedDonation.screenshot_url)
                      }
                      alt={viewMode === 'ela' ? 'Error Level Analysis Heatmap' : 'Payment Receipt Screenshot'}
                      className="max-h-[580px] w-auto object-contain rounded-lg shadow-2xl border border-slate-800 pointer-events-none"
                    />

                    {/* ELA Mode Banner Overlay */}
                    {viewMode === 'ela' && (
                      <div className="absolute top-4 left-4 bg-amber-950/90 border border-amber-500 text-amber-300 text-[10px] font-mono px-2.5 py-1 rounded-md shadow-lg pointer-events-none flex items-center gap-1.5">
                        <Activity className="w-3.5 h-3.5 text-amber-400" />
                        <span>ELA Forensic Recompression (Q90) • Score: {(selectedDonation.tamper_score || 0).toFixed(2)}</span>
                      </div>
                    )}

                    {/* OCR Detection Highlighting Badges */}
                    {selectedDonation.extracted_utr && viewMode === 'original' && (
                      <div className="absolute bottom-6 left-4 bg-emerald-950/90 border border-emerald-500 text-emerald-300 text-[10px] font-mono px-2.5 py-1 rounded-md shadow-lg pointer-events-none">
                        Detected UTR: <strong>{selectedDonation.extracted_utr}</strong>
                      </div>
                    )}
                  </div>
                </div>

                {/* Bottom OCR Confidence Pill */}
                <div className="bg-slate-950/90 text-slate-400 text-[11px] px-3 py-1.5 flex items-center justify-between border-t border-slate-800">
                  <div className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                    <span>OCR Confidence: {(selectedDonation.ocr_confidence * 100).toFixed(0)}%</span>
                  </div>
                  <a
                    href={api.getScreenshotUrl(selectedDonation.screenshot_url)}
                    target="_blank"
                    rel="noreferrer"
                    className="text-emerald-400 hover:underline flex items-center gap-1"
                  >
                    <Eye className="w-3 h-3" />
                    <span>Open Full Image</span>
                  </a>
                </div>
              </div>

              {/* SPLIT PANE 2: VERIFICATION & EDIT CONTROLS (6 cols on md) */}
              <div className="md:col-span-6 flex flex-col h-full overflow-y-auto p-5 space-y-4 bg-white">
                {/* Match Status Banner */}
                <div className={`p-3.5 rounded-xl border flex items-start gap-3 ${
                  selectedDonation.status === 'MATCHED'
                    ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
                    : selectedDonation.status === 'FLAGGED_REVIEW'
                    ? 'bg-amber-50 border-amber-200 text-amber-900'
                    : selectedDonation.status === 'REJECTED'
                    ? 'bg-red-50 border-red-200 text-red-900'
                    : 'bg-blue-50 border-blue-200 text-blue-900'
                }`}>
                  {selectedDonation.status === 'MATCHED' ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
                  ) : selectedDonation.status === 'FLAGGED_REVIEW' ? (
                    <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                  ) : selectedDonation.status === 'REJECTED' ? (
                    <XCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
                  ) : (
                    <ScanLine className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
                  )}

                  <div className="text-xs">
                    <div className="font-bold text-sm">
                      {selectedDonation.status === 'MATCHED'
                        ? '🟢 Exact Match (Verified)'
                        : selectedDonation.status === 'FLAGGED_REVIEW'
                        ? '🟡 Review Needed / Fuzzy Match'
                        : selectedDonation.status === 'REJECTED'
                        ? '🔴 Rejected Submission'
                        : '🔵 Extracted Proof (Pending Bank Statement)'}
                    </div>
                    {selectedDonation.flagged_reason && (
                      <p className="mt-1 text-slate-700 leading-snug">
                        {selectedDonation.flagged_reason}
                      </p>
                    )}
                  </div>
                </div>

                {/* Anti-Fraud & Media Inspection Card */}
                <div className={`border rounded-xl p-3.5 space-y-3 ${
                  selectedDonation.is_flagged_fraud 
                    ? 'border-red-300 bg-red-50/40' 
                    : 'border-emerald-200 bg-emerald-50/20'
                }`}>
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 text-slate-800">
                      {selectedDonation.is_flagged_fraud ? (
                        <ShieldAlert className="w-4 h-4 text-red-600" />
                      ) : (
                        <ShieldCheck className="w-4 h-4 text-emerald-600" />
                      )}
                      <span>Anti-Fraud & Forensic Integrity</span>
                    </h3>
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                      selectedDonation.is_flagged_fraud
                        ? 'bg-red-200 text-red-900 border border-red-300'
                        : 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                    }`}>
                      {selectedDonation.is_flagged_fraud ? 'TAMPER RISK DETECTED' : 'FORENSIC CLEARANCE'}
                    </span>
                  </div>

                  {/* Fraud reasons if flagged */}
                  {selectedDonation.fraud_reasons && selectedDonation.fraud_reasons.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {selectedDonation.fraud_reasons.map((reason, idx) => (
                        <span key={idx} className="bg-red-100 border border-red-200 text-red-800 text-[10px] font-bold px-2 py-0.5 rounded-md flex items-center gap-1">
                          <AlertTriangle className="w-3 h-3 text-red-600" />
                          <span>{reason}</span>
                        </span>
                      ))}
                    </div>
                  )}

                  <div className="grid grid-cols-2 gap-2 text-xs">
                    {/* ELA Score Gauge */}
                    <div className="bg-white p-2.5 rounded-lg border border-slate-200 shadow-2xs">
                      <div className="flex items-center justify-between text-[10px] text-slate-500 mb-1">
                        <span>ELA Tamper Variance</span>
                        <span className={`font-bold ${((selectedDonation.tamper_score || 0) > 12.5) ? 'text-red-600' : 'text-emerald-600'}`}>
                          {(selectedDonation.tamper_score || 0).toFixed(1)} / 12.5 limit
                        </span>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                        <div 
                          className={`h-full rounded-full transition-all ${
                            (selectedDonation.tamper_score || 0) > 12.5 ? 'bg-red-500' : 'bg-emerald-500'
                          }`}
                          style={{ width: `${Math.min(((selectedDonation.tamper_score || 0) / 25) * 100, 100)}%` }}
                        />
                      </div>
                    </div>

                    {/* SHA-256 Digest */}
                    <div className="bg-white p-2.5 rounded-lg border border-slate-200 shadow-2xs">
                      <div className="flex items-center justify-between text-[10px] text-slate-500 mb-0.5">
                        <span className="flex items-center gap-1">
                          <Fingerprint className="w-3 h-3 text-slate-400" />
                          <span>SHA-256 Digest</span>
                        </span>
                        <span className="text-[9px] bg-slate-100 text-slate-600 px-1 rounded font-mono">Dedupe</span>
                      </div>
                      <div className="font-mono text-[10px] text-slate-700 truncate" title={selectedDonation.image_sha256 || 'N/A'}>
                        {selectedDonation.image_sha256 ? `${selectedDonation.image_sha256.substring(0, 16)}...` : 'Check Verified'}
                      </div>
                    </div>
                  </div>

                  {selectedDonation.ela_heatmap_url && (
                    <button
                      onClick={() => setViewMode(prev => prev === 'ela' ? 'original' : 'ela')}
                      className="w-full py-1.5 px-3 bg-white hover:bg-slate-50 border border-slate-200 rounded-lg text-xs font-semibold text-slate-700 flex items-center justify-center gap-1.5 cursor-pointer shadow-2xs transition-all"
                    >
                      <Activity className="w-3.5 h-3.5 text-amber-600" />
                      <span>{viewMode === 'ela' ? 'Switch Back to Original Receipt' : 'Inspect ELA Heatmap Layer'}</span>
                    </button>
                  )}
                </div>

                {/* CA Audit Trail & Compliance Card */}
                <div className="border border-slate-200 rounded-xl p-3.5 bg-slate-50/60 space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                      <FileCheck2 className="w-3.5 h-3.5 text-indigo-600" />
                      <span>CA Audit Trail (Form 10BD & 80G)</span>
                    </h3>
                    {selectedDonation.is_verified && (
                      <span className="text-[10px] font-bold bg-indigo-100 text-indigo-800 px-2 py-0.5 rounded font-mono">
                        {selectedDonation.bank_matched_mode || 'VERIFIED'}
                      </span>
                    )}
                  </div>

                  {selectedDonation.is_verified ? (
                    <div className="space-y-1.5 text-xs text-slate-600 bg-white p-3 rounded-lg border border-slate-200 shadow-2xs">
                      <div className="flex items-center justify-between">
                        <span className="text-slate-500 text-[11px]">Certified By CA/Admin:</span>
                        <strong className="text-slate-900 font-mono text-[11px]">{selectedDonation.verified_by_user || 'admin@raiseindia.org'}</strong>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-slate-500 text-[11px]">Audit Timestamp:</span>
                        <span className="text-slate-800 font-mono text-[11px]">
                          {selectedDonation.verified_at ? new Date(selectedDonation.verified_at).toLocaleString('en-IN') : 'N/A'}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-slate-500 text-[11px]">Reconciliation Mode:</span>
                        <span className="text-indigo-700 font-semibold">{selectedDonation.bank_matched_mode || 'AUTO_EXACT'}</span>
                      </div>
                      {selectedDonation.admin_audit_notes && (
                        <div className="pt-1.5 border-t border-slate-100 text-[11px]">
                          <span className="text-slate-500 block mb-0.5">Auditor Notes:</span>
                          <p className="italic text-slate-700 bg-slate-50 p-1.5 rounded">{selectedDonation.admin_audit_notes}</p>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="space-y-2.5 bg-white p-3 rounded-lg border border-slate-200 shadow-2xs">
                      <div>
                        <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                          Auditor / Compliance Officer ID
                        </label>
                        <input
                          type="text"
                          value={auditorUser}
                          onChange={(e) => setAuditorUser(e.target.value)}
                          placeholder="e.g. ca_audit@raiseindia.org"
                          className="w-full px-2.5 py-1.5 rounded border border-slate-300 text-xs font-mono"
                        />
                      </div>
                      <div>
                        <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                          CA Inspection Notes & Justification
                        </label>
                        <textarea
                          rows={2}
                          value={auditNotes}
                          onChange={(e) => setAuditNotes(e.target.value)}
                          placeholder="e.g. Cross-verified with core banking credit UTR. Approved for 80G tax certificate."
                          className="w-full px-2.5 py-1.5 rounded border border-slate-300 text-xs"
                        />
                      </div>
                    </div>
                  )}
                </div>

                {/* Donor Details Card */}
                <div className="border border-slate-200 rounded-xl p-3.5 bg-slate-50/50 space-y-2">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                      <User className="w-3.5 h-3.5 text-emerald-600" />
                      <span>Donor Details</span>
                    </h3>
                    {selectedDonation.donor?.pan_number && (
                      <span className="text-[11px] font-mono font-bold bg-slate-200 px-2 py-0.5 rounded text-slate-800">
                        PAN: {selectedDonation.donor.pan_number}
                      </span>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-xs text-slate-600">
                    <div>
                      <span className="text-slate-400 block text-[10px]">Full Name</span>
                      <strong className="text-slate-900">{selectedDonation.donor?.full_name || 'N/A'}</strong>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[10px]">Mobile</span>
                      <span className="text-slate-900">{selectedDonation.donor?.phone || 'N/A'}</span>
                    </div>
                    <div className="col-span-2">
                      <span className="text-slate-400 block text-[10px]">Email</span>
                      <span className="text-slate-900 truncate block">{selectedDonation.donor?.email || 'N/A'}</span>
                    </div>
                    {selectedDonation.donor?.address && (
                      <div className="col-span-2">
                        <span className="text-slate-400 block text-[10px]">Address</span>
                        <span className="text-slate-900 line-clamp-1">{selectedDonation.donor.address}</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* OCR Extracted Fields & Inline Edit Card */}
                <div className="border border-slate-200 rounded-xl p-3.5 space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                      <CreditCard className="w-3.5 h-3.5 text-emerald-600" />
                      <span>OCR Extracted Payment Values</span>
                    </h3>
                    {!isEditing ? (
                      <button
                        onClick={() => setIsEditing(true)}
                        className="text-xs text-emerald-700 hover:text-emerald-800 font-semibold flex items-center gap-1 cursor-pointer"
                      >
                        <Edit3 className="w-3.5 h-3.5" />
                        <span>Edit Digits</span>
                      </button>
                    ) : (
                      <div className="flex items-center gap-2">
                        <button
                          onClick={handleSaveEdit}
                          disabled={savingEdit}
                          className="text-xs bg-emerald-600 text-white px-2.5 py-1 rounded font-semibold flex items-center gap-1 hover:bg-emerald-700"
                        >
                          <Save className="w-3.5 h-3.5" />
                          <span>{savingEdit ? 'Saving...' : 'Save & Match'}</span>
                        </button>
                        <button
                          onClick={() => setIsEditing(false)}
                          className="text-xs text-slate-500 hover:text-slate-700"
                        >
                          Cancel
                        </button>
                      </div>
                    )}
                  </div>

                  {isEditing ? (
                    <div className="space-y-3 bg-slate-50 p-3 rounded-lg border border-slate-200">
                      <div>
                        <div className="flex justify-between text-[11px] text-slate-600 mb-1">
                          <label className="font-semibold">12-Digit UTR / UPI Ref</label>
                          <span className="font-mono text-slate-400">{editUtr.length}/12 digits</span>
                        </div>
                        <input
                          type="text"
                          maxLength={20}
                          value={editUtr}
                          onChange={(e) => setEditUtr(e.target.value)}
                          className="w-full px-3 py-1.5 rounded border border-slate-300 text-xs font-mono font-bold tracking-wider"
                          placeholder="e.g. 428910293812"
                        />
                      </div>
                      <div>
                        <label className="block text-[11px] font-semibold text-slate-600 mb-1">Amount (INR)</label>
                        <input
                          type="number"
                          value={editAmount}
                          onChange={(e) => setEditAmount(e.target.value)}
                          className="w-full px-3 py-1.5 rounded border border-slate-300 text-xs font-bold"
                          placeholder="5000"
                        />
                      </div>
                    </div>
                  ) : (
                    <div className="grid grid-cols-2 gap-3 text-xs">
                      <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                        <span className="text-slate-400 block text-[10px]">Extracted 12-Digit UTR</span>
                        <strong className="text-slate-900 font-mono text-sm tracking-wider">
                          {selectedDonation.extracted_utr || 'Not Found'}
                        </strong>
                      </div>
                      <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                        <span className="text-slate-400 block text-[10px]">Extracted Amount</span>
                        <strong className="text-emerald-700 text-sm">
                          {selectedDonation.extracted_amount ? `₹${selectedDonation.extracted_amount.toLocaleString('en-IN')}` : 'Not Found'}
                        </strong>
                      </div>
                    </div>
                  )}
                </div>

                {/* Matched Bank Statement Entry Card */}
                {selectedDonation.matched_statement && (
                  <div className="border border-emerald-200 rounded-xl p-3.5 bg-emerald-50/30 space-y-2">
                    <div className="flex items-center justify-between">
                      <h3 className="text-xs font-bold text-emerald-800 uppercase tracking-wider flex items-center gap-1.5">
                        <Building2 className="w-3.5 h-3.5 text-emerald-600" />
                        <span>Matched Bank Credit Entry</span>
                      </h3>
                      <button
                        onClick={handleUnlink}
                        className="text-[11px] text-red-600 hover:text-red-800 font-semibold flex items-center gap-1"
                        title="Unlink statement"
                      >
                        <Unlink className="w-3 h-3" />
                        <span>Unlink</span>
                      </button>
                    </div>

                    <div className="text-xs space-y-1">
                      <p className="font-mono text-[11px] text-slate-800 bg-white p-2 rounded border border-emerald-100">
                        {selectedDonation.matched_statement.narration}
                      </p>
                      <div className="flex items-center justify-between text-slate-600 pt-1">
                        <span>Date: <strong>{selectedDonation.matched_statement.transaction_date}</strong></span>
                        <span>Credit Amount: <strong className="text-emerald-700">₹{selectedDonation.matched_statement.credit_amount.toLocaleString('en-IN')}</strong></span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Fuzzy Candidates Selector (when not verified or flagged) */}
                {!selectedDonation.is_verified && candidates.length > 0 && (
                  <div className="border border-amber-200 rounded-xl p-3.5 bg-amber-50/20 space-y-2">
                    <h3 className="text-xs font-bold text-amber-800 uppercase tracking-wider flex items-center gap-1.5">
                      <SlidersHorizontal className="w-3.5 h-3.5 text-amber-600" />
                      <span>Suggested Bank Matches ({candidates.length} candidates)</span>
                    </h3>
                    <p className="text-[11px] text-slate-500">
                      Top matching bank credits based on UTR edit distance and amount matching:
                    </p>

                    <div className="space-y-1.5 max-h-36 overflow-y-auto divide-y divide-slate-100">
                      {candidates.map((cand, idx) => (
                        <div key={idx} className="pt-1.5 flex items-center justify-between gap-2 text-xs">
                          <div className="min-w-0 flex-1">
                            <p className="font-mono text-[11px] text-slate-800 truncate">
                              {cand.statement_entry.narration}
                            </p>
                            <div className="flex items-center gap-2 text-[10px] text-slate-500">
                              <span>₹{cand.statement_entry.credit_amount}</span>
                              <span>•</span>
                              <span>{cand.statement_entry.transaction_date}</span>
                              <span className="bg-amber-100 text-amber-800 px-1 rounded font-semibold">
                                Score: {(cand.confidence_score * 100).toFixed(0)}%
                              </span>
                            </div>
                          </div>
                          <button
                            onClick={() => handleManualLink(cand.statement_entry.id)}
                            className="px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-[11px] shrink-0 flex items-center gap-1 cursor-pointer"
                          >
                            <Link2 className="w-3 h-3" />
                            <span>Link</span>
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 80G Receipt Preview Card if already verified */}
                {selectedDonation.tax_receipt && (
                  <div className="border border-indigo-200 rounded-xl p-3.5 bg-indigo-50/30 flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2.5">
                      <FileCheck2 className="w-6 h-6 text-indigo-600 shrink-0" />
                      <div>
                        <div className="text-xs font-bold text-indigo-900">
                          80G Tax Exemption Certificate Generated
                        </div>
                        <div className="text-[11px] text-slate-600 font-mono">
                          Receipt No: {selectedDonation.tax_receipt.receipt_number}
                        </div>
                      </div>
                    </div>
                    <a
                      href={api.getReceiptPdfUrl(selectedDonation.tax_receipt.pdf_url)}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold px-3 py-1.5 rounded-lg shadow-2xs"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>Download PDF</span>
                    </a>
                  </div>
                )}

                {/* Bottom Action Buttons */}
                <div className="pt-2 border-t border-slate-100 flex flex-wrap items-center gap-2">
                  {!selectedDonation.is_verified && (
                    <button
                      onClick={handleVerify}
                      className={`flex-1 py-2.5 px-4 rounded-xl text-white text-xs font-bold shadow-xs flex items-center justify-center gap-1.5 cursor-pointer transition-all ${
                        selectedDonation.is_flagged_fraud
                          ? 'bg-gradient-to-r from-amber-600 to-red-600 hover:from-amber-700 hover:to-red-700'
                          : 'bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700'
                      }`}
                    >
                      <Check className="w-4 h-4" />
                      <span>
                        {selectedDonation.is_flagged_fraud
                          ? 'CA Override & Issue 80G Certificate'
                          : 'Mark as Verified & Generate 80G'}
                      </span>
                    </button>
                  )}

                  {selectedDonation.status !== 'REJECTED' && (
                    <button
                      onClick={handleReject}
                      className="py-2.5 px-4 rounded-xl bg-red-50 hover:bg-red-100 text-red-700 border border-red-200 text-xs font-semibold flex items-center justify-center gap-1.5 cursor-pointer"
                    >
                      <X className="w-4 h-4" />
                      <span>Reject / Fraud Duplicate</span>
                    </button>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-8 text-slate-400">
              <ScanLine className="w-12 h-12 text-slate-300 mb-3" />
              <h3 className="text-sm font-bold text-slate-700">No Donation Selected</h3>
              <p className="text-xs text-slate-500 max-w-sm mt-1">
                Select a payment screenshot from the queue on the left to inspect OCR values, view zoomable proof, and reconcile against bank statement credits.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
