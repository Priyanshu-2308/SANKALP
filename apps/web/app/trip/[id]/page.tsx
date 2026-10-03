import TripClientView from "./TripClientView";

export default async function TripPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = await params;
  return <TripClientView id={resolvedParams.id} />;
}
