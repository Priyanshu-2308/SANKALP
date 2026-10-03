import type { Metadata } from "next";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import "./globals.css";

export const metadata: Metadata = {
  title: "SANKALP — Autonomous Multi-Modal Transit Recovery",
  description:
    "Instant probabilistic journey-recovery platform for India when trains or flights are cancelled or delayed. Powered by Monte Carlo simulation and Pareto optimization.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen flex flex-col bg-surface font-sans antialiased text-ink-primary">
        <Navbar />
        <main className="flex-1 w-full pt-16 flex flex-col items-center">
          {children}
        </main>
        <Footer />
      </body>
    </html>
  );
}
