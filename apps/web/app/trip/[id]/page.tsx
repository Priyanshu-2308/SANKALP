import TripClientView from "./TripClientView";

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
