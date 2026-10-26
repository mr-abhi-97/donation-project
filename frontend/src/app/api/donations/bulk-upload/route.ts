import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function POST(req: NextRequest) {
  try {
    const formData = await req.formData();

    // Prepare upstream FormData to forward to FastAPI backend
    const upstreamFormData = new FormData();
    for (const [key, value] of formData.entries()) {
      upstreamFormData.append(key, value);
    }

    // Set 120-second timeout for large bulk and OCR extractions
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 120000);

    const upstreamRes = await fetch("http://127.0.0.1:8000/api/donations/bulk-upload", {
      method: "POST",
      body: upstreamFormData,
      signal: controller.signal,
    }).finally(() => clearTimeout(timeoutId));

    if (!upstreamRes.ok) {
      const errorText = await upstreamRes.text().catch(() => "Backend server error");
      return NextResponse.json(
        {
          success: false,
          message: `FastAPI upload error (${upstreamRes.status}): ${errorText}`,
          processed_count: 0,
          donations: [],
        },
        { status: upstreamRes.status }
      );
    }

    const data = await upstreamRes.json();
    return NextResponse.json(data);
  } catch (error: any) {
    console.error("Bulk Upload Proxy Error:", error);
    if (error.name === "AbortError") {
      return NextResponse.json(
        {
          success: false,
          message: "Upload request timed out after 120 seconds while processing OCR.",
          processed_count: 0,
          donations: [],
        },
        { status: 504 }
      );
    }
    return NextResponse.json(
      {
        success: false,
        message: error?.message || "Failed to forward bulk upload to backend server.",
        processed_count: 0,
        donations: [],
      },
      { status: 500 }
    );
  }
}
