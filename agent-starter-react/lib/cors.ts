import { NextResponse } from 'next/server';

/**
 * CORS headers for API routes
 * Allows mobile app to access endpoints
 */
export const corsHeaders = {
  'Access-Control-Allow-Origin': '*', // In production, specify exact origin
  'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
  'Access-Control-Max-Age': '86400',
};

/**
 * Creates a CORS-enabled response
 * 
 * @param data - Response data
 * @param status - HTTP status code
 * @returns NextResponse with CORS headers
 */
export function corsResponse(data: any, status: number = 200): NextResponse {
  return NextResponse.json(data, {
    status,
    headers: corsHeaders,
  });
}

/**
 * Handles OPTIONS preflight request
 * 
 * @returns NextResponse with CORS headers
 */
export function corsPreflight(): NextResponse {
  return new NextResponse(null, {
    status: 200,
    headers: corsHeaders,
  });
}

