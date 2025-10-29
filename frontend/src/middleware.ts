import { NextRequest, NextResponse } from 'next/server';
import { getToken } from 'next-auth/jwt';

export async function middleware(request: NextRequest) {
  // Check for admin routes
  if (request.nextUrl.pathname.startsWith('/admin')) {
    const token = await getToken({ req: request });

    if (!token) {
      // Redirect to login if not authenticated
      const loginUrl = new URL('/auth/signin', request.url);
      loginUrl.searchParams.set('callbackUrl', request.url);
      return NextResponse.redirect(loginUrl);
    }

    // Check if user is admin
    const isAdmin = token.email?.endsWith('@chandrahoro.com') ||
                   token.email === 'admin@example.com' ||
                   process.env.ADMIN_EMAILS?.split(',').includes(token.email || '');

    if (!isAdmin) {
      // Redirect to unauthorized page or home
      return NextResponse.redirect(new URL('/', request.url));
    }
  }

  const response = NextResponse.next();

  // Add compression headers
  const acceptEncoding = request.headers.get('accept-encoding') || '';
  
  // Set compression headers for static assets
  if (request.nextUrl.pathname.match(/\.(js|css|html|svg|png|jpg|jpeg|gif|ico|woff|woff2|ttf|eot)$/)) {
    // Enable compression for static assets
    if (acceptEncoding.includes('br')) {
      response.headers.set('Content-Encoding', 'br');
    } else if (acceptEncoding.includes('gzip')) {
      response.headers.set('Content-Encoding', 'gzip');
    }
    
    // Set cache headers for static assets
    response.headers.set('Cache-Control', 'public, max-age=31536000, immutable');
  }

  // Add security headers
  response.headers.set('X-Content-Type-Options', 'nosniff');
  response.headers.set('X-Frame-Options', 'DENY');
  response.headers.set('X-XSS-Protection', '1; mode=block');
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
  
  // Add performance headers
  response.headers.set('X-DNS-Prefetch-Control', 'on');
  
  // Add CSP header for security
  const csp = [
    "default-src 'self'",
    "script-src 'self' 'unsafe-eval' 'unsafe-inline'",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "style-src-elem 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src 'self' https://fonts.gstatic.com data:",
    "img-src 'self' data: blob: https:",
    "connect-src 'self' http://localhost:8000 http://localhost:8001 https://api.joytishdrishti.com",
    "frame-src 'none'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'"
  ].join('; ');

  response.headers.set('Content-Security-Policy', csp);

  return response;
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
    // Also match admin routes specifically for authentication
    '/admin/:path*',
  ],
};
