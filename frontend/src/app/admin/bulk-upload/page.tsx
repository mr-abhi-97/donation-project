'use client';

import React, { useState, useRef } from 'react';
import Link from 'next/link';
import { 
  UploadCloud, 
  FileArchive, 
  Image as ImageIcon, 
  CheckCircle2, 
  AlertCircle, 
  X, 
  RefreshCw, 
  ArrowRight, 
  ExternalLink,
  ShieldCheck,
  FileCheck2,
  Clock
} from 'lucide-react';
import { api, Donation } from '@/lib/api';

export default function BulkUploadPage() {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [processedDonations, setProcessedDonations] = useState<Donation[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFiles = (files: FileList | null) => {
    if (!files) return;
    const validFiles: File[] = [];
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const ext = file.name.toLowerCase();
      if (
        ext.endsWith('.png') ||
        ext.endsWith('.jpg') ||
        ext.endsWith('.jpeg') ||
        ext.endsWith('.webp') ||
        ext.endsWith('.zip')
      ) {
        validFiles.push(file);
      }
    }
    setSelectedFiles((prev) => [...prev, ...validFiles]);
    setErrorMessage(null);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    handleFiles(e.dataTransfer.files);
  };

  const handleRemoveFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleClearAll = () => {
    setSelectedFiles([]);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleUploadAndProcess = async () => {
    if (selectedFiles.length === 0) return;
    setUploading(true);
    setErrorMessage(null);

    try {
      const results = await api.bulkUploadScreenshots(selectedFiles);
      setProcessedDonations(results);
      setSelectedFiles([]);
      if (fileInputRef.current) fileInputRef.current.value = '';
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to process files in bulk');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="py-8 px-4 sm:px-6 lg:px-8 max-w-6xl mx-auto space-y-6">
      {/* Page Header */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              Bulk Screenshot Upload & OCR Pipeline
            </h1>
            <span className="text-xs bg-indigo-100 text-indigo-800 font-bold px-2.5 py-0.5 rounded-full">
              OpenCV + Tesseract Engine
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Drag and drop multiple UPI screenshots (.png, .jpg, .webp) or a .zip archive. The system automatically enhances contrast, executes OCR, and extracts 12-digit UTRs.
          </p>
        </div>

        <Link
          href="/admin/reconcile"
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow-xs transition-all shrink-0"
        >
          <span>Open Reconciliation Console</span>
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>

      {errorMessage && (
        <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-red-500 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Dropzone Container */}
      <div className="bg-white p-6 sm:p-8 rounded-2xl border border-slate-200 shadow-xs space-y-6">
        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className="border-2 border-dashed border-slate-300 hover:border-emerald-500 rounded-2xl p-8 sm:p-12 text-center cursor-pointer bg-slate-50/50 hover:bg-emerald-50/20 transition-all group"
        >
          <div className="w-16 h-16 bg-white rounded-full flex items-center justify-center text-slate-400 group-hover:text-emerald-600 group-hover:scale-110 shadow-xs mx-auto mb-4 transition-transform">
            <UploadCloud className="w-8 h-8" />
          </div>
          <h2 className="text-base font-bold text-slate-800 group-hover:text-emerald-800">
            Click to upload, or drag and drop batch receipts
          </h2>
          <p className="text-xs text-slate-500 mt-1.5 max-w-md mx-auto">
            Drop up to 100 payment screenshots simultaneously or a single <strong>.zip</strong> package containing receipts.
          </p>
          <div className="flex items-center justify-center gap-3 mt-4 text-[11px] text-slate-400 font-mono">
            <span>.PNG</span>
            <span>•</span>
            <span>.JPG</span>
            <span>•</span>
            <span>.JPEG</span>
            <span>•</span>
            <span>.WEBP</span>
            <span>•</span>
            <span className="text-indigo-600 font-bold">.ZIP ARCHIVES</span>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept="image/*,.zip"
            onChange={(e) => handleFiles(e.target.files)}
            className="hidden"
          />
        </div>

        {/* Selected Files Staging List */}
        {selectedFiles.length > 0 && (
          <div className="border border-slate-200 rounded-xl p-4 bg-slate-50 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-700">
                Staged Files for OCR Analysis ({selectedFiles.length} items)
              </span>
              <button
                onClick={handleClearAll}
                className="text-[11px] text-red-600 hover:underline font-semibold"
              >
                Clear all
              </button>
            </div>

            <div className="max-h-48 overflow-y-auto space-y-1.5 divide-y divide-slate-200">
              {selectedFiles.map((f, idx) => (
                <div key={idx} className="pt-1.5 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2 truncate">
                    {f.name.toLowerCase().endsWith('.zip') ? (
                      <FileArchive className="w-4 h-4 text-amber-500 shrink-0" />
                    ) : (
                      <ImageIcon className="w-4 h-4 text-emerald-500 shrink-0" />
                    )}
                    <span className="text-slate-800 font-medium truncate">{f.name}</span>
                    <span className="text-slate-400 text-[10px]">({(f.size / 1024).toFixed(1)} KB)</span>
                  </div>
                  <button
                    onClick={() => handleRemoveFile(idx)}
                    className="p-1 hover:bg-slate-200 rounded text-slate-400 hover:text-red-500"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>

            <div className="pt-2 flex justify-end">
              <button
                onClick={handleUploadAndProcess}
                disabled={uploading}
                className="px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-md shadow-emerald-600/20 disabled:opacity-50 flex items-center gap-2 cursor-pointer"
              >
                {uploading ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Processing OpenCV Preprocessing & OCR...</span>
                  </>
                ) : (
                  <>
                    <UploadCloud className="w-4 h-4" />
                    <span>Start Batch OCR Pipeline ({selectedFiles.length})</span>
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Processed Results Table */}
      {processedDonations.length > 0 && (
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-slate-900">
                Batch OCR Processing Complete ({processedDonations.length} records)
              </h2>
              <p className="text-xs text-slate-500">
                All receipts have been processed through Otsu thresholding & regex parsing.
              </p>
            </div>
            <Link
              href="/admin/reconcile"
              className="text-xs text-emerald-700 font-bold hover:underline flex items-center gap-1"
            >
              <span>View in Split-Screen Reconciler</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="overflow-x-auto border border-slate-200 rounded-xl">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-700 font-bold border-b border-slate-200">
                <tr>
                  <th className="p-3">Receipt Preview</th>
                  <th className="p-3">Extracted UTR</th>
                  <th className="p-3">Extracted Amount</th>
                  <th className="p-3">OCR Confidence</th>
                  <th className="p-3">Status</th>
                  <th className="p-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono">
                {processedDonations.map((d) => (
                  <tr key={d.id} className="hover:bg-slate-50/50">
                    <td className="p-3">
                      <img
                        src={api.getScreenshotUrl(d.screenshot_url)}
                        alt="Thumbnail"
                        className="w-9 h-12 object-cover rounded border border-slate-200 shadow-2xs"
                      />
                    </td>
                    <td className="p-3 font-bold text-slate-900">
                      {d.extracted_utr || <span className="text-amber-600 font-normal">Pending Review</span>}
                    </td>
                    <td className="p-3 text-slate-800 font-sans font-bold">
                      {d.extracted_amount ? `₹${d.extracted_amount.toLocaleString('en-IN')}` : '—'}
                    </td>
                    <td className="p-3 font-sans">
                      <span className="bg-emerald-50 text-emerald-700 font-semibold px-2 py-0.5 rounded text-[11px]">
                        {(d.ocr_confidence * 100).toFixed(0)}%
                      </span>
                    </td>
                    <td className="p-3 font-sans">
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                        d.status === 'MATCHED'
                          ? 'bg-emerald-100 text-emerald-800'
                          : d.status === 'FLAGGED_REVIEW'
                          ? 'bg-amber-100 text-amber-800'
                          : 'bg-blue-100 text-blue-800'
                      }`}>
                        {d.status}
                      </span>
                    </td>
                    <td className="p-3 text-right font-sans">
                      <Link
                        href={`/admin/reconcile`}
                        className="inline-flex items-center gap-1 text-xs text-emerald-600 hover:text-emerald-800 font-semibold"
                      >
                        <span>Reconcile</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
