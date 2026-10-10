export interface Donor {
  id: string;
  full_name: string;
  pan_number: string;
  phone: string;
  email: string;
  address?: string;
  created_at: string;
}

export interface BankStatementEntry {
  id: string;
  transaction_date: string;
  narration: string;
  extracted_utr?: string;
  credit_amount: number;
  balance?: number;
  is_reconciled: boolean;
  statement_batch_id?: string;
  is_balance_continuous?: boolean;
  is_suspicious_pdf_source?: boolean;
  math_discrepancy_details?: any;
  created_at: string;
}

export interface TaxReceipt {
  id: string;
  donation_id: string;
  receipt_number: string;
  financial_year: string;
  eligible_amount: number;
  pdf_path: string;
  pdf_url: string;
  issued_at: string;
}

export type DonationStatus = 'PENDING' | 'PENDING_OCR' | 'EXTRACTED' | 'MATCHED' | 'SUCCESS' | 'FLAGGED_REVIEW' | 'REJECTED';

export interface Donation {
  id: string;
  donor_id?: string;
  donor?: Donor;
  screenshot_url: string;
  extracted_utr?: string;
  extracted_amount?: number;
  extracted_date?: string;
  raw_ocr_payload?: Record<string, any>;
  ocr_confidence: number;
  status: DonationStatus;
  matched_statement_id?: string;
  matched_statement?: BankStatementEntry;
  is_verified: boolean;
  flagged_reason?: string;
  tax_receipt?: TaxReceipt;
  // Anti-fraud & CA audit fields
  image_sha256?: string;
  tamper_score?: number;
  ela_heatmap_url?: string;
  is_flagged_fraud?: boolean;
  fraud_reasons?: string[];
  verified_by_user?: string;
  verified_at?: string;
  bank_matched_mode?: string;
  admin_audit_notes?: string;
  created_at: string;
  updated_at: string;
}

export interface ReconciliationStats {
  total_donations: number;
  matched_count: number;
  pending_count: number;
  flagged_count: number;
  fraud_flagged_count?: number;
  rejected_count: number;
  total_amount_collected: number;
  reconciled_amount: number;
  match_rate_percentage: number;
  total_statement_entries: number;
  unreconciled_statement_count: number;
}

export interface FuzzyCandidate {
  statement_entry: BankStatementEntry;
  utr_distance: number;
  amount_diff: number;
  days_diff: number;
  confidence_score: number;
  match_type: string;
}

