"use client";

import React, { useState, useEffect } from "react";
import confetti from "canvas-confetti";
import { api } from "@/lib/api";
import {
  UploadCloud,
  FileSpreadsheet,
  CheckCircle2,
  Clock,
  RefreshCw,
  Search,
  ExternalLink,
  Edit2,
  Check,
  X,
  AlertTriangle,
  Download,
  Copy,
  CheckCheck,
  Eye,
  IndianRupee,
  Layers,
  ArrowRight,
  ShieldCheck,
  ShieldAlert,
  Shield,
  Fingerprint,
  User,
  FileText,
  Building2,
  Sparkles,
  Trash2,
} from "lucide-react";

interface DonorInfo {
  full_name: string;
  pan_number?: string;
  phone?: string;
  email?: string;
}

interface DonationItem {
  id: string;
  donor_id?: string;
  donor?: DonorInfo;
  donor_name?: string;
  extracted_utr: string;
  extracted_amount: number;
  status: string;
  is_verified: boolean;
  screenshot_url?: string;
  image_sha256?: string;
  is_duplicate_hash?: boolean;
  tamper_score?: number;
  is_flagged_fraud?: boolean;
  fraud_reasons?: string[];
  matched_statement?: {
    narration: string;
    transaction_date: string;
    credit_amount: number;
  };
}

