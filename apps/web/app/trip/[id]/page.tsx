import TripClientView from "./TripClientView";

export const dynamicParams = true;

// Required for Next.js static HTML export (e.g. GitHub Pages)
export function generateStaticParams() {
  return [
    { id: "demo" },
    { id: "trip_preview_1" },
  ];
}

export default async function TripPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = await params;
  return <TripClientView id={resolvedParams.id} />;
}
