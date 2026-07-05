// Backend base URL, no trailing slash.
// Preferred: set VITE_API_BASE_URL in your hosting env (Vercel > Settings >
// Environment Variables) so switching backends needs no code change.
// The hardcoded value below is only the fallback for local dev convenience.
const fromEnv = import.meta.env.VITE_API_BASE_URL as string | undefined;

export const API_BASE_URL = (
  fromEnv || 'https://artifact-generator-backend-58653101019.us-central1.run.app'
).replace(/\/+$/, '');
// For local backend testing set VITE_API_BASE_URL=http://localhost:8000 in .env.local
