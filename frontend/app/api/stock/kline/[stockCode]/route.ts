import { NextRequest, NextResponse } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function GET(
  request: NextRequest,
  { params }: { params: { stockCode: string } }
) {
  try {
    const { stockCode } = params;
    const searchParams = request.nextUrl.searchParams;
    const period = searchParams.get("period") ?? "30d";

    const response = await fetch(
      `${API_BASE}/api/stock/kline/${stockCode}?period=${period}`
    );

    if (!response.ok) {
      return NextResponse.json(
        { error: "Failed to fetch kline data" },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
