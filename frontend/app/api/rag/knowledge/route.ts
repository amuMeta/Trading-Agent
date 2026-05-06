import { NextRequest, NextResponse } from "next/server";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const collection = searchParams.get("collection") || "user_knowledge";

    const response = await fetch(
      `${API_BASE_URL}/api/rag/knowledge/info?collection=${collection}`
    );

    if (!response.ok) {
      return NextResponse.json(
        { error: "Failed to get knowledge base info" },
        { status: response.status }
      );
    }

    return NextResponse.json(await response.json());
  } catch (error) {
    console.error("Knowledge info proxy error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const collection = searchParams.get("collection") || "user_knowledge";

    const response = await fetch(
      `${API_BASE_URL}/api/rag/knowledge?collection=${collection}`,
      { method: "DELETE" }
    );

    if (!response.ok) {
      return NextResponse.json(
        { error: "Failed to delete knowledge base" },
        { status: response.status }
      );
    }

    return NextResponse.json(await response.json());
  } catch (error) {
    console.error("Knowledge delete proxy error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}