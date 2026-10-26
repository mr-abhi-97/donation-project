import { NextResponse } from "next/server";

export async function GET() {
  try {
    const res = await fetch("http://127.0.0.1:8000/api/donations", {
      cache: "no-store",
    });
    if (!res.ok) {
      return NextResponse.json([], { status: res.status });
    }
    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Backend Proxy Error:", error);
    return NextResponse.json([], { status: 500 });
  }
}