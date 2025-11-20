import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db/prisma";

export async function GET(
    request: NextRequest,
    { params }: { params: Promise<{ id: string }> }
) {
    const apiKey = request.headers.get("x-api-key");

    if (apiKey !== process.env.INTERNAL_API_KEY) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    try {
        const { id } = await params;
        const beneficiaries = await prisma.beneficiary.findMany({
            where: { userId: id },
            select: {
                nickname: true,
                fullName: true,
                paymentAddress: true,
                paymentType: true,
                bankName: true,
            },
        });

        return NextResponse.json({ beneficiaries });
    } catch (error) {
        console.error("Error fetching beneficiaries:", error);
        return NextResponse.json(
            { error: "Internal Server Error" },
            { status: 500 }
        );
    }
}