export interface AuditReportData {
  total_entries: number;
  entries_with_math_discrepancies: number;
  suspicious_source_entries: number;
  discrepancies: Array<{
    id: string;
    transaction_date: string;
    narration: string;
    credit_amount: number;
    balance?: number;
    is_suspicious_pdf_source: boolean;
    math_discrepancy_details: any;
  }>;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api';

export const api = {
  // Public donation submission
  async submitPublicDonation(formData: FormData) {
    const res = await fetch(`${API_BASE}/donations/public-submit`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to submit donation' }));
      throw new Error(err.detail || 'Failed to submit donation');
    }
    return res.json();
  },

  // Public receipt lookup
  async lookupReceipt(pan?: string, trackingId?: string) {
    const params = new URLSearchParams();
    if (pan) params.append('pan', pan);
    if (trackingId) params.append('tracking_id', trackingId);

    const res = await fetch(`${API_BASE}/receipts/lookup?${params.toString()}`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Record not found' }));
      throw new Error(err.detail || 'Record not found');
    }
    return res.json();
  },

  // Admin donations list
  async getDonations(status?: string, search?: string) {
    const params = new URLSearchParams();
    if (status && status !== 'ALL') params.append('status', status);
    if (search) params.append('search', search);

    const res = await fetch(`${API_BASE}/donations/?${params.toString()}`);
    if (!res.ok) throw new Error('Failed to fetch donations');
    return res.json() as Promise<Donation[]>;
  },

  // Admin single donation
  async getDonation(id: string) {
    const res = await fetch(`${API_BASE}/donations/${id}`);
    if (!res.ok) throw new Error('Donation not found');
    return res.json() as Promise<Donation>;
  },

  // Inline edit & save
  async updateDonation(id: string, data: Partial<Donation>) {
    const res = await fetch(`${API_BASE}/donations/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Failed to update donation');
    return res.json() as Promise<Donation>;
  },

  // Verify donation & issue official receipt
  async verifyDonation(id: string, auditData?: { verified_by_user?: string; admin_audit_notes?: string; bank_matched_mode?: string }) {
    const res = await fetch(`${API_BASE}/donations/${id}/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(auditData || { verified_by_user: 'admin@raiseindia.org' }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to verify donation' }));
      throw new Error(err.detail || 'Failed to verify donation');
    }
    return res.json() as Promise<Donation>;
  },

  // Reject donation
  async rejectDonation(id: string, reason?: string) {
    const params = new URLSearchParams();
    if (reason) params.append('reason', reason);

    const res = await fetch(`${API_BASE}/donations/${id}/reject?${params.toString()}`, {
      method: 'POST',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to reject donation' }));
      throw new Error(err.detail || 'Failed to reject donation');
    }
    return res.json() as Promise<Donation>;
  },

  // Bulk screenshot upload
  async bulkUploadScreenshots(files: File[]) {
    const formData = new FormData();
    for (const f of files) {
      formData.append('files', f);
    }
    const res = await fetch(`${API_BASE}/donations/bulk-upload`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) throw new Error('Failed to upload screenshots');
    return res.json() as Promise<Donation[]>;
  },

  // Delete donation
  async deleteDonation(id: string) {
    const res = await fetch(`${API_BASE}/donations/${id}`, {
      method: 'DELETE',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to delete donation' }));
      throw new Error(err.detail || 'Failed to delete donation');
    }
    return res.json();
  },

  // Bank Statement upload
  async uploadBankStatement(file: File) {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/bank-statement/upload`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to upload bank statement' }));
      throw new Error(err.detail || 'Failed to upload bank statement');
    }
    return res.json() as Promise<Donation[]>;
  },

  // Bank Statement entries
  async getBankStatementEntries(isReconciled?: boolean, search?: string) {
    const params = new URLSearchParams();
    if (isReconciled !== undefined) params.append('is_reconciled', String(isReconciled));
    if (search) params.append('search', search);

    const res = await fetch(`${API_BASE}/bank-statement/entries?${params.toString()}`);
    if (!res.ok) throw new Error('Failed to fetch bank statements');
    return res.json() as Promise<BankStatementEntry[]>;
  },

  // Bank Statement Audit Report
  async getStatementAuditReport() {
    const res = await fetch(`${API_BASE}/bank-statement/audit-report`);
    if (!res.ok) throw new Error('Failed to fetch statement audit report');
    return res.json() as Promise<AuditReportData>;
  },

  // Reconciliation stats
  async getReconciliationStats() {
    const res = await fetch(`${API_BASE}/reconciliation/stats`);
    if (!res.ok) throw new Error('Failed to fetch reconciliation stats');
    return res.json() as Promise<ReconciliationStats>;
  },

  // Trigger auto-reconciliation
  async triggerReconciliation() {
    const res = await fetch(`${API_BASE}/reconciliation/run`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Failed to run reconciliation');
    return res.json();
  },

  // Fuzzy candidates for a donation
  async getFuzzyCandidates(donationId: string) {
    const res = await fetch(`${API_BASE}/reconciliation/candidates/${donationId}`);
    if (!res.ok) throw new Error('Failed to fetch fuzzy candidates');
    return res.json() as Promise<FuzzyCandidate[]>;
  },

  // Manual link & verify
  async manualLinkAndVerify(
    donationId: string, 
    statementId: string, 
    auditData?: { verified_by_user?: string; admin_audit_notes?: string; bank_matched_mode?: string }
  ) {
    const params = new URLSearchParams({
      donation_id: donationId,
      statement_id: statementId,
    });
    const res = await fetch(`${API_BASE}/reconciliation/manual-link?${params.toString()}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(auditData || { verified_by_user: 'admin@raiseindia.org', bank_matched_mode: 'MANUAL_OVERRIDE' }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to link donation with bank entry' }));
      throw new Error(err.detail || 'Failed to link donation with bank entry');
    }
    return res.json() as Promise<Donation>;
  },

  // Unlink
  async unlinkDonation(donationId: string) {
    const res = await fetch(`${API_BASE}/reconciliation/unlink/${donationId}`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Failed to unlink donation');
    return res.json() as Promise<Donation>;
  },

  // Asset URLs
  getScreenshotUrl(urlPath: string) {
    if (!urlPath) return '';
    if (urlPath.startsWith('http')) return urlPath;
    return urlPath.startsWith('/') ? urlPath : `/${urlPath}`;
  },

  getReceiptPdfUrl(urlPath: string) {
    if (!urlPath) return '';
    if (urlPath.startsWith('http')) return urlPath;
    return urlPath.startsWith('/') ? urlPath : `/${urlPath}`;
  },

  getForm10BdExportUrl() {
    return `${API_BASE}/receipts/export/form-10bd`;
  },

  getSampleTemplateUrl() {
    return `${API_BASE}/bank-statement/sample-template`;
  },
};
