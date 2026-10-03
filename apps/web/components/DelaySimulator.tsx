"use client";

import { useState } from "react";
import { simulateDelay } from "@/lib/api";
import { Leg, SimulateDelayResponse } from "@/lib/types";

interface DelaySimulatorProps {
  tripId: string;
  legs: Leg[];
  originalPOntime: number;
}

export default function DelaySimulator({ tripId, legs, originalPOntime }: DelaySimulatorProps) {
  const [selectedLegIndex, setSelectedLegIndex] = useState(0);
  const [delayMinutes, setDelayMinutes] = useState(30);
  const [simResult, setSimResult] = useState<SimulateDelayResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRunSimulation = async (minutesToInject?: number) => {
    const mins = minutesToInject !== undefined ? minutesToInject : delayMinutes;
    setDelayMinutes(mins);
    setIsLoading(true);
    setError(null);

    try {
      const res = await simulateDelay({
        trip_id: tripId,
        leg_index: selectedLegIndex,
        injected_delay_minutes: mins,
      });
      setSimResult(res);
    } catch (err: any) {
      setError(err.message || "Failed to simulate delay.");
    } finally {
      setIsLoading(false);
    }
  };

  const quickButtons = [15, 30, 45, 60, 90, 120];

  return (
    <div className="w-full bg-surface-container-lowest border border-ink-border rounded-xl p-5 md:p-6 shadow-sm">
      <div className="flex items-center justify-between pb-3 border-b border-ink-border">
        <div>
          <h3 className="text-sm font-semibold text-ink-primary">Interactive Journey Disruption Simulator</h3>
          <p className="text-xs text-ink-muted">
            Simulate operational delays on active legs to see how SANKALP&apos;s Monte Carlo engine reacts.
          </p>
        </div>
        <span className="text-[11px] px-2 py-0.5 rounded bg-surface-container text-ink-secondary border border-ink-border">
          Active Monitor
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 my-4">
        {/* Leg Selection */}
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-ink-secondary">Select Journey Segment</label>
          <select
            value={selectedLegIndex}
            onChange={(e) => setSelectedLegIndex(Number(e.target.value))}
            className="bg-surface-container-lowest border border-ink-border rounded-lg px-3 py-2 text-xs text-ink-primary focus:outline-none focus:border-ink-primary"
          >
            {legs.map((leg, i) => (
              <option key={leg.leg_id} value={i}>
                Leg {i + 1}: {leg.operator_name} ({leg.identifier}) · {leg.mode}
              </option>
            ))}
          </select>
        </div>

        {/* Delay Minutes Selection */}
        <div className="flex flex-col gap-1">
          <div className="flex justify-between items-center text-xs">
            <span className="font-medium text-ink-secondary">Injected Delay</span>
            <span className="font-semibold text-ink-primary">+{delayMinutes} minutes</span>
          </div>
          <div className="flex items-center gap-1.5 flex-wrap pt-0.5">
            {quickButtons.map((btn) => (
              <button
                key={btn}
                type="button"
                onClick={() => handleRunSimulation(btn)}
                className={`px-2.5 py-1 rounded text-xs transition-colors border ${
                  delayMinutes === btn
                    ? "bg-primary-container text-white border-primary-container"
                    : "bg-surface-container-lowest hover:bg-surface-container border-ink-border text-ink-secondary"
                }`}
              >
                +{btn}m
              </button>
            ))}
          </div>
        </div>
      </div>

      <button
        type="button"
        onClick={() => handleRunSimulation()}
        disabled={isLoading}
        className="w-full py-2 px-4 rounded-lg bg-surface-container-high hover:bg-surface-container text-ink-primary text-xs font-medium border border-ink-border transition-colors flex items-center justify-center gap-2"
      >
        {isLoading ? <span>Recalculating 10,000 Monte Carlo Trials...</span> : <span>Run Disruption Analysis</span>}
      </button>

      {error && <div className="mt-3 p-2.5 rounded bg-red-50 text-red-700 text-xs border border-red-200">{error}</div>}

      {/* Simulation Result Presentation */}
      {simResult && (
        <div className="mt-5 pt-4 border-t border-ink-border space-y-4">
          <div
            className={`p-3.5 rounded-lg border text-xs ${
              simResult.is_deadline_at_risk
                ? "bg-red-50 text-red-900 border-red-200"
                : "bg-emerald-50 text-emerald-900 border-emerald-200"
            }`}
          >
            <div className="font-semibold flex items-center justify-between">
              <span>{simResult.is_deadline_at_risk ? "⚠️ Deadline Compromised" : "✅ Buffer Holds Safe"}</span>
              <span className="text-[11px] font-bold">
                {Math.round(simResult.recalculated_metrics.p_ontime * 100)}% On-Time
              </span>
            </div>
            <p className="mt-1 text-[11px] leading-relaxed">{simResult.risk_explanation}</p>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
            <div className="p-2.5 rounded bg-surface-container-low border border-ink-border/50">
              <span className="text-[10px] text-ink-muted uppercase">Original Certainty</span>
              <div className="font-semibold text-ink-primary mt-0.5">{Math.round(originalPOntime * 100)}%</div>
            </div>
            <div className="p-2.5 rounded bg-surface-container-low border border-ink-border/50">
              <span className="text-[10px] text-ink-muted uppercase">Recalculated</span>
              <div
                className={`font-semibold mt-0.5 ${
                  simResult.is_deadline_at_risk ? "text-red-700" : "text-emerald-700"
                }`}
              >
                {Math.round(simResult.recalculated_metrics.p_ontime * 100)}%
              </div>
            </div>
            <div className="p-2.5 rounded bg-surface-container-low border border-ink-border/50">
              <span className="text-[10px] text-ink-muted uppercase">95% Wilson Band</span>
              <div className="font-medium text-ink-primary mt-0.5 text-[11px]">
                {(simResult.recalculated_metrics.p_ontime_ci_95[0] * 100).toFixed(0)}% –{" "}
                {(simResult.recalculated_metrics.p_ontime_ci_95[1] * 100).toFixed(0)}%
              </div>
            </div>
            <div className="p-2.5 rounded bg-surface-container-low border border-ink-border/50">
              <span className="text-[10px] text-ink-muted uppercase">Broken Transfer Risk</span>
              <div className="font-semibold text-ink-primary mt-0.5">
                {Math.round(simResult.recalculated_metrics.missed_connection_rate * 100)}%
              </div>
            </div>
          </div>

          {/* On-Demand Replacement Route Card */}
          {simResult.replacement_plan && (
            <div className="mt-4 p-4 rounded-xl border border-primary-container/40 bg-surface-container-lowest shadow-sm">
              <div className="flex items-center justify-between pb-2 border-b border-ink-border">
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-600 animate-ping" />
                  <span className="text-xs font-semibold text-ink-primary uppercase tracking-wide">
                    Autonomous Recovery Plan Generated
                  </span>
                </div>
                <span className="text-[11px] px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 font-semibold">
                  {Math.round(simResult.replacement_plan.metrics.p_ontime * 100)}% Certainty
                </span>
              </div>

              <div className="py-2.5 text-xs text-ink-secondary">
                <p>{simResult.replacement_plan.plain_reason}</p>
                <div className="flex items-center gap-4 mt-2 font-medium text-ink-primary">
                  <span>Fare: ₹{simResult.replacement_plan.total_fare_inr}</span>
                  <span>·</span>
                  <span>Duration: {Math.floor(simResult.replacement_plan.total_duration_minutes / 60)}h {simResult.replacement_plan.total_duration_minutes % 60}m</span>
                  <span>·</span>
                  <span>{simResult.replacement_plan.legs.length} replacement segment(s)</span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
