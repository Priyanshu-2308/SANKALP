"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import TripClientView from "./[id]/TripClientView";

function TripContent() {
  const searchParams = useSearchParams();
  const tripId = searchParams.get("id") || "demo";
  return <TripClientView id={tripId} />;
}

export default function TripPage() {
  return (
    <Suspense
      fallback={
        <div className="w-full max-w-[800px] mx-auto px-4 py-16 flex flex-col items-center justify-center">
          <div className="w-8 h-8 border-2 border-primary-container border-t-transparent rounded-full animate-spin mb-3" />
          <p className="text-xs text-ink-muted">Loading journey audit log...</p>
        </div>
      }
    >
      <TripContent />
    </Suspense>
  );
}
