---
name: journey-recovery
description: Autonomous runbook for resolving high-stakes travel disruptions across Indian Railways, bus, and aviation corridors. Use when a passenger's train is cancelled, heavily delayed, or when a connection is broken.
---

# Intelligent Journey Recovery Skill (IRJA - SANKALP)

This skill provides domain knowledge, procedural workflows, and tool execution policies for resolving high-stakes travel emergencies across Indian transportation networks.

## 1. Disruption Triage Workflow
When a disruption is reported:
1. **Verify PNR & Cancellation Status**: Call `Tool_IRCTCRulesRefund` to confirm whether the train is officially cancelled by Indian Railways.
2. **Auto-Relief Advice**: Inform passenger that 100% refund is auto-credited for online e-tickets. For PRS counter tickets, prepare TDR guidelines within the 72-hour window.
3. **Establish Belief State**:
   - Extract destination, hard arrival deadline, exam reporting time, maximum budget, and luggage/fatigue tolerance.

## 2. Multi-Source Search Policy
1. **Direct Rail**: Search primary terminal pairs (e.g., `BPL`/`RKMP` to `SBC`/`YPR`/`SMVB`) across General (GN), Tatkal (TQ), and Premium Tatkal (PT).
2. **Intermediate Junction Rail-Hop**:
   - For South-bound traffic from Bhopal, evaluate:
     - **Itarsi Junction (ET)**: 90 km South, high frequency of trains from Jabalpur/Howrah heading to Bengaluru/Chennai.
     - **Nagpur (NGP)**: Central interchange node with direct connections to Bengaluru.
     - **Secunderabad / Kacheguda (SC/KCG)**: Major Deccan junction.
   - Enforce **Minimum Connection Time (MCT)**: $\ge 45$ mins cross-platform at same station; $\ge 90$ mins if station transit required.
3. **Multi-Modal Emergency Fallback**:
   - Intercity Express Bus (e.g., Bhopal ISBT to Indore Airport) + Flight to Kempegowda International Airport (BLR).
   - Overnight AC sleeper bus to Nagpur + morning flight or Vande Bharat to Bengaluru.

## 3. Multi-Attribute Utility Theory (MAUT) Scoring
Score each candidate journey $j$:
$$U(j) = 0.45 \cdot S_{\text{time}}(j) + 0.30 \cdot (1 - R_{\text{disruption}}(j)) + 0.15 \cdot S_{\text{cost}}(j) + 0.10 \cdot S_{\text{comfort}}(j)$$

Where:
- $S_{\text{time}} = \frac{T_{\text{max\_allowed}} - T_{\text{arrival}}}{T_{\text{max\_allowed}} - T_{\text{optimal}}}$
- $S_{\text{cost}} = \max\left(0, 1 - \frac{\text{Cost}}{\text{Budget}_{\text{max}}}\right)$
- $R_{\text{disruption}} = 1 - \prod P(\text{leg punctuality}) \times \prod P(\text{transfer buffer safety})$

## 4. Human-in-the-Loop Consequential Action Card
Present top 3 Pareto alternatives:
1. **Safe Option**: Maximum punctuality guarantee, minimal risk.
2. **Balanced Option**: Optimal trade-off between cost and buffer.
3. **Budget Option**: Maximum cost savings within safety boundaries.

Always request explicit confirmation before executing bookings or cancellations.
