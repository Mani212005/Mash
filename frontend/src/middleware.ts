import { withAuth } from "next-auth/middleware"

// Protect all routes under /dashboard, /conversations, /agents, etc.
export default withAuth({
  pages: {
    signIn: '/login',
  },
})

export const config = {
  matcher: [
    '/dashboard/:path*',
    '/conversations/:path*',
    '/agents/:path*',
    '/knowledge/:path*',
    '/tickets/:path*',
    '/settings/:path*',
  ],
}
