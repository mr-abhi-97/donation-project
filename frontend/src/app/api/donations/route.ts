import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const res = await fetch("http://127.0.0.1:8000/api/donations", {
      cache: "no-store",
    });
    if (!res.ok) {
      const errText = await res.text().catch(() => "Backend server error");
      return NextResponse.json(
        { error: true, message: `FastAPI error (${res.status}): ${errText}` },
        { status: res.status }
      );
    }
    const data = await res.json();
    return NextResponse.json(data);
  } catch (error: any) {
    console.error("Backend Proxy Error:", error);
    return NextResponse.json(
      { error: true, message: error?.message || "Cannot connect to backend server on port 8000." },
      { status: 502 }
    );
  }
}