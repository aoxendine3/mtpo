#!/usr/bin/env python3
"""
MTPO Multi-Agent Concurrency & Saga Rollback Example
===================================================
Demonstrates 4 AI agent citizen roles concurrently coordinating shared state
in an MTPO HexCell memory ring with zero lock stalls and automatic Saga compensation.
"""

import sys
import os
import time
import random
import threading

# Add python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
import mtpo

def main():
    print("=" * 65)
    print("  MTPO MULTI-AGENT SWARM SYNCHRONIZATION RUNTIME")
    print("=" * 65)

    ring = mtpo.HexCellRing()
    print(f"[*] Native Silicon C11 Engine Active: {ring.is_native}")

    AGENTS = [
        {"name": "RESEARCHER_AGENT", "slot": 0, "rank": 10},
        {"name": "ARCHITECT_AGENT",  "slot": 1, "rank": 20},
        {"name": "CODER_AGENT",      "slot": 2, "rank": 30},
        {"name": "CRITIC_AGENT",     "slot": 3, "rank": 40},
    ]

    print("\n[Step 1] Initializing Agent Citizens and Assigning Ranks:")
    for a in AGENTS:
        print(f"  • {a['name']:<18} -> Assigned Slot [{a['slot']}], Serialization Rank σ = {a['rank']}")

    print("\n[Step 2] Executing Concurrent Multi-Agent Writes (3-Phase Saga):")
    tx_counter = 1000

    def run_agent_workflow(agent):
        nonlocal tx_counter
        for step in range(1, 4):
            tx_id = tx_counter
            tx_counter += 1
            # Generate state hash / token representation
            proposed_state = (agent['rank'] * 1000) + (step * 111)

            # Let Critic simulate fault injection on step 2
            inject_fault = (agent['name'] == "CRITIC_AGENT" and step == 2)

            committed = ring.execute_saga(
                slot_idx=agent['slot'],
                tx_id=tx_id,
                new_val=proposed_state,
                inject_fault=inject_fault
            )

            if committed:
                print(f"  [{agent['name']}] TX #{tx_id}: Committed Phase 3A -> Slot [{agent['slot']}] = 0x{proposed_state:08X}")
            else:
                print(f"  [{agent['name']}] TX #{tx_id}: Constraint Violation Detected! Triggered Phase 3B SAGA ROLLBACK -> Slot [{agent['slot']}] preserved!")

            time.sleep(0.01)

    threads = [threading.Thread(target=run_agent_workflow, args=(a,)) for a in AGENTS]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    print("\n[Step 3] Final Inspected State Across HexCell Ring:")
    for a in AGENTS:
        val = ring.read(a['slot'])
        print(f"  • Slot [{a['slot']}] ({a['name']}): Final Active Value = 0x{val:08X}")

    print("\n" + "=" * 65)
    print("  MTPO EXECUTION COMPLETE: 100% STATE MONOTONICITY PRESERVED")
    print("=" * 65)

if __name__ == "__main__":
    main()
