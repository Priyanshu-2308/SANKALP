"""
SANKALP: System for Autonomous Navigation, Knowledge-driven Adaptation, and Logistic Planning
Interactive Simulation & Scenario Testing Runner

Flags:
  python simulate.py                # Automated end-to-end corridor recovery demonstration
  python simulate.py --interactive  # Interactive step-by-step user choices
  python simulate.py --conflict     # Test conflicting telemetry sensor fusion
  python simulate.py --resilience   # Test IRCTC PRS gateway 503 circuit-breaker retry
  python simulate.py --mutation     # Test dynamic constraint mutation mid-process
  python simulate.py --all-edge-cases # Test all edge cases & disruption contingencies
"""
import sys
import time
from datetime import datetime, timedelta
from sankalp.orchestrator import SankalpOrchestrator
from sankalp.agent import SankalpAgent
from sankalp.mock_data import get_base_date

def print_banner():
    banner = """
================================================================================
          S A N K A L P  :  Autonomous Multi-Modal Journey Recovery Engine
================================================================================
Architecture: ReAct + Reflexion Agent Swarm with Deterministic Decision Science
Real-Time Dynamic Contingency & Multi-Corridor Re-Routing Platform
================================================================================
"""
    print(banner)

def run_simulation(
    interactive: bool = False,
    demo_conflict: bool = False,
    demo_resilience: bool = False,
    demo_mutation: bool = False
):
    print_banner()
    base_date = get_base_date()

    print("[INCIDENT 10:45 AM] Train 12628 (Karnataka Express) is CANCELLED by Indian Railways.")
    print("Passenger PNR: 2458901234. Scheduled Dep: 11:30 AM from Bhopal Junction.")
    print("Passenger Destination: Whitefield, Bengaluru for GATE Examination tomorrow morning.")
    print("--------------------------------------------------------------------------------\n")

    # Initialize Orchestrator
    orchestrator = SankalpOrchestrator(
        pnr="2458901234",
        cancelled_train_no="12628",
        base_date=base_date
    )

    # 1. Disruption Triage & Financial Safeguard
    print(">>> [PHASE 1: PERCEPTION, TRIAGE & FINANCIAL LIQUIDITY SAFEGUARD]")
    triage = orchestrator.step1_disruption_triage()
    print(f"[*] Agent Perception   : {triage['message']}")
    print(f"[*] Gazette Compliance : {triage['gazette_clause']}")
    print(f"[*] Auto-Relief Action : {triage['refund_advice']}")
    print(f"[*] Recovered Liquidity: INR {triage['refund_amount']:,.2f}\n")
    time.sleep(0.3)

    # Edge Case 1: Conflicting Sensor Information Resolution
    if demo_conflict:
        print(">>> [EDGE CASE TEST: CONFLICTING SENSOR INFORMATION RESOLUTION (PS SEC 5)]")
        print("[!] Detection: Telemetry sources report divergent statuses for incoming corridor:")
        conflict_res = orchestrator.resolve_conflicting_telemetry("20846")
        for src in conflict_res["sources_evaluated"]:
            print(f"    - [{src['source']}] Delay: {src['delay_minutes']}m | Confidence: {src['confidence']*100:.0f}% | Note: {src['status']}")
        print(f"[*] Decision Engine Fusion: {conflict_res['decision']}")
        print(f"[*] Root Cause Identified : {conflict_res['root_cause']}\n")
        time.sleep(0.3)

    # 2. Socratic Constraint Elicitation
    print(">>> [PHASE 2: PROACTIVE SOCRATIC CONSTRAINT ELICITATION (ReAct Cycle)]")
    if interactive:
        print("Agent: 'Hello! I see your Karnataka Express was cancelled. What is your exact exam reporting time and budget limit?'")
        exam_hour = input("Enter Exam Reporting Hour tomorrow (default 9 for 09:00 AM): ").strip()
        exam_hour = int(exam_hour) if exam_hour.isdigit() else 9
        budget_in = input("Enter Budget Ceiling in INR (default 4000): ").strip()
        budget = float(budget_in) if budget_in.replace('.','',1).isdigit() else 4000.0
    else:
        exam_hour = 9
        budget = 4000.0

    exam_time = (base_date + timedelta(days=1)).replace(hour=exam_hour, minute=0)
    elicitation = orchestrator.step2_elicit_constraints(exam_time=exam_time, budget=budget, venue_area="Whitefield, Bengaluru")
    
    # Run the Agent's ReAct Cognition Cycle
    react_output = orchestrator.agent.execute_react_cycle(f"Reporting at {exam_hour}:00 AM, budget INR {budget}")
    print("[*] ReAct Cognition Traces:")
    for i, st in enumerate(orchestrator.agent.steps[:3], 1):
        print(f"    Step {i}:")
        print(f"      • Thought : {st.thought[:80]}...")
        if st.action:
            print(f"      • Action  : {st.action} (Input: {st.action_input})")
        if st.reflexion:
            print(f"      • Reflexion: {st.reflexion[:80]}...")

    print(f"\n[*] Exam Venue Area     : {elicitation['venue_area']}")
    print(f"[*] Exam Reporting Time : {elicitation['exam_time']}")
    print(f"[*] Station Cutoff      : {elicitation['hard_deadline']} (Mandatory buffer for last-mile transit)")
    print(f"[*] Budget Bound Ceiling: INR {elicitation['budget']:,.2f}\n")
    time.sleep(0.3)

    # 3. Combinatorial Graph Pathfinder & Monte Carlo Delay Simulation
    print(">>> [PHASE 3: GRAPH PATHFINDING & 10,000-TRIAL MONTE CARLO SIMULATION]")
    ranked_plans = orchestrator.step3_explore_and_rank_plans()
    print(f"[*] Discovered {len(ranked_plans)} viable recovery corridors with verified last-mile connections:\n")

    for i, plan in enumerate(ranked_plans, 1):
        lm_desc = f"{plan.last_mile.carrier_name} ({plan.last_mile.duration_minutes}m)" if plan.last_mile else "Local Cab"
        print(f"  [{i}] [{plan.category}] {plan.name}")
        print(f"      Total Fare : INR {plan.total_fare:,.2f} | Transfers: {plan.num_transfers}")
        print(f"      Terminal Arr: {plan.final_arrival_time.strftime('%b %d, %I:%M %p')} -> Last-Mile: {lm_desc}")
        print(f"      Venue Arr  : {plan.venue_arrival_time.strftime('%b %d, %I:%M %p')} ({plan.venue_buffer_minutes}m slack before exam)")
        print(f"      Monte Carlo: {plan.monte_carlo_punctuality * 100:.1f}% on-time (95% CI: [{plan.confidence_interval_95[0]*100:.1f}%, {plan.confidence_interval_95[1]*100:.1f}%])")
        print(f"      MAUT Score : {plan.utility_score} / 1.000 | Disruption Risk: {plan.disruption_risk * 100:.1f}%\n")

    # Edge Case 4: Dynamic Constraint Mutation
    if demo_mutation:
        print(">>> [EDGE CASE TEST: DYNAMIC CONSTRAINT MUTATION (PS SEC 5)]")
        print("[!] EVENT: User calls back in panic: 'My exam was preponed to 07:30 AM, and my parents transferred emergency funds (Budget: INR 10,000)!'")
        new_exam = (base_date + timedelta(days=1)).replace(hour=7, minute=30)
        mut_res = orchestrator.mutate_user_constraints(new_exam, 10000.0)
        print(f"[*] Agent Reflexion     : {mut_res['reflexion']}")
        print(f"[*] Evicted Infeasible  : {len(mut_res['evicted_routes'])} routes pruned ({', '.join(mut_res['evicted_routes'][:2])}...)")
        print(f"[*] Elevated Route #1   : [{mut_res['new_top_recommendation'].category}] {mut_res['new_top_recommendation'].name}")
        print(f"    Fare: INR {mut_res['new_top_recommendation'].total_fare:,.2f} | Punctuality: {mut_res['new_top_recommendation'].monte_carlo_punctuality*100:.1f}%")
        print(f"    Venue Arrival: {mut_res['new_top_recommendation'].venue_arrival_time.strftime('%b %d, %I:%M %p')} (Safe overnight rest!)\n")
        ranked_plans = mut_res['ranked_plans']
        time.sleep(0.3)

    # Select corridor based on scenario
    if demo_mutation:
        chosen_plan = mut_res['new_top_recommendation']
    else:
        chosen_plan = next(
            (p for p in ranked_plans if "Wainganga" in p.name or "Nagpur" in p.name),
            ranked_plans[0]
        )

    if interactive:
        print(f"Enter option number to select (1-{len(ranked_plans)}) [default: {chosen_plan.name}]: ", end="")
        choice = input().strip()
        if choice.isdigit() and 1 <= int(choice) <= len(ranked_plans):
            chosen_plan = ranked_plans[int(choice) - 1]

    print(f"[*] Selected Corridor: [{chosen_plan.category}] {chosen_plan.name}")
    print(f"    Rationale: Optimal multi-attribute balance between budget (INR {chosen_plan.total_fare:,.2f}) and high punctuality.\n")
    print("--------------------------------------------------------------------------------\n")
    time.sleep(0.3)

    # 4. Zero-Trust Consequential Action Gate
    print(">>> [PHASE 4: ZERO-TRUST CONSEQUENTIAL ACTION GATE (HUMAN AUTHORIZATION REQUIRED)]")
    prep = orchestrator.step4_prepare_booking(chosen_plan.itinerary_id)
    print("  +-------------------------------------------------------------------------+")
    print("  |                 ZERO-TRUST HUMAN AUTHORIZATION GATE                     |")
    print("  +-------------------------------------------------------------------------+")
    print(f"  | Itinerary  : {prep['itinerary'].name}")
    print(f"  | Amount Due : INR {prep['total_payable']:,.2f}")
    print(f"  | Session ID : {prep['reservation_token']} (Valid for {prep['expires_in_seconds']}s)")
    print(f"  | Mandate URI: {prep['upi_intent_uri'][:52]}...")
    print(f"  | Last-Mile  : {prep['last_mile'].carrier_name if prep['last_mile'] else 'N/A'}")
    print(f"  | Security   : {prep['verification_type']} required (No headless debit allowed)")
    print("  +-------------------------------------------------------------------------+")

    if interactive:
        input("\nPress ENTER to authorize payment and proceed to ticketing... ")
    else:
        print("  [Passenger Biometric / UPI Intent Authorization Granted: PROCEED]\n")
    time.sleep(0.3)

    # 5. Execution & Gateway Resilience (Edge Case 2)
    print(">>> [PHASE 5: TRANSACTIONAL EXECUTION & GATEWAY RESILIENCE (PS SEC 5)]")
    receipt = orchestrator.step5_execute_booking(prep["reservation_token"], simulate_gateway_retry=demo_resilience)
    if receipt.get("resilience_log"):
        print("  [GATEWAY CIRCUIT BREAKER ACTIVATED]")
        for log_line in receipt["resilience_log"]:
            print(f"    • {log_line}")
    print(f"[*] Booking Success! Generated PNR: {receipt['pnr']}")
    print(f"[*] Coach/Berth Allotted : {receipt['coach_berth']}")
    print(f"[*] Active Watchdog ID   : {receipt['monitor_id']}")
    print(f"[*] Ticket Verification  : {receipt['qr_token']}\n")
    time.sleep(0.3)

    # 6. Active Telemetry Monitoring (Nominal)
    print(">>> [PHASE 6: ACTIVE TELEMETRY SENTINEL DAEMON (Tool 7)]")
    telemetry = orchestrator.step6_check_telemetry()
    print(f"[*] NTES GPS Tracking : Status = {telemetry['status']} | Active Carrier: {telemetry['carrier']}")
    print(f"[*] Junction Buffer   : {telemetry['remaining_buffer']} mins remaining at {telemetry['transfer_station']}")
    print("--------------------------------------------------------------------------------\n")
    time.sleep(0.3)

    # 7. In-Transit Disruption & Cascade Re-Planning Simulation (Edge Case 3)
    print(">>> [PHASE 7: SIMULATED IN-TRANSIT DISRUPTION & DYNAMIC CASCADE RE-PLANNING (PS SEC 5)]")
    print("[EVENT 18:30 PM] While passenger is en-route near Betul / Amla ghat section,")
    print("a freight derailment causes a sudden 110-MINUTE DELAY on the active incoming train.")
    print("Scheduled transfer buffer at junction is completely wiped out -> BROKEN CONNECTION.")
    print("Active Sentinel Daemon intercepts the delay signal via NTES...\n")

    replan_result = orchestrator.trigger_mid_journey_delay_simulation(delay_minutes=110)
    tel = replan_result["telemetry"]
    sol = replan_result["replan_solution"]

    print(f"[!] TELEMETRY ALARM    : {tel['status']} on {tel['carrier']}")
    print(f"[!] Buffer at Junction : {tel['transfer_station']} = {tel['remaining_buffer']} mins (Connection Broken!)")
    print(f"[!] Autonomous Action  : {tel['action_required']}\n")

    print(">>> [AUTONOMOUS CASCADE RECOVERY PLAN (ReAct Reflexion Engine)]")
    print(f"  [*] Action Decided     : {sol['switch_action']}")
    print(f"  [*] Cancel Missed Train: {sol['old_connecting_train']}")
    print(f"  [*] Refund Protection  : {sol['refund_note']}")
    print(f"  [*] Re-routed Carrier  : {sol['new_connecting_train']}")
    print(f"  [*] PRS Quota Applied  : {sol['quota_used']}")
    print(f"  [*] Station Arrival    : {sol['new_station_arrival']}")
    print(f"  [*] Last-Mile Rescue   : {sol['last_mile_override']}")
    print(f"  [*] Venue Exam Arrival : {sol['venue_arrival_time']} (Buffer before exam: {sol['buffer_remaining_for_exam']})")
    print(f"  [*] Recovery Confidence: {sol['confidence'] * 100:.1f}%\n")

    print("================================================================================")
    print("MISSION ACCOMPLISHED: Passenger reached Whitefield Exam Hall on-time despite 2 disruptions!")
    print("Zero-Hallucination PRS Grounding | Verifiable Monte Carlo Probabilities | Zero-Trust Safety")
    print("================================================================================")

if __name__ == "__main__":
    is_interactive = "--interactive" in sys.argv
    demo_conflict = "--conflict" in sys.argv or "--all-edge-cases" in sys.argv
    demo_resilience = "--resilience" in sys.argv or "--all-edge-cases" in sys.argv
    demo_mutation = "--mutation" in sys.argv or "--all-edge-cases" in sys.argv
    run_simulation(
        interactive=is_interactive,
        demo_conflict=demo_conflict,
        demo_resilience=demo_resilience,
        demo_mutation=demo_mutation
    )
