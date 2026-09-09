import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
    return NextResponse.json({
        API_URL: process.env.NEXT_PUBLIC_API_URL || process.env.API_URL || "http://localhost:8001"
    });
}
