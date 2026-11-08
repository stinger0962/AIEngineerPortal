import { NextResponse, type NextRequest } from "next/server";
import { isPaidProductPath, paidProduct } from "@/lib/product/config";

// Separate product deployments must not serve personal-portal pages. The API
// has its own dedicated entrypoint; this is not a substitute for API isolation.
export function middleware(request: NextRequest) {
  if (paidProduct && !isPaidProductPath(request.nextUrl.pathname)) {
    return new NextResponse("Not found", { status: 404 });
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/|favicon.ico$|fonts/|images/).*)"],
};
