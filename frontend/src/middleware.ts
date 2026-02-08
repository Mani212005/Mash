// No middleware protection - all pages are publicly accessible
// Auth is optional: logged-in users see their private data (conversations, phone numbers)
// Non-logged-in users can browse dashboard, agents, knowledge base, etc.
export { default } from 'next-auth/middleware'

// Only protect conversations (contains private phone numbers)
export const config = {
  matcher: [],  // Empty = nothing is protected, auth is fully optional
}
