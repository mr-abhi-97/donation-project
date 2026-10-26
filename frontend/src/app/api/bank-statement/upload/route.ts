import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  try {
    const formData = await req.formData();
    const res = await fetch("http://127.0.0.1:8000/api/bank-statement/upload", {
      method: "POST",
      body: formData,
    });
    const data = await res.json().catch(() => ({ detail: "Invalid server response" }));
    return NextResponse.json(data, { status: res.status });
  } catch (error: any) {
    return NextResponse.json({ detail: error.message || "Failed to forward request" }, { status: 500 });
  }
}
