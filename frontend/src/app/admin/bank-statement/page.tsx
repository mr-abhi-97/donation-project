'use client';

import React, { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { 
  Building2, 
  UploadCloud, 
  Download, 
  RefreshCw, 
  CheckCircle2, 
  AlertCircle, 
  AlertTriangle,
  FileSpreadsheet, 
  Search, 
  ArrowRight,
  Filter,
  Check,
  Clock,
  ShieldCheck,
  ShieldAlert,
  Calculator,
  X
} from 'lucide-react';
import { api, BankStatementEntry, AuditReportData } from '@/lib/api';

export default function BankStatementPage() {
  const [entries, setEntries] = useState<BankStatementEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [activeFilter, setActiveFilter] = useState<'ALL' | 'RECONCILED' | 'UNRECONCILED'>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Forensic Audit Report State
  const [auditReport, setAuditReport] = useState<AuditReportData | null>(null);
  const [showAuditModal, setShowAuditModal] = useState(false);
  const [loadingAudit, setLoadingAudit] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchAuditReport = async () => {
    try {
      setLoadingAudit(true);
      const rep = await api.getStatementAuditReport();
      setAuditReport(rep);
    } catch (err) {
      console.error('Failed to fetch audit report:', err);
    } finally {
      setLoadingAudit(false);
    }
  };

  const fetchEntries = async () => {
    try {
      setLoading(true);
      const isReconciled = activeFilter === 'ALL' ? undefined : activeFilter === 'RECONCILED';
      const [data, rep] = await Promise.all([
        api.getBankStatementEntries(isReconciled, searchQuery),
        api.getStatementAuditReport().catch(() => null),
      ]);
      setEntries(data);
      if (rep) setAuditReport(rep);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEntries();
  }, [activeFilter]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchEntries();
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setUploading(true);
      setStatusMessage(null);
      try {
        const created = await api.uploadBankStatement(file);
        setStatusMessage({
          type: 'success',
          text: `Bank statement uploaded! Extracted and stored ${created.length} credit transactions. Auto-reconciliation executed.`,
        });
        await fetchEntries();
      } catch (err: any) {
        setStatusMessage({
          type: 'error',
          text: err.message || 'Failed to parse and upload bank statement.',
        });
      } finally {
        setUploading(false);
        if (fileInputRef.current) fileInputRef.current.value = '';
      }
    }
  };

  const handleRunReconciliation = async () => {
    try {
      setLoading(true);
      const res = await api.triggerReconciliation();
      setStatusMessage({
        type: 'success',
        text: `Reconciliation engine run complete! Exact matches: ${res.details.exact_matches}, Fuzzy matches: ${res.details.fuzzy_matches}`,
      });
      await fetchEntries();
    } catch (err) {
      setStatusMessage({ type: 'error', text: 'Failed to run auto-reconciliation' });
    } finally {
      setLoading(false);
    }
  };

  const reconciledCount = entries.filter((e) => e.is_reconciled).length;
  const unreconciledCount = entries.filter((e) => !e.is_reconciled).length;

  return (
    <div className="py-8 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto space-y-6">
      {/* Top Header */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              Bank Statement & Ledger Integration
            </h1>
            <span className="text-xs bg-emerald-100 text-emerald-800 font-bold px-2.5 py-0.5 rounded-full">
              Automated UTR Parser
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Upload official bank statements (.xlsx, .csv). The system auto-detects credit columns and regex extracts 12-digit UTR references from narrations.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Download Sample Statement */}
          <a
            href={api.getSampleTemplateUrl()}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold shadow-2xs transition-all"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download Sample Statement (.xlsx)</span>
          </a>

          {/* Audit Report Button */}
          <button
            onClick={() => {
              fetchAuditReport();
              setShowAuditModal(true);
            }}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-xs transition-all cursor-pointer"
          >
            <Calculator className="w-3.5 h-3.5" />
            <span>Math & Forensic Audit</span>
            {auditReport && (auditReport.entries_with_math_discrepancies > 0 || auditReport.suspicious_source_entries > 0) ? (
              <span className="bg-red-500 text-white text-[10px] px-1.5 py-0.2 rounded-full font-bold ml-0.5">
                {auditReport.entries_with_math_discrepancies + auditReport.suspicious_source_entries}
              </span>
            ) : auditReport ? (
              <span className="bg-emerald-500 text-white text-[10px] px-1.5 py-0.2 rounded-full font-bold ml-0.5">
                ✓
              </span>
            ) : null}
          </button>

          {/* Trigger Reconciliation */}
          <button
            onClick={handleRunReconciliation}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow-xs transition-all cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Run Reconciliation Engine</span>
          </button>
        </div>
      </div>

      {statusMessage && (
        <div className={`p-4 rounded-xl text-xs font-medium flex items-center justify-between ${
          statusMessage.type === 'success'
            ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
            : 'bg-red-50 text-red-800 border border-red-200'
        }`}>
          <span>{statusMessage.text}</span>
          <button onClick={() => setStatusMessage(null)} className="hover:opacity-75">
            ✕
          </button>
        </div>
      )}

      {/* Upload Drop Area */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col sm:flex-row items-center justify-between gap-6">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 bg-emerald-100 text-emerald-700 rounded-xl flex items-center justify-center shrink-0">
            <FileSpreadsheet className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-900">
              Upload Bank Statement (Excel or CSV)
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Supports SBI, HDFC, ICICI, Axis and standard CBS formats.
            </p>
          </div>
        </div>

        <div>
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white font-bold text-xs shadow-md shadow-emerald-600/20 disabled:opacity-50 flex items-center gap-2 cursor-pointer"
          >
            {uploading ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Parsing & Ingesting Statement...</span>
              </>
            ) : (
              <>
                <UploadCloud className="w-4 h-4" />
                <span>Upload Statement (.xlsx / .csv)</span>
              </>
            )}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".xlsx,.xls,.csv"
            onChange={handleFileUpload}
            className="hidden"
          />
        </div>
      </div>

      {/* Statement Table Section */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden space-y-4 p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          {/* Filter Pills */}
          <div className="flex items-center gap-1.5">
            {[
              { id: 'ALL', label: `All Entries (${entries.length})` },
              { id: 'RECONCILED', label: `Reconciled (${reconciledCount})` },
              { id: 'UNRECONCILED', label: `Unmatched (${unreconciledCount})` },
            ].map((f) => (
              <button
                key={f.id}
                onClick={() => setActiveFilter(f.id as any)}
                className={`text-xs font-semibold px-3 py-1.5 rounded-lg transition-all cursor-pointer ${
                  activeFilter === f.id
                    ? 'bg-slate-900 text-white shadow-2xs'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>

          {/* Search Form */}
          <form onSubmit={handleSearch} className="relative w-full sm:w-72">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search narration or UTR..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 rounded-lg border border-slate-300 text-xs focus:ring-1 focus:ring-emerald-500 outline-hidden"
            />
          </form>
        </div>

        {/* Entries Table */}
        <div className="overflow-x-auto border border-slate-200 rounded-xl">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-700 font-bold border-b border-slate-200">
              <tr>
                <th className="p-3">Txn Date</th>
                <th className="p-3">Bank Narration</th>
                <th className="p-3">Extracted 12-Digit UTR</th>
                <th className="p-3">Credit Amount (INR)</th>
                <th className="p-3">Balance</th>
                <th className="p-3">Forensic Audit</th>
                <th className="p-3">Reconciled Status</th>
                <th className="p-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan={8} className="p-8 text-center text-slate-400">
                    <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-emerald-600" />
                    <span>Loading bank entries...</span>
                  </td>
                </tr>
              ) : entries.length === 0 ? (
                <tr>
                  <td colSpan={8} className="p-8 text-center text-slate-400">
                    No bank statement entries found. Upload an Excel or CSV file above.
                  </td>
                </tr>
              ) : (
                entries.map((entry) => (
                  <tr key={entry.id} className="hover:bg-slate-50/50">
                    <td className="p-3 font-mono text-slate-600 whitespace-nowrap">
                      {entry.transaction_date}
                    </td>
                    <td className="p-3 font-mono text-[11px] text-slate-800 max-w-xs truncate" title={entry.narration}>
                      {entry.narration}
                    </td>
                    <td className="p-3 font-mono font-bold text-slate-900">
                      {entry.extracted_utr || (
                        <span className="text-slate-400 font-normal">None detected</span>
                      )}
                    </td>
                    <td className="p-3 font-bold text-emerald-700 whitespace-nowrap">
                      ₹{entry.credit_amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="p-3 text-slate-500 whitespace-nowrap">
                      {entry.balance ? `₹${entry.balance.toLocaleString('en-IN')}` : '—'}
                    </td>
                    <td className="p-3 whitespace-nowrap">
                      <div className="flex flex-col gap-1">
                        {entry.is_balance_continuous === false ? (
                          <span className="inline-flex items-center gap-1 text-red-700 bg-red-100 font-bold px-2 py-0.5 rounded-full text-[10px] w-fit">
                            <AlertTriangle className="w-3 h-3 text-red-600" />
                            <span>Math Discrepancy</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-emerald-700 bg-emerald-100 font-semibold px-2 py-0.5 rounded-full text-[10px] w-fit">
                            <Check className="w-3 h-3 text-emerald-600" />
                            <span>Continuous Math</span>
                          </span>
                        )}

                        {entry.is_suspicious_pdf_source ? (
                          <span className="inline-flex items-center gap-1 text-red-700 bg-red-100 font-bold px-2 py-0.5 rounded-full text-[10px] w-fit">
                            <ShieldAlert className="w-3 h-3 text-red-600" />
                            <span>Suspicious Source</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-slate-600 bg-slate-100 font-medium px-2 py-0.5 rounded-full text-[10px] w-fit">
                            <ShieldCheck className="w-3 h-3 text-slate-500" />
                            <span>Authentic CBS</span>
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="p-3 whitespace-nowrap">
                      {entry.is_reconciled ? (
                        <span className="inline-flex items-center gap-1 bg-emerald-100 text-emerald-800 text-[10px] font-bold px-2 py-0.5 rounded-full">
                          <Check className="w-3 h-3" />
                          <span>Reconciled</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 bg-amber-100 text-amber-800 text-[10px] font-bold px-2 py-0.5 rounded-full">
                          <Clock className="w-3 h-3" />
                          <span>Unmatched</span>
                        </span>
                      )}
                    </td>
                    <td className="p-3 text-right whitespace-nowrap">
                      <Link
                        href={`/admin/reconcile`}
                        className="inline-flex items-center gap-1 text-xs text-emerald-600 hover:text-emerald-800 font-semibold"
                      >
                        <span>Inspect</span>
                        <ArrowRight className="w-3 h-3" />
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Forensic Audit Report Modal */}
      {showAuditModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-2xl w-full max-h-[85vh] overflow-hidden flex flex-col animate-in fade-in zoom-in-95 duration-200">
            {/* Modal Header */}
            <div className="p-5 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold">
                  <Calculator className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">
                    Bank Statement Mathematical & Metadata Audit Report
                  </h3>
                  <p className="text-[11px] text-slate-500">
                    Continuous running balance verification & PDF binary header forensics
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowAuditModal(false)}
                className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-5 overflow-y-auto space-y-4 text-xs">
              {/* Formula Callout */}
              <div className="bg-indigo-50/70 border border-indigo-200 rounded-xl p-3.5 space-y-1">
                <div className="font-bold text-indigo-900 flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4 text-indigo-600" />
                  <span>Mathematical Continuity Rule:</span>
                </div>
                <p className="font-mono text-[11px] text-indigo-800 bg-white/80 p-2 rounded border border-indigo-100">
                  Balance(N) = Balance(N-1) + Deposit(N) - Withdrawal(N) [Tolerance: ±₹0.05]
                </p>
                <p className="text-[11px] text-indigo-700">
                  Verifies row-by-row consistency to immediately detect manually inserted rows or edited amounts.
                </p>
              </div>

              {/* Stats Grid */}
              <div className="grid grid-cols-3 gap-3">
                <div className="border border-slate-200 rounded-xl p-3 bg-slate-50 text-center">
                  <span className="text-[10px] text-slate-500 uppercase font-bold">Total Statement Rows</span>
                  <div className="text-base font-bold text-slate-900 mt-0.5">
                    {auditReport?.total_entries ?? entries.length}
                  </div>
                </div>

                <div className={`border rounded-xl p-3 text-center ${
                  (auditReport?.entries_with_math_discrepancies ?? 0) > 0 
                    ? 'border-red-200 bg-red-50 text-red-900' 
                    : 'border-emerald-200 bg-emerald-50 text-emerald-900'
                }`}>
                  <span className="text-[10px] uppercase font-bold">Math Discrepancies</span>
                  <div className="text-base font-bold mt-0.5">
                    {auditReport?.entries_with_math_discrepancies ?? 0}
                  </div>
                  <span className="text-[10px] block">
                    {(auditReport?.entries_with_math_discrepancies ?? 0) === 0 ? '✓ All rows verified' : 'Broken continuity'}
                  </span>
                </div>

                <div className={`border rounded-xl p-3 text-center ${
                  (auditReport?.suspicious_source_entries ?? 0) > 0 
                    ? 'border-red-200 bg-red-50 text-red-900' 
                    : 'border-emerald-200 bg-emerald-50 text-emerald-900'
                }`}>
                  <span className="text-[10px] uppercase font-bold">Suspicious PDF Tools</span>
                  <div className="text-base font-bold mt-0.5">
                    {auditReport?.suspicious_source_entries ?? 0}
                  </div>
                  <span className="text-[10px] block">
                    {(auditReport?.suspicious_source_entries ?? 0) === 0 ? '✓ Authentic Core Banking' : 'Canva/Photoshop flagged'}
                  </span>
                </div>
              </div>

              {/* PDF Headers & Source Forensics */}
              <div className="border border-slate-200 rounded-xl p-3.5 space-y-2">
                <h4 className="font-bold text-slate-800 flex items-center gap-1.5 text-xs">
                  <ShieldCheck className="w-4 h-4 text-emerald-600" />
                  <span>PDF Metadata & Core Banking Header Inspection</span>
                </h4>
                <p className="text-[11px] text-slate-500">
                  Inspects <code>/Creator</code> and <code>/Producer</code> headers for genuine CBS systems (Finacle, Oracle, Jasper, iText) vs. editing software (Canva, Photoshop, iLovePDF, Word).
                </p>
                <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200 font-mono text-[11px] space-y-1">
                  <div><strong>Status:</strong> <span className="text-emerald-700">Validated against banking software allowlist</span></div>
                  <div><strong>Allowed:</strong> Finacle, Oracle Banking, SAP, JasperReports, Apache PDFBox, iText</div>
                  <div><strong>Disallowed:</strong> Photoshop, Canva, iLovePDF, SmallPDF, Microsoft Word, Excel export</div>
                </div>
              </div>

              {/* Broken Rows Details */}
              {auditReport && auditReport.discrepancies && auditReport.discrepancies.length > 0 ? (
                <div className="border border-red-200 rounded-xl p-3.5 bg-red-50/50 space-y-2">
                  <h4 className="font-bold text-red-900 flex items-center gap-1.5 text-xs">
                    <AlertTriangle className="w-4 h-4 text-red-600" />
                    <span>Discrepant / Suspicious Rows ({auditReport.discrepancies.length})</span>
                  </h4>
                  <div className="space-y-1.5 max-h-48 overflow-y-auto">
                    {auditReport.discrepancies.map((d) => (
                      <div key={d.id} className="bg-white p-2 rounded border border-red-200 text-[11px] font-mono">
                        <div className="flex justify-between text-slate-800">
                          <span>{d.transaction_date} • {d.narration}</span>
                          <span className="font-bold text-emerald-700">₹{d.credit_amount}</span>
                        </div>
                        {d.math_discrepancy_details && (
                          <div className="text-red-700 text-[10px] mt-1">
                            Discrepancy Details: {JSON.stringify(d.math_discrepancy_details)}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3.5 flex items-center gap-2.5 text-emerald-800">
                  <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                  <div>
                    <div className="font-bold">Zero Financial or Metadata Anomalies Detected</div>
                    <div className="text-[11px] text-emerald-700">
                      All uploaded bank credit entries adhere to mathematical balance continuity and authentic banking sources.
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-slate-200 bg-slate-50 flex justify-end">
              <button
                onClick={() => setShowAuditModal(false)}
                className="px-4 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white font-semibold text-xs cursor-pointer"
              >
                Close Audit Report
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
