'use client';

import React, { useState, useRef } from 'react';
import confetti from 'canvas-confetti';
import { 
  HeartHandshake, 
  UploadCloud, 
  CheckCircle2, 
  AlertCircle, 
  FileText, 
  Download, 
  Search, 
  ShieldCheck, 
  Smartphone, 
  ArrowRight, 
  Clock, 
  X,
  CreditCard,
  User,
  Mail,
  MapPin,
  RefreshCw,
  MessageSquare,
  Fingerprint
} from 'lucide-react';
import { api } from '@/lib/api';

export default function DonatePage() {
  const [activeTab, setActiveTab] = useState<'submit' | 'lookup'>('submit');

  // Form State
  const [fullName, setFullName] = useState('');
  const [panNumber, setPanNumber] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [address, setAddress] = useState('');
  const [amountPaid, setAmountPaid] = useState<string>('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  
  // Status states
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submissionResult, setSubmissionResult] = useState<any | null>(null);

  // Lookup state
  const [lookupQuery, setLookupQuery] = useState('');
  const [lookupType, setLookupType] = useState<'pan' | 'tracking_id'>('pan');
  const [lookupLoading, setLookupLoading] = useState(false);
  const [lookupResult, setLookupResult] = useState<any | null>(null);
  const [lookupError, setLookupError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Live PAN validation
  const panRegex = /^[A-Z]{5}[0-9]{4}[A-Z]{1}$/;
  const isPanValid = panRegex.test(panNumber.trim().toUpperCase());

  // Phone normalization & E.164 standard (+91XXXXXXXXXX)
  const cleanedPhoneDigits = phone.replace(/\D/g, '');
  let normalizedDigits = cleanedPhoneDigits;
  if (cleanedPhoneDigits.length === 12 && cleanedPhoneDigits.startsWith('91')) {
    normalizedDigits = cleanedPhoneDigits.slice(2);
  } else if (cleanedPhoneDigits.length === 11 && cleanedPhoneDigits.startsWith('0')) {
    normalizedDigits = cleanedPhoneDigits.slice(1);
  }
  const isPhoneValid = normalizedDigits.length === 10 && /^[6-9]/.test(normalizedDigits);
  const e164Phone = isPhoneValid ? `+91${normalizedDigits}` : null;

  const handlePanChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setPanNumber(e.target.value.toUpperCase());
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      setSubmitError(null);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      setSubmitError(null);
    }
  };

  const handleClearFile = () => {
    setSelectedFile(null);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError(null);

    if (!isPanValid) {
      setSubmitError('Please enter a valid 10-character PAN number (e.g. ABCDE1234F).');
      return;
    }
    if (!isPhoneValid) {
      setSubmitError('Please enter a valid 10-digit Indian mobile number starting with 6-9 for WhatsApp delivery.');
      return;
    }
    if (!selectedFile) {
      setSubmitError('Please upload your UPI payment screenshot.');
      return;
    }

    try {
      setSubmitting(true);
      const formData = new FormData();
      formData.append('full_name', fullName);
      formData.append('pan_number', panNumber);
      formData.append('phone', e164Phone || phone);
      formData.append('email', email);
      if (address) formData.append('address', address);
      if (amountPaid) formData.append('amount_paid', amountPaid);
      formData.append('file', selectedFile);

      const res = await api.submitPublicDonation(formData);
      setSubmissionResult(res);

      // Trigger celebration confetti
      confetti({
        particleCount: 80,
        spread: 60,
        origin: { y: 0.6 },
      });
    } catch (err: any) {
      setSubmitError(err.message || 'Failed to submit donation. Please check your inputs.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleLookup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!lookupQuery.trim()) return;

    setLookupLoading(true);
    setLookupError(null);
    setLookupResult(null);

    try {
      if (lookupType === 'pan') {
        const res = await api.lookupReceipt(lookupQuery.trim().toUpperCase(), undefined);
        setLookupResult(res);
      } else {
        const res = await api.lookupReceipt(undefined, lookupQuery.trim());
        setLookupResult(res);
      }
    } catch (err: any) {
      setLookupError(err.message || 'No matching verified donation records found.');
    } finally {
      setLookupLoading(false);
    }
  };

  return (
    <div className="py-10 px-4 sm:px-6 lg:px-8 max-w-5xl mx-auto">
      {/* Header Banner */}
      <div className="text-center mb-10">
        <div className="inline-flex items-center gap-2 bg-emerald-100 text-emerald-800 text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider mb-3">
          <ShieldCheck className="w-4 h-4 text-emerald-600" />
          <span>Section 80G Tax Exemption Certified</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
          UPI Donation & 80G Tax Receipt Portal
        </h1>
        <p className="mt-3 text-slate-600 max-w-2xl mx-auto text-sm sm:text-base leading-relaxed">
          Because UPI transfers don&apos;t automatically transmit PAN & identity details, upload your payment screenshot here. Our automated OCR extracts your 12-digit UTR, reconciles it against our bank credits, and generates your compliant 80G tax certificate.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex justify-center mb-8">
        <div className="bg-slate-200/80 p-1 rounded-xl flex gap-1 shadow-inner">
          <button
            onClick={() => setActiveTab('submit')}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold transition-all ${
              activeTab === 'submit'
                ? 'bg-white text-emerald-700 shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <UploadCloud className="w-4 h-4" />
            <span>Submit Payment Proof</span>
          </button>
          <button
            onClick={() => setActiveTab('lookup')}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold transition-all ${
              activeTab === 'lookup'
                ? 'bg-white text-emerald-700 shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Search className="w-4 h-4" />
            <span>Check 80G Status / Download</span>
          </button>
        </div>
      </div>

      {/* SUBMIT FORM TAB */}
      {activeTab === 'submit' && (
        <>
          {submissionResult ? (
            /* SUCCESS ACKNOWLEDGEMENT SCREEN */
            <div className="bg-white rounded-2xl border border-emerald-200 shadow-xl overflow-hidden p-6 sm:p-8 animate-in fade-in zoom-in-95 duration-300">
              <div className="text-center pb-6 border-b border-slate-100">
                <div className="w-16 h-16 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mx-auto mb-4">
                  <CheckCircle2 className="w-10 h-10" />
                </div>
                <h2 className="text-2xl font-bold text-slate-900">
                  Donation Received & OCR Processed!
                </h2>
                <p className="text-sm text-slate-600 mt-1 max-w-lg mx-auto">
                  {submissionResult.message}
                </p>
                <div className="inline-flex items-center gap-2 bg-slate-100 text-slate-700 text-xs px-3 py-1.5 rounded-lg font-mono mt-3">
                  <span>Tracking ID:</span>
                  <span className="font-bold">{submissionResult.tracking_id}</span>
                </div>
              </div>

              {/* Status Stepper */}
              <div className="py-8">
                <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-6 text-center">
                  Live Verification & Forensic Security Pipeline
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3">
                  <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3.5">
                    <div className="flex items-center gap-1.5 text-emerald-700 font-bold text-xs mb-1">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>1. Identity Registered</span>
                    </div>
                    <p className="text-[11px] text-slate-600">
                      PAN {submissionResult.donor?.pan_number} & E.164 mobile logged.
                    </p>
                  </div>

                  <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3.5">
                    <div className="flex items-center gap-1.5 text-emerald-700 font-bold text-xs mb-1">
                      <ShieldCheck className="w-3.5 h-3.5" />
                      <span>2. Forensic Clearance</span>
                    </div>
                    <p className="text-[11px] text-slate-600">
                      SHA-256 deduplicated • ELA tamper variance verified.
                    </p>
                  </div>

                  <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3.5">
                    <div className="flex items-center gap-1.5 text-emerald-700 font-bold text-xs mb-1">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>3. UTR Validated</span>
                    </div>
                    <p className="text-[11px] text-slate-600">
                      UTR: <strong className="font-mono text-slate-900">{submissionResult.extracted_utr || 'Under Review'}</strong>
                      {submissionResult.extracted_amount && ` • ₹${submissionResult.extracted_amount}`}
                    </p>
                  </div>

                  <div className={`rounded-xl p-3.5 border ${
                    submissionResult.status === 'MATCHED'
                      ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
                      : 'bg-amber-50 border-amber-200 text-amber-700'
                  }`}>
                    <div className="flex items-center gap-1.5 font-bold text-xs mb-1">
                      {submissionResult.status === 'MATCHED' ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                      ) : (
                        <Clock className="w-3.5 h-3.5 text-amber-600 animate-spin" />
                      )}
                      <span>4. Bank Clearance</span>
                    </div>
                    <p className="text-[11px] text-slate-600">
                      {submissionResult.status === 'MATCHED'
                        ? '🟢 Reconciled against CBS feed!'
                        : 'Reconciling with Bank feed.'}
                    </p>
                  </div>

                  <div className={`rounded-xl p-3.5 border ${
                    submissionResult.status === 'MATCHED'
                      ? 'bg-emerald-50 border-emerald-200'
                      : 'bg-slate-50 border-slate-200 text-slate-400'
                  }`}>
                    <div className="flex items-center gap-1.5 font-bold text-xs mb-1 text-slate-800">
                      <MessageSquare className="w-3.5 h-3.5 text-emerald-600" />
                      <span>5. 80G via WhatsApp</span>
                    </div>
                    <p className="text-[11px] text-slate-600">
                      {submissionResult.status === 'MATCHED'
                        ? 'Certificate dispatched via WhatsApp!'
                        : 'Auto-dispatched upon clearance.'}
                    </p>
                  </div>
                </div>
              </div>

              {/* Action */}
              <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-4 border-t border-slate-100">
                <button
                  onClick={() => {
                    setSubmissionResult(null);
                    handleClearFile();
                    setAmountPaid('');
                  }}
                  className="w-full sm:w-auto px-6 py-2.5 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50 font-semibold text-sm transition-all"
                >
                  Submit Another Donation
                </button>
                <button
                  onClick={() => {
                    setActiveTab('lookup');
                    setLookupQuery(submissionResult.donor?.pan_number || submissionResult.tracking_id);
                    setLookupType('pan');
                  }}
                  className="w-full sm:w-auto px-6 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-sm shadow-sm transition-all flex items-center justify-center gap-2"
                >
                  <Search className="w-4 h-4" />
                  <span>Check Verification & Download PDF</span>
                </button>
              </div>
            </div>
          ) : (
            /* SUBMISSION FORM */
            <form onSubmit={handleSubmit} className="bg-white rounded-2xl border border-slate-200 shadow-xl overflow-hidden p-6 sm:p-8">
              {submitError && (
                <div className="mb-6 bg-red-50 border border-red-200 text-red-700 p-4 rounded-xl flex items-start gap-3 text-sm">
                  <AlertCircle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
                  <div>
                    <strong className="font-semibold">Submission Error:</strong> {submitError}
                  </div>
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Left Column: Donor Info */}
                <div className="space-y-4">
                  <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2 border-b border-slate-100 pb-2">
                    <User className="w-4 h-4 text-emerald-600" />
                    <span>Donor Identity (For Tax Exemption)</span>
                  </h3>

                  {/* Full Name */}
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Full Name (As per PAN Card) <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. Rajesh Kumar Verma"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-lg border border-slate-300 text-sm focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-hidden transition-all"
                    />
                  </div>

                  {/* PAN Number */}
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <label className="text-xs font-semibold text-slate-700">
                        PAN Number <span className="text-red-500">*</span>
                      </label>
                      {panNumber && (
                        <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${
                          isPanValid ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-600'
                        }`}>
                          {isPanValid ? '✓ Valid PAN Format' : 'Invalid PAN (e.g. ABCDE1234F)'}
                        </span>
                      )}
                    </div>
                    <div className="relative">
                      <CreditCard className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                      <input
                        type="text"
                        required
                        maxLength={10}
                        placeholder="ABCDE1234F"
                        value={panNumber}
                        onChange={handlePanChange}
                        className={`w-full pl-10 pr-3.5 py-2.5 rounded-lg border text-sm font-mono tracking-wider uppercase focus:ring-2 outline-hidden transition-all ${
                          panNumber && !isPanValid
                            ? 'border-red-300 focus:ring-red-500'
                            : 'border-slate-300 focus:ring-emerald-500 focus:border-emerald-500'
                        }`}
                      />
                    </div>
                    <p className="text-[11px] text-slate-500 mt-1">
                      Mandatory for Form 10BD and claiming 80G tax rebate.
                    </p>
                  </div>

                  {/* Phone & Email */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <label className="text-xs font-semibold text-slate-700">
                          Mobile Number <span className="text-red-500">*</span>
                        </label>
                        {phone && (
                          <span className={`text-[10px] font-bold px-1.5 py-0.2 rounded-full ${
                            isPhoneValid ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'
                          }`}>
                            {isPhoneValid ? '✓ Valid Mobile' : '10 Digits (6-9)'}
                          </span>
                        )}
                      </div>
                      <div className="relative">
                        <Smartphone className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                        <input
                          type="tel"
                          required
                          placeholder="9876543210"
                          value={phone}
                          onChange={(e) => setPhone(e.target.value)}
                          className={`w-full pl-9 pr-3 py-2.5 rounded-lg border text-sm focus:ring-2 outline-hidden ${
                            phone && !isPhoneValid
                              ? 'border-amber-300 focus:ring-amber-500'
                              : 'border-slate-300 focus:ring-emerald-500'
                          }`}
                        />
                      </div>
                      <p className="text-[10px] text-slate-500 mt-1 flex items-center gap-1">
                        <MessageSquare className="w-3 h-3 text-emerald-600 shrink-0" />
                        <span>
                          {e164Phone
                            ? `E.164: ${e164Phone} • 80G receipt dispatched via WhatsApp`
                            : '80G Tax certificate will be dispatched via WhatsApp to this phone.'}
                        </span>
                      </p>
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1">
                        Email Address <span className="text-red-500">*</span>
                      </label>
                      <div className="relative">
                        <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                        <input
                          type="email"
                          required
                          placeholder="you@domain.com"
                          value={email}
                          onChange={(e) => setEmail(e.target.value)}
                          className="w-full pl-9 pr-3 py-2.5 rounded-lg border border-slate-300 text-sm focus:ring-2 focus:ring-emerald-500 outline-hidden"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Address */}
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Postal Address (Optional, for 80G Certificate)
                    </label>
                    <textarea
                      rows={2}
                      placeholder="e.g. Flat 402, Sunshine Apts, Bengaluru - 560038"
                      value={address}
                      onChange={(e) => setAddress(e.target.value)}
                      className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm focus:ring-2 focus:ring-emerald-500 outline-hidden"
                    />
                  </div>
                </div>

                {/* Right Column: Payment Details & Screenshot Upload */}
                <div className="space-y-4">
                  <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2 border-b border-slate-100 pb-2">
                    <UploadCloud className="w-4 h-4 text-emerald-600" />
                    <span>UPI Payment Proof</span>
                  </h3>

                  {/* Amount Paid */}
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Amount Paid (INR)
                    </label>
                    <div className="relative">
                      <span className="absolute left-3.5 top-2.5 text-slate-500 font-bold text-sm">₹</span>
                      <input
                        type="number"
                        placeholder="5000"
                        value={amountPaid}
                        onChange={(e) => setAmountPaid(e.target.value)}
                        className="w-full pl-8 pr-3.5 py-2.5 rounded-lg border border-slate-300 text-sm font-semibold focus:ring-2 focus:ring-emerald-500 outline-hidden"
                      />
                    </div>
                    {/* Quick Amount Chips */}
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {['1000', '2500', '5000', '11000', '21000'].map((amt) => (
                        <button
                          key={amt}
                          type="button"
                          onClick={() => setAmountPaid(amt)}
                          className={`text-xs px-2.5 py-1 rounded-md font-medium border transition-all ${
                            amountPaid === amt
                              ? 'bg-emerald-600 text-white border-emerald-600'
                              : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
                          }`}
                        >
                          ₹{parseInt(amt).toLocaleString('en-IN')}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* File Upload Dropzone */}
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Upload UPI Receipt Screenshot <span className="text-red-500">*</span>
                    </label>

                    {previewUrl ? (
                      <div className="relative border-2 border-emerald-300 rounded-xl p-3 bg-emerald-50/30 flex items-center gap-4">
                        <img
                          src={previewUrl}
                          alt="Screenshot Preview"
                          className="w-20 h-28 object-cover rounded-lg border border-emerald-200 shadow-xs"
                        />
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-bold text-slate-800 truncate">
                            {selectedFile?.name}
                          </p>
                          <p className="text-[11px] text-slate-500 mt-0.5">
                            {selectedFile && `${(selectedFile.size / 1024).toFixed(1)} KB`}
                          </p>
                          <span className="inline-flex items-center gap-1 text-[11px] text-emerald-700 font-semibold mt-2">
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            <span>Ready for OCR analysis</span>
                          </span>
                        </div>
                        <button
                          type="button"
                          onClick={handleClearFile}
                          className="p-1.5 rounded-full hover:bg-red-100 text-slate-400 hover:text-red-600 transition-colors"
                          title="Remove file"
                        >
                          <X className="w-5 h-5" />
                        </button>
                      </div>
                    ) : (
                      <div
                        onDragOver={(e) => e.preventDefault()}
                        onDrop={handleDrop}
                        onClick={() => fileInputRef.current?.click()}
                        className="border-2 border-dashed border-slate-300 hover:border-emerald-500 rounded-xl p-6 text-center cursor-pointer bg-slate-50/50 hover:bg-emerald-50/20 transition-all group"
                      >
                        <div className="w-12 h-12 bg-white rounded-full flex items-center justify-center text-slate-400 group-hover:text-emerald-600 group-hover:scale-110 shadow-xs mx-auto mb-3 transition-transform">
                          <UploadCloud className="w-6 h-6" />
                        </div>
                        <p className="text-xs font-bold text-slate-700 group-hover:text-emerald-700">
                          Drag & drop receipt screenshot, or click to browse
                        </p>
                        <p className="text-[11px] text-slate-400 mt-1">
                          Supports PNG, JPG, JPEG, WEBP (GPay, PhonePe, Paytm, BHIM)
                        </p>
                        <input
                          ref={fileInputRef}
                          type="file"
                          accept="image/*"
                          onChange={handleFileChange}
                          className="hidden"
                        />
                      </div>
                    )}
                  </div>

                  <div className="bg-slate-50 p-3 rounded-xl border border-slate-200 text-xs text-slate-600 flex items-start gap-2">
                    <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                    <span>
                      Our optical recognition engine automatically extracts your 12-digit UPI UTR to match with our official SBI bank statement.
                    </span>
                  </div>
                </div>
              </div>

              {/* Submit CTA */}
              <div className="mt-8 pt-6 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-4">
                <p className="text-xs text-slate-500">
                  By submitting, you confirm that the contribution is made from your own bank account.
                </p>
                <button
                  type="submit"
                  disabled={submitting}
                  className="w-full sm:w-auto px-8 py-3 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white font-bold text-sm shadow-md shadow-emerald-600/20 hover:shadow-lg disabled:opacity-50 transition-all flex items-center justify-center gap-2 cursor-pointer"
                >
                  {submitting ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Processing OCR & Verifying...</span>
                    </>
                  ) : (
                    <>
                      <span>Submit Proof & Claim 80G Receipt</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>
            </form>
          )}
        </>
      )}

      {/* LOOKUP TAB */}
      {activeTab === 'lookup' && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-xl overflow-hidden p-6 sm:p-8">
          <div className="max-w-xl mx-auto text-center mb-6">
            <h2 className="text-xl font-bold text-slate-900 mb-2">
              Lookup & Download 80G Tax Exemption Certificate
            </h2>
            <p className="text-xs text-slate-500">
              Enter your registered PAN or Donation Tracking ID to check status and download your digitally verified 80G Tax Exemption Certificate.
            </p>
          </div>

          <form onSubmit={handleLookup} className="max-w-xl mx-auto mb-8">
            <div className="flex gap-2 mb-3 justify-center">
              <label className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-700 cursor-pointer">
                <input
                  type="radio"
                  name="lookupType"
                  value="pan"
                  checked={lookupType === 'pan'}
                  onChange={() => setLookupType('pan')}
                  className="text-emerald-600 focus:ring-emerald-500"
                />
                <span>By PAN Number</span>
              </label>
              <span className="text-slate-300">|</span>
              <label className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-700 cursor-pointer">
                <input
                  type="radio"
                  name="lookupType"
                  value="tracking_id"
                  checked={lookupType === 'tracking_id'}
                  onChange={() => setLookupType('tracking_id')}
                  className="text-emerald-600 focus:ring-emerald-500"
                />
                <span>By Tracking ID (UUID)</span>
              </label>
            </div>

            <div className="flex gap-2">
              <input
                type="text"
                placeholder={lookupType === 'pan' ? 'Enter 10-digit PAN (e.g. ABCDE1234F)' : 'Enter Tracking ID UUID'}
                value={lookupQuery}
                onChange={(e) => setLookupQuery(e.target.value)}
                className="flex-1 px-4 py-2.5 rounded-xl border border-slate-300 text-sm focus:ring-2 focus:ring-emerald-500 outline-hidden font-mono uppercase"
              />
              <button
                type="submit"
                disabled={lookupLoading}
                className="px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-sm shadow-sm transition-all flex items-center gap-2"
              >
                {lookupLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                <span>Lookup</span>
              </button>
            </div>
          </form>

          {lookupError && (
            <div className="max-w-xl mx-auto bg-amber-50 border border-amber-200 text-amber-800 p-4 rounded-xl text-center text-xs">
              <AlertCircle className="w-5 h-5 text-amber-600 mx-auto mb-1" />
              <span>{lookupError}</span>
            </div>
          )}

          {/* Results list */}
          {lookupResult && (
            <div className="max-w-2xl mx-auto space-y-4">
              <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                Found Donations & Receipts
              </h3>

              {lookupResult.records ? (
                lookupResult.records.map((rec: any, idx: number) => (
                  <div key={idx} className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 hover:border-emerald-300 transition-all">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-900 text-sm">{rec.donor_name}</span>
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                          rec.is_verified ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'
                        }`}>
                          {rec.is_verified ? '🟢 Verified & Reconciled' : '🟡 Bank Verification In Progress'}
                        </span>
                      </div>
                      <p className="text-xs text-slate-600 mt-1">
                        Amount: <strong className="text-slate-900">₹{rec.amount.toLocaleString('en-IN')}</strong> • Date: {rec.date}
                      </p>
                      <p className="text-[11px] text-slate-400 font-mono mt-0.5">
                        UTR: {rec.extracted_utr || 'Pending'} {rec.receipt_number && `• Receipt: ${rec.receipt_number}`}
                      </p>
                    </div>

                    {rec.receipt_url ? (
                      <a
                        href={api.getReceiptPdfUrl(rec.receipt_url)}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold px-4 py-2 rounded-lg shadow-sm transition-all"
                      >
                        <Download className="w-4 h-4" />
                        <span>Download 80G PDF</span>
                      </a>
                    ) : (
                      <span className="text-xs text-amber-600 bg-amber-50 px-3 py-1.5 rounded-lg border border-amber-200 font-medium">
                        Receipt ready once reconciled
                      </span>
                    )}
                  </div>
                ))
              ) : (
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-slate-900 text-sm">{lookupResult.donor_name}</span>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                        lookupResult.is_verified ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'
                      }`}>
                        {lookupResult.is_verified ? '🟢 Verified' : '🟡 Pending Clearance'}
                      </span>
                    </div>
                    <p className="text-xs text-slate-600 mt-1">
                      Amount: <strong>₹{lookupResult.amount.toLocaleString('en-IN')}</strong> • UTR: {lookupResult.extracted_utr}
                    </p>
                  </div>
                  {lookupResult.receipt_url ? (
                    <a
                      href={api.getReceiptPdfUrl(lookupResult.receipt_url)}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold px-4 py-2 rounded-lg shadow-sm"
                    >
                      <Download className="w-4 h-4" />
                      <span>Download 80G PDF</span>
                    </a>
                  ) : (
                    <span className="text-xs text-slate-500">Processing bank clearance</span>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
