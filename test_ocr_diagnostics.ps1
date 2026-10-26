<#
.SYNOPSIS
    Standalone OCR Diagnostics & UPI Extraction Test Script
.DESCRIPTION
    Runs the Python OCR engine directly on any payment screenshot or tests against
    the repository's sample uploads to verify UTR, Amount, and Payer Name extraction.
.PARAMETER ImagePath
    Optional absolute or relative path to a screenshot image. If omitted, uses a sample screenshot.
#>

[CmdletBinding()]
param (
    [string]$ImagePath
)

$ProjectRoot = if ($PSScriptRoot) { $PSScriptRoot } else { "E:\raise india" }
Set-Location -LiteralPath $ProjectRoot

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host " [Raise India] OCR & UPI Payment Forensics Diagnostic Tool" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Cyan

# 1. Resolve Image Path
if (-not $ImagePath) {
    # Pick a sample screenshot from uploads
    $ScreenshotsDir = Join-Path $ProjectRoot "backend\uploads\screenshots"
    $SampleImages = Get-ChildItem -Path "$ScreenshotsDir\*" -Include "*.png", "*.jpg", "*.jpeg" -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like "*phonepe*" -or $_.Name -like "*gpay*" -or $_.Name -like "*google*" -or $_.Name -like "*WhatsApp*" }

    if ($SampleImages) {
        $SelectedFile = $SampleImages[0]
        $ImagePath = $SelectedFile.FullName
        Write-Host "[INFO] No -ImagePath specified. Selected sample: $($SelectedFile.Name)" -ForegroundColor DarkCyan
    } else {
        Write-Error "No sample screenshots found in $ScreenshotsDir. Please specify -ImagePath."
        exit 1
    }
} else {
    if (-not (Test-Path -LiteralPath $ImagePath)) {
        Write-Error "Specified file does not exist: $ImagePath"
        exit 1
    }
    $ImagePath = (Resolve-Path -LiteralPath $ImagePath).Path
}

Write-Host "[+] Target File: $ImagePath" -ForegroundColor DarkGray
$FileSizeKB = [math]::Round(((Get-Item -LiteralPath $ImagePath).Length / 1KB), 2)
Write-Host "[+] File Size  : $FileSizeKB KB" -ForegroundColor DarkGray
Write-Host ""

# 2. Locate Virtual Environment Python
$VenvPython = Join-Path $ProjectRoot "backend\venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $VenvPython)) {
    Write-Error "Python virtual environment not found at $VenvPython"
    exit 1
}

# 3. Inline Python Execution Script
$PythonScript = @"
import sys
import os
import json

# Set project root in sys.path
root_dir = r'$ProjectRoot'
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from backend.app.services.ocr import OCRService, TESSERACT_AVAILABLE, TESSERACT_PATH, _rapidocr_engine

img_path = r'$ImagePath'
result = OCRService.process_screenshot(img_path)

output = {
    'summary': {
        'status': result.get('status'),
        'is_valid_receipt': result.get('is_valid_receipt'),
        'extracted_utr': result.get('extracted_utr'),
        'extracted_amount': result.get('extracted_amount'),
        'extracted_donor_name': result.get('extracted_donor_name'),
        'extracted_date': result.get('extracted_date'),
        'confidence': result.get('confidence'),
        'keyword_hits': result.get('keyword_hits'),
        'is_custom_id': result.get('is_custom_id'),
        'domain_rejection_reason': result.get('domain_rejection_reason'),
    },
    'engine_telemetry': {
        'tesseract_bound': TESSERACT_AVAILABLE,
        'tesseract_path': TESSERACT_PATH,
        'rapidocr_active': _rapidocr_engine is not None,
        'engines_used': result.get('diagnostics', {}).get('engines_used', [])
    },
    'raw_text_preview': result.get('raw_text', '')[:300].replace('\n', ' // ')
}

print(json.dumps(output, indent=2))
"@

$TempScript = Join-Path $ProjectRoot "scratch_ocr_test.py"
Set-Content -LiteralPath $TempScript -Value $PythonScript -Encoding UTF8

try {
    $env:PYTHONPATH = $ProjectRoot
    $JsonOutput = & $VenvPython $TempScript
    $Parsed = $JsonOutput | ConvertFrom-Json

    Write-Host "------------------------------------------------------------------" -ForegroundColor DarkGray
    Write-Host " OCR EXTRACTION RESULTS:" -ForegroundColor Yellow
    Write-Host "------------------------------------------------------------------" -ForegroundColor DarkGray

    $StatusColor = if ($Parsed.summary.is_valid_receipt -and $Parsed.summary.extracted_utr) { "Green" } elseif ($Parsed.summary.is_valid_receipt) { "Yellow" } else { "Red" }
    Write-Host " Receipt Status      : " -NoNewline; Write-Host "$($Parsed.summary.status)" -ForegroundColor $StatusColor
    Write-Host " Valid Receipt       : " -NoNewline; Write-Host "$($Parsed.summary.is_valid_receipt)" -ForegroundColor $StatusColor
    Write-Host " Extracted UTR       : " -NoNewline; Write-Host "$($Parsed.summary.extracted_utr)" -ForegroundColor Cyan
    Write-Host " Extracted Amount    : " -NoNewline; Write-Host "Rs. $($Parsed.summary.extracted_amount)" -ForegroundColor Green
    Write-Host " Donor Name          : " -NoNewline; Write-Host "$($Parsed.summary.extracted_donor_name)" -ForegroundColor White
    Write-Host " Extracted Date      : " -NoNewline; Write-Host "$($Parsed.summary.extracted_date)" -ForegroundColor DarkGray
    Write-Host " Confidence Score    : " -NoNewline; Write-Host "$($Parsed.summary.confidence)" -ForegroundColor Cyan
    Write-Host " UPI Keyword Hits    : " -NoNewline; Write-Host "$($Parsed.summary.keyword_hits)" -ForegroundColor DarkGray

    if ($Parsed.summary.domain_rejection_reason) {
        Write-Host " Rejection Reason    : " -NoNewline; Write-Host "$($Parsed.summary.domain_rejection_reason)" -ForegroundColor Red
    }

    Write-Host ""
    Write-Host " ENGINE TELEMETRY:" -ForegroundColor Yellow
    Write-Host " RapidOCR Active     : " -NoNewline; Write-Host "$($Parsed.engine_telemetry.rapidocr_active)" -ForegroundColor Green
    Write-Host " Tesseract Bound     : " -NoNewline; Write-Host "$($Parsed.engine_telemetry.tesseract_bound) ($($Parsed.engine_telemetry.tesseract_path))" -ForegroundColor DarkGray
    Write-Host " Pipeline Passes     : " -NoNewline; Write-Host "$($Parsed.engine_telemetry.engines_used -join ', ')" -ForegroundColor Cyan

    Write-Host ""
    Write-Host " RAW TEXT PREVIEW:" -ForegroundColor Yellow
    Write-Host " $($Parsed.raw_text_preview)..." -ForegroundColor DarkGray
    Write-Host "------------------------------------------------------------------" -ForegroundColor DarkGray

} finally {
    if (Test-Path -LiteralPath $TempScript) {
        Remove-Item -LiteralPath $TempScript -Force -ErrorAction SilentlyContinue
    }
}
