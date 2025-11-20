import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/db/prisma";
import { validateAccessToken, extractTokenFromHeader } from "@/lib/auth";

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const authHeader = request.headers.get("Authorization");
    const token = extractTokenFromHeader(authHeader);
    const user = await validateAccessToken(token);

    const { id } = await params;

    // Ensure the beneficiary belongs to the user
    const existing = await prisma.beneficiary.findUnique({
      where: { id },
    });

    if (!existing || existing.userId !== user.user_id) {
      return NextResponse.json({ error: "Not found" }, { status: 404 });
    }

    await prisma.beneficiary.delete({
      where: { id },
    });

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Error deleting beneficiary:", error);
    return NextResponse.json(
      { error: "Unauthorized or Internal Error" },
      { status: 401 }
    );
  }
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const authHeader = request.headers.get("Authorization");
    const token = extractTokenFromHeader(authHeader);
    const user = await validateAccessToken(token);

    const { id } = await params;
    const body = await request.json();
    const { nickname, fullName, paymentAddress, paymentType, bankName } = body;

    // Ensure the beneficiary belongs to the user
    const existing = await prisma.beneficiary.findUnique({
      where: { id },
    });

    if (!existing || existing.userId !== user.user_id) {
      return NextResponse.json({ error: "Not found" }, { status: 404 });
    }

    // Update beneficiary
    const updated = await prisma.beneficiary.update({
      where: { id },
      data: {
        ...(nickname !== undefined && { nickname }),
        ...(fullName !== undefined && { fullName }),
        ...(paymentAddress !== undefined && { paymentAddress }),
        ...(paymentType !== undefined && { paymentType }),
        ...(bankName !== undefined && { bankName }),
      },
    });

    return NextResponse.json(updated);
  } catch (error) {
    console.error("Error updating beneficiary:", error);
    // Check for unique constraint violation (P2002)
    if ((error as any).code === 'P2002') {
      return NextResponse.json(
        { error: "A beneficiary with this nickname already exists" },
        { status: 409 }
      );
    }
    return NextResponse.json(
      { error: "Unauthorized or Internal Error" },
      { status: 401 }
    );
  }
}
