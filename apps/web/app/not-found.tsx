"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

export default function NotFound() {
  const [redirecting, setRedirecting] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const pathname = window.location.pathname;

    // Check if the 404 path is a direct link to a dynamic trip ID, e.g. /SANKALP/trip/trip_12345/
    const tripMatch = pathname.match(/\/trip\/([^/]+)\/?$/);
    if (tripMatch && tripMatch[1] && tripMatch[1] !== "trip") {
      setRedirecting(true);
      const tripId = tripMatch[1];
      const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";
      window.location.replace(`${basePath}/trip/?id=${encodeURIComponent(tripId)}`);
    }
  }, []);

  if (redirecting) {
    return (
      <div className="w-full max-w-[600px] mx-auto px-4 py-24 text-center">
        <div className="w-8 h-8 border-2 border-primary-container border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-xs text-ink-muted">Redirecting to journey details...</p>
      </div>
    );
  }

  return (
    <div className="w-full max-w-[600px] mx-auto px-4 py-24 text-center">
      <div className="bg-surface-container-lowest border border-ink-border rounded-xl p-8 shadow-sm">
        <h1 className="text-4xl font-bold text-ink-primary mb-2">404</h1>
        <h2 className="text-base font-semibold text-ink-primary mb-2">Page Not Found</h2>
        <p className="text-xs text-ink-secondary mb-6">
          The requested page does not exist or has been moved.
        </p>
        <Link
          href="/"
          className="inline-flex px-4 py-2 rounded-lg bg-primary-container text-white text-xs font-medium hover:bg-primary-hover transition-colors"
        >
          Back to Home
        </Link>
      </div>
    </div>
  );
}
