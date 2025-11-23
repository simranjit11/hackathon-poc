import { NextRequest, NextResponse } from 'next/server';
import { extractTokenFromHeader, validateAccessToken } from '@/lib/auth';
import { prisma } from '@/lib/db/prisma';

export async function GET(request: NextRequest) {
  try {
    const authHeader = request.headers.get('Authorization');
    const token = extractTokenFromHeader(authHeader);
    const user = await validateAccessToken(token);

    const beneficiaries = await prisma.beneficiary.findMany({
      where: { userId: user.user_id },
      select: {
        id: true,
        nickname: true,
        fullName: true,
        paymentAddress: true,
        paymentType: true,
        bankName: true,
      },
      orderBy: { nickname: 'asc' },
    });

    return NextResponse.json(beneficiaries);
  } catch (error) {
    console.error('Error fetching beneficiaries:', error);
    return NextResponse.json({ error: 'Unauthorized or Internal Error' }, { status: 401 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const authHeader = request.headers.get('Authorization');
    const token = extractTokenFromHeader(authHeader);
    const user = await validateAccessToken(token);

    const body = await request.json();
    const { nickname, fullName, paymentAddress, paymentType, bankName } = body;

    // Basic validation
    if (!nickname || !fullName || !paymentAddress || !paymentType) {
      return NextResponse.json({ error: 'Missing required fields' }, { status: 400 });
    }

    const beneficiary = await prisma.beneficiary.create({
      data: {
        userId: user.user_id,
        nickname,
        fullName,
        paymentAddress,
        paymentType,
        bankName,
      },
    });

    return NextResponse.json(beneficiary, { status: 201 });
  } catch (error) {
    console.error('Error creating beneficiary:', error);
    // Check for unique constraint violation (P2002)
    if ((error as any).code === 'P2002') {
      return NextResponse.json(
        { error: 'A beneficiary with this nickname already exists' },
        { status: 409 }
      );
    }
    return NextResponse.json({ error: 'Unauthorized or Internal Error' }, { status: 401 });
  }
}