export default function SingleScreenReconciliation() {
  const [donations, setDonations] = useState<DonationItem[]>([]);
  const [loadingScreenshots, setLoadingScreenshots] = useState(false);
  const [loadingStatement, setLoadingStatement] = useState(false);
  const [screenshotFiles, setScreenshotFiles] = useState<FileList | null>(null);
  const [statementFile, setStatementFile] = useState<File | null>(null);
  const [donorName, setDonorName] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editUtrValue, setEditUtrValue] = useState("");
  const [previewItem, setPreviewItem] = useState<DonationItem | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [isDraggingScreenshots, setIsDraggingScreenshots] = useState(false);
  const [isDraggingStatement, setIsDraggingStatement] = useState(false);
  const [statusNotification, setStatusNotification] = useState<{ message: string; type: "success" | "info" | "error" } | null>(null);
  const [confirmingDeleteId, setConfirmingDeleteId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const showNotification = (message: string, type: "success" | "info" | "error" = "info") => {
    setStatusNotification({ message, type });
    setTimeout(() => {
      setStatusNotification(null);
    }, 4500);
  };

  const fireConfetti = () => {
    if (typeof window !== "undefined") {
      try {
        confetti({
          particleCount: 110,
          spread: 75,
          origin: { y: 0.6 },
          colors: ["#4f46e5", "#059669", "#0891b2", "#d97706", "#7c3aed"],
        });
      } catch (e) {
        console.error("Confetti trigger error", e);
      }
    }
  };

  const fetchTransactions = async () => {
    try {
      const res = await fetch("/api/donations");
      if (res.ok) {
        const data = await res.json();
        setDonations(data);
      }
    } catch (err) {
      console.error("Failed to load transactions", err);
    }
  };

  useEffect(() => {
    fetchTransactions();
  }, []);

  // 1. Upload Payment Screenshots (Single / Bulk) with Automated Donor / Payer Name
  const handleUploadScreenshots = async () => {
    if (!screenshotFiles || screenshotFiles.length === 0) return;
    setLoadingScreenshots(true);

    const formData = new FormData();
    for (let i = 0; i < screenshotFiles.length; i++) {
      formData.append("files", screenshotFiles[i]);
    }
    // If donorName was entered, pass it; otherwise omit so OCR extracts donor name automatically
    if (donorName.trim()) {
      formData.append("donor_name", donorName.trim());
    }

    try {
      const res = await fetch("/api/donations/bulk-upload", {
        method: "POST",
        body: formData,
      });
      if (res.ok) {
        const resultData = await res.json();
        setScreenshotFiles(null);
        setDonorName("");
        // Reset file input
        const input = document.getElementById("screenshot-input") as HTMLInputElement;
        if (input) input.value = "";
        
        await fetchTransactions();
        
        // Check if any uploaded screenshot instantly matched
        const matchedUploaded = (resultData || []).some((item: DonationItem) => item.is_verified || item.status === "MATCHED");
        if (matchedUploaded) {
          fireConfetti();
          showNotification(`Processed ${resultData.length} receipt(s) — Bank statement match verified! 🟢`, "success");
        } else {
          showNotification(`Successfully processed ${resultData.length} receipt(s). Forensic inspection complete.`, "info");
        }
      } else {
        const errText = await res.text();
        showNotification(`Upload failed: ${errText}`, "error");
      }
    } catch (err) {
      console.error("Screenshot upload failed", err);
      showNotification("Screenshot upload failed. Please check network connection.", "error");
    } finally {
      setLoadingScreenshots(false);
    }
  };

  // Dedicated Row Deletion
  const handleDeleteDonation = async (donationId: string, utr?: string) => {
    setDeletingId(donationId);
    try {
      const res = await fetch(`/api/donations/${donationId}`, {
        method: "DELETE",
      });
      if (res.ok) {
        setDonations((prev) => prev.filter((d) => d.id !== donationId));
        setConfirmingDeleteId(null);
        showNotification(`Receipt record ${utr ? `(UTR: ${utr})` : ""} successfully deleted.`, "info");
      } else {
        const err = await res.json().catch(() => ({ detail: "Failed to delete donation record" }));
        showNotification(`Delete failed: ${err.detail || err.message || "Unknown error"}`, "error");
      }
    } catch (err) {
      console.error("Delete failed", err);
      showNotification("Failed to delete record. Please check network connection.", "error");
    } finally {
      setDeletingId(null);
    }
  };

  // 2. Upload Bank Statement & Trigger Auto-Match
  const handleUploadStatement = async () => {
    if (!statementFile) return;
    setLoadingStatement(true);

    const formData = new FormData();
    formData.append("file", statementFile);

    try {
      const res = await fetch("/api/bank-statement/upload", {
        method: "POST",
        body: formData,
      });
      if (res.ok) {
        fireConfetti();
        setStatementFile(null);
        const input = document.getElementById("statement-input") as HTMLInputElement;
        if (input) input.value = "";
        await fetchTransactions();
        showNotification("Bank statement reconciled successfully! 🎉 Matching UTR records updated.", "success");
      } else {
        const errData = await res.json().catch(() => ({ detail: "Failed to parse statement" }));
        showNotification(`Statement error: ${errData.detail || "Upload failed"}`, "error");
      }
    } catch (err) {
      console.error("Statement upload failed", err);
      showNotification("Statement upload failed. Please check file format.", "error");
    } finally {
      setLoadingStatement(false);
    }
  };

  // 3. Inline Edit UTR in case of OCR misread
  const handleSaveUtr = async (donationId: string) => {
    try {
      let res = await fetch(`/api/donations/${donationId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ extracted_utr: editUtrValue }),
      });
      if (!res.ok) {
        res = await fetch(`/api/donations/${donationId}/edit`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ extracted_utr: editUtrValue }),
        });
      }
      if (res.ok) {
        const updatedItem = await res.json();
        setEditingId(null);
        await fetchTransactions();
        if (updatedItem.is_verified || updatedItem.status === "MATCHED") {
          fireConfetti();
          showNotification("UTR updated and successfully matched with bank record! 🟢", "success");
        } else {
          showNotification("UTR updated successfully.", "info");
        }
      }
    } catch (err) {
      console.error("Failed to update UTR", err);
      showNotification("Failed to update UTR. Try again.", "error");
    }
  };

  // 4. 1-Click Copy UTR to Clipboard
  const handleCopyUtr = async (utr: string, id: string) => {
    if (!utr) return;
    try {
      await navigator.clipboard.writeText(utr);
      setCopiedId(id);
      setTimeout(() => {
        setCopiedId(null);
      }, 2000);
    } catch (err) {
      console.error("Copy failed", err);
    }
  };

  // Derived Stats
  const totalCount = donations.length;
  const matchedList = donations.filter((d) => d.is_verified || d.status === "MATCHED");
  const matchedCount = matchedList.length;
  const pendingCount = totalCount - matchedCount;
  const matchedAmount = matchedList.reduce((acc, curr) => acc + (Number(curr.extracted_amount) || 0), 0);
  const totalAmount = donations.reduce((acc, curr) => acc + (Number(curr.extracted_amount) || 0), 0);
  const authenticCount = donations.filter((d) => !d.is_flagged_fraud && d.status !== "REJECTED" && (!d.tamper_score || d.tamper_score <= 25)).length;
  const flaggedCount = totalCount - authenticCount;

  const filtered = donations.filter((d) => {
    const q = searchQuery.toLowerCase();
    const donorNameStr = (d.donor?.full_name || "").toLowerCase();
    const utrStr = (d.extracted_utr || "").toLowerCase();
    const narrationStr = (d.matched_statement?.narration || "").toLowerCase();
    return utrStr.includes(q) || narrationStr.includes(q) || donorNameStr.includes(q);
  });

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 p-4 sm:p-6 lg:p-10 font-sans selection:bg-indigo-600 selection:text-white bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(99,102,241,0.08),rgba(248,250,252,0))]">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* Top Header with Corporate Branding */}
        <header className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-5 border-b border-slate-200 pb-6 bg-white/60 p-5 rounded-2xl backdrop-blur-md shadow-xs">
          <div className="flex items-center gap-4">
            {/* Official Logo Box */}
            <div className="w-13 h-13 sm:w-14 sm:h-14 bg-white rounded-2xl p-1.5 shadow-sm border border-slate-200 flex items-center justify-center overflow-hidden flex-shrink-0 transition-transform hover:scale-105">
              <img
                src="/raise-india-logo.png"
                alt="Raise India Foundation Official Logo"
                className="w-full h-full object-contain"
              />
            </div>

            <div>
              <div className="flex flex-wrap items-center gap-2.5">
                <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900">
                  Raise India Foundation
                </h1>
                <span className="text-[11px] font-bold uppercase tracking-wider bg-indigo-50 text-indigo-700 border border-indigo-200 px-2.5 py-0.5 rounded-full font-mono flex items-center gap-1 shadow-2xs">
                  <Fingerprint className="w-3 h-3 text-indigo-600" /> VerifyAI Cockpit
                </span>
              </div>
              <p className="text-xs text-slate-500 flex flex-wrap items-center gap-2 mt-1">
                <span>Automated UPI Payment Proof Forensics</span>
                <span>•</span>
                <span>Bank Statement Auto-Reconciler</span>
                <span>•</span>
                <span className="text-indigo-600 font-medium font-mono">Regd No. 274409</span>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <a
              href="/api/bank-statement/sample-template"
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-2 px-3.5 py-2 bg-white border border-slate-200 hover:border-slate-300 hover:bg-slate-50 text-xs text-slate-700 font-semibold rounded-xl transition shadow-2xs"
              title="Download pre-formatted bank statement template"
            >
              <Download className="w-3.5 h-3.5 text-indigo-600"/> Sample Excel
            </a>
            <button
              onClick={fetchTransactions}
              className="flex items-center gap-2 px-3.5 py-2 bg-indigo-600 hover:bg-indigo-700 text-xs text-white font-semibold rounded-xl transition shadow-sm hover:shadow active:scale-98"
              title="Refresh ledger records"
            >
              <RefreshCw className="w-3.5 h-3.5 text-white"/> Refresh
            </button>
          </div>
        </header>

        {/* Status Toast / Banner */}
        {statusNotification && (
          <div
            className={`p-3.5 rounded-xl border text-xs font-semibold flex items-center justify-between transition-all shadow-xs animate-in fade-in slide-in-from-top-2 ${
              statusNotification.type === "success"
                ? "bg-emerald-50 border-emerald-200 text-emerald-800"
                : statusNotification.type === "error"
                ? "bg-rose-50 border-rose-200 text-rose-800"
                : "bg-indigo-50 border-indigo-200 text-indigo-800"
            }`}
          >
            <div className="flex items-center gap-2.5">
              {statusNotification.type === "success" && <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />}
              {statusNotification.type === "error" && <AlertTriangle className="w-4 h-4 text-rose-600 flex-shrink-0" />}
              {statusNotification.type === "info" && <Clock className="w-4 h-4 text-indigo-600 flex-shrink-0" />}
              <span>{statusNotification.message}</span>
            </div>
            <button
              onClick={() => setStatusNotification(null)}
              className="text-slate-400 hover:text-slate-600 text-xs p-1"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* 2 Side-by-Side Creative Upload Hubs */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Card 1: Screenshots Upload */}
          <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-sm hover:shadow-md transition space-y-4 relative group">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-indigo-50 text-indigo-600 border border-indigo-100">
                  <UploadCloud className="w-5 h-5"/>
                </div>
                <div>
                  <h2 className="text-base font-bold text-slate-900">1. Upload Payment Receipts</h2>
                  <p className="text-xs text-slate-500">Single or Bulk screenshots (.png, .jpg, .webp, .zip)</p>
                </div>
              </div>
              <span className="text-[11px] px-2.5 py-1 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200 font-mono font-semibold flex items-center gap-1">
                <Shield className="w-3 h-3 text-indigo-600" /> Forensics & OCR
              </span>
            </div>

            {/* Payer / Donor Name Input */}
            <div>
              <label htmlFor="donor-name-input" className="block text-xs font-semibold text-slate-700 mb-1.5 flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <User className="w-3.5 h-3.5 text-indigo-600" /> Donor / Payer Name
                </span>
                <span className="text-[11px] text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-md font-medium">Auto-extracted via OCR if blank</span>
              </label>
              <input
                type="text"
                id="donor-name-input"
                value={donorName}
                onChange={(e) => setDonorName(e.target.value)}
                placeholder="Leave blank for automatic OCR name detection (e.g. Rohan Sharma)"
                className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-indigo-500 focus:bg-white transition"
              />
            </div>

            {/* Drag & Drop Box */}
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setIsDraggingScreenshots(true);
              }}
              onDragLeave={() => setIsDraggingScreenshots(false)}
              onDrop={(e) => {
                e.preventDefault();
                setIsDraggingScreenshots(false);
                if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                  setScreenshotFiles(e.dataTransfer.files);
                }
              }}
              className={`border-2 border-dashed rounded-xl p-5 text-center transition ${
                isDraggingScreenshots
                  ? "border-indigo-500 bg-indigo-50/50"
                  : "border-slate-300 hover:border-indigo-400 bg-slate-50/60"
              }`}
            >
              <input
                type="file"
                multiple
                accept="image/*,.zip"
                id="screenshot-input"
                className="hidden"
                onChange={(e) => setScreenshotFiles(e.target.files)}
              />
              <label htmlFor="screenshot-input" className="cursor-pointer block space-y-2">
                <UploadCloud className="w-8 h-8 mx-auto text-indigo-500 group-hover:scale-105 transition" />
                <span className="text-sm font-semibold text-slate-800 block">
                  {screenshotFiles && screenshotFiles.length > 0
                    ? `✓ ${screenshotFiles.length} file(s) selected`
                    : "Drag & drop receipts or browse"}
                </span>
                <span className="text-xs text-slate-500 block">
                  Supports Google Pay, PhonePe, Paytm, BHIM, Cred, Amazon Pay
                </span>
              </label>
            </div>

            <button
              onClick={handleUploadScreenshots}
              disabled={!screenshotFiles || screenshotFiles.length === 0 || loadingScreenshots}
              className="w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 disabled:hover:bg-indigo-600 text-white rounded-xl text-sm font-semibold transition flex items-center justify-center gap-2 shadow-sm hover:shadow active:scale-98"
            >
              {loadingScreenshots ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin"/> Running Forensics & OCR Extraction...
                </>
              ) : (
                <>
                  <span>Extract UTRs & Run Authenticity Audit</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>

          {/* Card 2: Bank Statement Upload */}
          <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-sm hover:shadow-md transition space-y-4 relative group">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-emerald-50 text-emerald-600 border border-emerald-100">
                  <FileSpreadsheet className="w-5 h-5"/>
                </div>
                <div>
                  <h2 className="text-base font-bold text-slate-900">2. Upload Bank Statement</h2>
                  <p className="text-xs text-slate-500">Excel or CSV ledger file (.xlsx, .csv)</p>
                </div>
              </div>
              <span className="text-[11px] px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 font-mono font-semibold">
                12-Digit Auto-Match
              </span>
            </div>

            <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-600 flex items-center justify-between">
              <div>
                <p className="font-semibold text-slate-800">Auto-Reconciliation Engine</p>
                <p className="text-[11px] text-slate-500">Automatically parses UPI narrations & matches UTR credits</p>
              </div>
              <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded font-semibold text-[10px]">
                Active
              </span>
            </div>

            {/* Drag & Drop Box */}
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setIsDraggingStatement(true);
              }}
              onDragLeave={() => setIsDraggingStatement(false)}
              onDrop={(e) => {
                e.preventDefault();
                setIsDraggingStatement(false);
                if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                  setStatementFile(e.dataTransfer.files[0]);
                }
              }}
              className={`border-2 border-dashed rounded-xl p-5 text-center transition ${
                isDraggingStatement
                  ? "border-emerald-500 bg-emerald-50/50"
                  : "border-slate-300 hover:border-emerald-400 bg-slate-50/60"
              }`}
            >
              <input
                type="file"
                accept=".xlsx, .csv, .xls"
                id="statement-input"
                className="hidden"
                onChange={(e) => setStatementFile(e.target.files ? e.target.files[0] : null)}
              />
              <label htmlFor="statement-input" className="cursor-pointer block space-y-2">
                <FileSpreadsheet className="w-8 h-8 mx-auto text-emerald-600 group-hover:scale-105 transition" />
                <span className="text-sm font-semibold text-slate-800 block">
                  {statementFile ? `✓ ${statementFile.name}` : "Drag & drop Bank Statement file or browse"}
                </span>
                <span className="text-xs text-slate-500 block">
                  Matches UTR numbers from credit narrations automatically
                </span>
              </label>
            </div>

            <button
              onClick={handleUploadStatement}
              disabled={!statementFile || loadingStatement}
              className="w-full py-2.5 px-4 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-40 disabled:hover:bg-emerald-600 text-white rounded-xl text-sm font-semibold transition flex items-center justify-center gap-2 shadow-sm hover:shadow active:scale-98"
            >
              {loadingStatement ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin"/> Verifying Statement Records...
                </>
              ) : (
                <>
                  <span>Reconcile & Match Transaction IDs</span>
                  <CheckCircle2 className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </div>

        {/* Real-Time Metric Ticker */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {/* Total Uploaded */}
          <div className="bg-white border border-slate-200/90 p-4.5 rounded-2xl shadow-xs hover:shadow-sm transition">
            <div className="flex items-center justify-between">
              <p className="text-xs text-slate-500 font-semibold">Total Receipts</p>
              <div className="p-1.5 rounded-lg bg-slate-100 text-slate-600">
                <Layers className="w-4 h-4" />
              </div>
            </div>
            <p className="text-2xl font-bold text-slate-900 mt-2">{totalCount} Receipts</p>
            <p className="text-[11px] text-slate-500 mt-0.5">
              <span className="text-emerald-700 font-semibold">{authenticCount} Authentic</span>
              {flaggedCount > 0 && <span className="text-rose-600 font-semibold ml-1.5">• {flaggedCount} Flagged</span>}
            </p>
          </div>

          {/* Bank Matched */}
          <div className="bg-white border border-emerald-200 p-4.5 rounded-2xl shadow-xs hover:shadow-sm transition">
            <div className="flex items-center justify-between">
              <p className="text-xs text-emerald-700 font-semibold">Bank Matched</p>
              <div className="p-1.5 rounded-lg bg-emerald-50 text-emerald-600">
                <CheckCircle2 className="w-4 h-4" />
              </div>
            </div>
            <p className="text-2xl font-bold text-emerald-700 mt-2">{matchedCount} SUCCESS</p>
            <p className="text-[11px] text-emerald-600 mt-0.5 font-medium">Reconciled against official bank credit</p>
          </div>

          {/* Pending Statement */}
          <div className="bg-white border border-amber-200 p-4.5 rounded-2xl shadow-xs hover:shadow-sm transition">
            <div className="flex items-center justify-between">
              <p className="text-xs text-amber-700 font-semibold">Pending Statement</p>
              <div className="p-1.5 rounded-lg bg-amber-50 text-amber-600">
                <Clock className="w-4 h-4" />
              </div>
            </div>
            <p className="text-2xl font-bold text-amber-700 mt-2">{pendingCount} Waiting</p>
            <p className="text-[11px] text-amber-600 mt-0.5 font-medium">Awaiting bank statement credit</p>
          </div>

          {/* Reconciled Value */}
          <div className="bg-white border border-slate-200/90 p-4.5 rounded-2xl shadow-xs hover:shadow-sm transition">
            <div className="flex items-center justify-between">
              <p className="text-xs text-slate-500 font-semibold">Reconciled ₹</p>
              <div className="p-1.5 rounded-lg bg-indigo-50 text-indigo-600">
                <IndianRupee className="w-4 h-4" />
              </div>
            </div>
            <p className="text-2xl font-bold text-slate-900 mt-2">₹{matchedAmount.toLocaleString("en-IN")}</p>
            <p className="text-[11px] text-slate-500 mt-0.5">
              {totalAmount > 0 ? `${Math.round((matchedAmount / totalAmount) * 100)}% of ₹${totalAmount.toLocaleString("en-IN")}` : "0% volume reconciled"}
            </p>
          </div>
        </div>

        {/* Live Interactive Reconciliation Ledger */}
        <div className="bg-white border border-slate-200/90 rounded-2xl overflow-hidden shadow-sm hover:shadow-md transition">
          <div className="p-4 sm:p-5 border-b border-slate-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 bg-slate-50/50">
            <div>
              <h3 className="font-bold text-slate-900 text-base flex items-center gap-2">
                Live Verification Ledger
              </h3>
              <p className="text-xs text-slate-500">
                Transactions automatically show <span className="text-emerald-700 font-semibold">SUCCESS</span> when their 12-digit UTR is matched in the bank statement.
              </p>
            </div>
            <div className="relative w-full sm:w-80">
              <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400"/>
              <input
                type="text"
                placeholder="Search UTR, Donor Name, or Narration..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-4 py-2 bg-white border border-slate-300 focus:border-indigo-500 rounded-xl text-xs text-slate-800 placeholder-slate-400 focus:outline-none transition shadow-2xs"
              />
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-100/70 text-slate-600 text-xs uppercase font-bold tracking-wider">
                  <th className="py-3 px-4">#</th>
                  <th className="py-3 px-4">Proof</th>
                  <th className="py-3 px-4">Donor Name</th>
                  <th className="py-3 px-4">Proof Authenticity</th>
                  <th className="py-3 px-4">Transaction ID (UTR)</th>
                  <th className="py-3 px-4">Amount (₹)</th>
                  <th className="py-3 px-4">Bank Match Status</th>
                  <th className="py-3 px-4">Statement Credit Details</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filtered.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="text-center py-20 text-slate-500">
                      <div className="max-w-md mx-auto space-y-3">
                        <div className="w-14 h-14 mx-auto rounded-2xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 shadow-2xs">
                          <UploadCloud className="w-7 h-7" />
                        </div>
                        <h4 className="font-bold text-slate-800 text-base">No Receipts Uploaded Yet</h4>
                        <p className="text-xs text-slate-500 leading-relaxed">
                          Your live reconciliation ledger is currently clean. Upload UPI payment receipt screenshots on the left or drop an official bank statement on the right to start automated verification and matching.
                        </p>
                        <div className="inline-flex items-center gap-2 px-3 py-1 bg-slate-100 text-slate-600 rounded-full text-[11px] font-medium">
                          <span>0 Pending</span> • <span>0 Reconciled</span> • <span>Ready to Ingest</span>
                        </div>
                      </div>
                    </td>
                  </tr>
                ) : (
                  filtered.map((item, index) => {
                    const isMatched = item.is_verified || item.status === "MATCHED";
                    const isCopied = copiedId === item.id;
                    const isNonPayment = item.status === "REJECTED" || (item.fraud_reasons && item.fraud_reasons.some(r => r.includes("NON_PAYMENT_IMAGE") || r.toLowerCase().includes("non-payment")));
                    const isDuplicate = item.is_duplicate_hash || (item.fraud_reasons && item.fraud_reasons.some(r => r.toLowerCase().includes("duplicate")));
                    const isTampered = item.is_flagged_fraud || (item.tamper_score !== undefined && item.tamper_score > 25);
                    const scoreText = item.tamper_score !== undefined ? `${item.tamper_score.toFixed(1)}%` : "0.0%";
                    const donorDisplayName = isNonPayment ? "Unverified Uploader" : (item.donor?.full_name || item.donor_name || "Verified Donor");

                    return (
                      <tr key={item.id} className="hover:bg-slate-50 transition group">
                        <td className="py-3.5 px-4 text-slate-500 text-xs font-mono">{index + 1}</td>
                        
                        {/* Proof (Clickable thumbnail with popup preview modal) */}
                        <td className="py-3.5 px-4">
                          {item.screenshot_url ? (
                            <button
                              onClick={() => setPreviewItem(item)}
                              className="group/thumb flex items-center gap-2 p-1 rounded-lg bg-indigo-50/60 hover:bg-indigo-100/80 border border-indigo-200/80 transition"
                              title="Click to view proof forensics preview"
                            >
                              <img
                                src={api.getScreenshotUrl(item.screenshot_url)}
                                alt="Proof thumbnail"
                                className="w-9 h-9 object-cover rounded-md border border-slate-200 shadow-2xs group-hover/thumb:scale-105 transition-transform"
                                onError={(e) => {
                                  (e.target as HTMLImageElement).src =
                                    "https://placehold.co/100x100/f8fafc/64748b?text=Receipt";
                                }}
                              />
                              <span className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-700 pr-1.5">
                                <Eye className="w-3.5 h-3.5"/> Preview
                              </span>
                            </button>
                          ) : (
                            <span className="text-xs text-slate-400 italic">None</span>
                          )}
                        </td>

                        {/* Donor Name */}
                        <td className="py-3.5 px-4 font-semibold text-slate-900">
                          <div className="flex items-center gap-1.5">
                            <User className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
                            <span className="truncate max-w-[150px]">{donorDisplayName}</span>
                          </div>
                        </td>

                        {/* Proof Authenticity (🟢 Genuine vs 🟡 Edited vs 🔴 Duplicate vs 🔴 Non-Payment) */}
                        <td className="py-3.5 px-4">
                          {isNonPayment ? (
                            <div className="flex flex-col gap-0.5" title={(item.fraud_reasons || []).join(" | ") || "Non-payment random image detected."}>
                              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-rose-50 text-rose-700 border border-rose-200">
                                <ShieldAlert className="w-3.5 h-3.5 text-rose-600 flex-shrink-0" />
                                <span>NON-PAYMENT / INVALID</span>
                              </span>
                              <span className="text-[10px] text-rose-600 font-mono pl-1">Random media • No UPI data</span>
                            </div>
                          ) : isDuplicate ? (
                            <div className="flex flex-col gap-0.5" title="Identical screenshot file hash already submitted in system.">
                              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-rose-50 text-rose-700 border border-rose-200">
                                <ShieldAlert className="w-3.5 h-3.5 text-rose-600 flex-shrink-0" />
                                <span>DUPLICATE PROOF</span>
                              </span>
                              <span className="text-[10px] text-rose-600 font-mono pl-1">Identical file hash</span>
                            </div>
                          ) : isTampered ? (
                            <div className="flex flex-col gap-0.5" title={(item.fraud_reasons || []).join(" | ") || "Pixel tampering detected."}>
                              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
                                <AlertTriangle className="w-3.5 h-3.5 text-amber-600 flex-shrink-0" />
                                <span>EDITED / SUSPICIOUS</span>
                              </span>
                              <span className="text-[10px] text-amber-700 font-mono pl-1">ELA: {scoreText} • Flagged</span>
                            </div>
                          ) : (
                            <div className="flex flex-col gap-0.5" title="Passed Error Level Analysis (ELA) and uniqueness checks.">
                              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                                <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0" />
                                <span>GENUINE PROOF</span>
                              </span>
                              <span className="text-[10px] text-emerald-600 font-mono pl-1">ELA: {scoreText} • Clean</span>
                            </div>
                          )}
                        </td>

                        {/* Transaction ID (UTR) with 1-Click Copy & Pencil Edit */}
                        <td className="py-3.5 px-4">
                          {editingId === item.id ? (
                            <div className="flex items-center gap-1.5">
                              <input
                                type="text"
                                value={editUtrValue}
                                onChange={(e) => setEditUtrValue(e.target.value)}
                                placeholder="12-digit UTR"
                                className="w-36 px-2.5 py-1 bg-white border border-indigo-500 text-xs text-slate-900 rounded-lg font-mono focus:outline-none"
                              />
                              <button
                                onClick={() => handleSaveUtr(item.id)}
                                title="Save UTR"
                                className="p-1.5 text-emerald-600 hover:bg-emerald-50 rounded-lg transition"
                              >
                                <Check className="w-3.5 h-3.5"/>
                              </button>
                              <button
                                onClick={() => setEditingId(null)}
                                title="Cancel"
                                className="p-1.5 text-slate-400 hover:bg-slate-100 rounded-lg transition"
                              >
                                <X className="w-3.5 h-3.5"/>
                              </button>
                            </div>
                          ) : (
                            <div className="flex items-center gap-2">
                              {item.extracted_utr ? (
                                <span className="font-mono font-bold text-slate-900 tracking-wide text-xs">
                                  {item.extracted_utr}
                                </span>
                              ) : (
                                <span className="font-mono text-xs text-rose-600 italic font-medium">
                                  {isNonPayment ? "No UTR (Rejected)" : "Extracting..."}
                                </span>
                              )}

                              {/* 1-Click Copy Button */}
                              {item.extracted_utr && (
                                <button
                                  onClick={() => handleCopyUtr(item.extracted_utr, item.id)}
                                  title={isCopied ? "Copied!" : "1-Click Copy UTR"}
                                  className={`p-1 rounded transition ${
                                    isCopied
                                      ? "text-emerald-600 bg-emerald-50"
                                      : "opacity-40 group-hover:opacity-80 hover:opacity-100 text-slate-500 hover:text-slate-800"
                                  }`}
                                >
                                  {isCopied ? (
                                    <CheckCheck className="w-3.5 h-3.5 text-emerald-600" />
                                  ) : (
                                    <Copy className="w-3.5 h-3.5" />
                                  )}
                                </button>
                              )}

                              {/* Inline Pencil Edit Button */}
                              {item.extracted_utr && (
                                <button
                                  onClick={() => {
                                    setEditingId(item.id);
                                    setEditUtrValue(item.extracted_utr || "");
                                  }}
                                  title="Edit UTR if OCR misread"
                                  className="p-1 opacity-40 group-hover:opacity-80 hover:opacity-100 text-slate-500 hover:text-slate-800 transition"
                                >
                                  <Edit2 className="w-3.5 h-3.5"/>
                                </button>
                              )}
                            </div>
                          )}
                        </td>

                        {/* Amount */}
                        <td className="py-3.5 px-4 font-bold text-slate-900">
                          {item.extracted_amount ? (
                            `₹${Number(item.extracted_amount || 0).toLocaleString("en-IN")}`
                          ) : (
                            <span className="text-xs text-slate-400 font-normal italic">—</span>
                          )}
                        </td>

                        {/* Bank Match Status (🟢 SUCCESS vs 🟡 PENDING vs 🔴 REJECTED) */}
                        <td className="py-3.5 px-4">
                          {isNonPayment || item.status === "REJECTED" ? (
                            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-rose-50 text-rose-700 border border-rose-200">
                              <X className="w-3.5 h-3.5 text-rose-600"/> REJECTED
                            </span>
                          ) : isMatched ? (
                            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 shadow-2xs animate-in fade-in">
                              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600"/> SUCCESS
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                              <Clock className="w-3.5 h-3.5 text-amber-600"/> PENDING
                            </span>
                          )}
                        </td>

                        {/* Statement Credit Details */}
                        <td className="py-3.5 px-4 text-xs text-slate-600 max-w-sm">
                          {item.matched_statement ? (
                            <div>
                              <span
                                title={item.matched_statement.narration}
                                className="font-mono text-slate-800 text-[11px] block truncate font-medium"
                              >
                                {item.matched_statement.narration}
                              </span>
                              <span className="text-[10px] text-slate-400">
                                Date: {item.matched_statement.transaction_date || "Cleared"}
                              </span>
                            </div>
                          ) : (
                            <span className="text-slate-400 italic">Awaiting bank statement credit</span>
                          )}
                        </td>

                        {/* Actions: Receipt Download & Dedicated Row Deletion */}
                        <td className="py-3.5 px-4 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            {isMatched && (
                              <a
                                href={`/api/receipts/${item.id}/pdf`}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-semibold bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 rounded-lg transition shadow-2xs"
                                title="Download official donation receipt"
                              >
                                <Download className="w-3.5 h-3.5 text-indigo-600"/> Receipt
                              </a>
                            )}

                            {confirmingDeleteId === item.id ? (
                              <div className="inline-flex items-center gap-1 bg-rose-50 border border-rose-200 rounded-lg p-1 animate-in fade-in">
                                <span className="text-[11px] font-semibold text-rose-700 px-1">Delete?</span>
                                <button
                                  onClick={() => handleDeleteDonation(item.id, item.extracted_utr)}
                                  disabled={deletingId === item.id}
                                  className="p-1 bg-rose-600 hover:bg-rose-700 text-white rounded transition disabled:opacity-50"
                                  title="Confirm Delete"
                                >
                                  {deletingId === item.id ? (
                                    <RefreshCw className="w-3 h-3 animate-spin" />
                                  ) : (
                                    <Check className="w-3 h-3" />
                                  )}
                                </button>
                                <button
                                  onClick={() => setConfirmingDeleteId(null)}
                                  className="p-1 hover:bg-rose-100 text-rose-700 rounded transition"
                                  title="Cancel"
                                >
                                  <X className="w-3 h-3" />
                                </button>
                              </div>
                            ) : (
                              <button
                                onClick={() => setConfirmingDeleteId(item.id)}
                                className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg border border-transparent hover:border-rose-200 transition"
                                title="Delete transaction record"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

      </div>

      {/* Lightbox Image Preview Modal with Forensics Inspection Details */}
      {previewItem && (
        <div
          className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in"
          onClick={() => setPreviewItem(null)}
        >
          <div
            className="bg-white border border-slate-200 p-5 rounded-2xl max-w-xl w-full relative shadow-xl space-y-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
                  <Eye className="w-4 h-4 text-indigo-600" /> Receipt Proof Forensics
                </span>
                <span className="font-mono text-xs text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
                  UTR: {previewItem.extracted_utr || "N/A"}
                </span>
              </div>
              <button
                onClick={() => setPreviewItem(null)}
                className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-100 transition"
              >
                <X className="w-4 h-4"/>
              </button>
            </div>

            {/* Forensics Inspection Strip */}
            <div className={`p-3 rounded-xl border text-xs flex items-center justify-between ${
              previewItem.is_flagged_fraud || (previewItem.tamper_score !== undefined && previewItem.tamper_score > 25)
                ? "bg-rose-50 border-rose-200 text-rose-800"
                : "bg-emerald-50 border-emerald-200 text-emerald-800"
            }`}>
              <div className="flex items-center gap-2.5">
                {previewItem.is_flagged_fraud || (previewItem.tamper_score !== undefined && previewItem.tamper_score > 25) ? (
                  <>
                    <ShieldAlert className="w-4 h-4 text-rose-600 flex-shrink-0" />
                    <div>
                      <span className="font-bold">FLAGGED: Potential Tampering Detected</span>
                      <p className="text-[11px] text-rose-600">
                        {(previewItem.fraud_reasons && previewItem.fraud_reasons.join(" • ")) || "Pixel tampering deviation detected."}
                      </p>
                    </div>
                  </>
                ) : (
                  <>
                    <ShieldCheck className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                    <div>
                      <span className="font-bold">VERIFIED AUTHENTIC: Passed Image Forensics</span>
                      <p className="text-[11px] text-emerald-600">
                        Error Level Analysis clean (ELA: {previewItem.tamper_score ? `${previewItem.tamper_score.toFixed(1)}%` : "0.0%"}). Unique file hash.
                      </p>
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* Image Preview Viewport */}
            <div className="bg-slate-100 rounded-xl p-2 flex items-center justify-center max-h-[60vh] overflow-hidden border border-slate-200">
              <img
                src={api.getScreenshotUrl(previewItem.screenshot_url)}
                alt="Payment Proof"
                className="w-full h-auto max-h-[55vh] object-contain rounded-lg shadow-2xs"
                onError={(e) => {
                  (e.target as HTMLImageElement).src =
                    "https://placehold.co/600x800/f8fafc/0f172a?text=Receipt+Preview+Unavailable";
                }}
              />
            </div>

            <div className="flex items-center justify-between pt-1 border-t border-slate-100">
              <div className="text-xs text-slate-500">
                <span>Payer: <b className="text-slate-800">{previewItem.donor?.full_name || "Anonymous Payer"}</b></span>
                <span className="ml-3 font-semibold text-slate-800">₹{Number(previewItem.extracted_amount || 0).toLocaleString("en-IN")}</span>
              </div>
              <div className="flex items-center gap-2">
                <a
                  href={api.getScreenshotUrl(previewItem.screenshot_url)}
                  target="_blank"
                  rel="noreferrer"
                  className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-xs font-semibold text-slate-700 rounded-lg transition inline-flex items-center gap-1"
                >
                  <ExternalLink className="w-3.5 h-3.5" /> Raw Image
                </a>
                <button
                  onClick={() => setPreviewItem(null)}
                  className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-xs font-semibold text-white rounded-lg transition"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
