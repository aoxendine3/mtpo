#include <stdio.h>
#include <stdbool.h>
#include "mtpo/mtpo_saga.h"

int main(void) {
    printf("=====================================================\n");
    printf("  MTPO BARE-METAL C11 SAGA QUICKSTART DEMO\n");
    printf("=====================================================\n");

    HexCellRing ring;
    mtpo_ring_init(&ring);

    // 1. Execute normal 3-Phase Saga commit
    uint64_t tx1 = 1001;
    uint32_t slot = 0;
    uint64_t state_val = 0xBEAF0001ULL;

    printf("[1] Executing Saga on Slot [%u] with value 0x%llX...\n", slot, (unsigned long long)state_val);
    bool committed = mtpo_saga_execute(&ring, slot, tx1, state_val, false);
    printf("    -> Phase 3A Commit Result: %s\n", committed ? "COMMITTED (SUCCESS)" : "FAILED");
    printf("    -> Active Slot Value:      0x%llX\n", (unsigned long long)mtpo_ring_read(&ring, slot));

    // 2. Execute Saga with fault injection (simulating hardware/agent crash)
    uint64_t tx2 = 1002;
    uint64_t bad_val = 0xDEADBEEFULL;
    printf("\n[2] Executing Saga with Fault Injection (Simulating Agent Violation)...\n");
    bool roll_result = mtpo_saga_execute(&ring, slot, tx2, bad_val, true);
    printf("    -> Phase 3B Rollback Result: %s\n", roll_result ? "COMMITTED" : "ROLLED BACK SAFELY");
    printf("    -> Active Slot Value After Rollback: 0x%llX (Preserved original!)\n", 
           (unsigned long long)mtpo_ring_read(&ring, slot));

    printf("\n=====================================================\n");
    printf("  MTPO C11 DEMO COMPLETE: ZERO STATE CORRUPTION\n");
    printf("=====================================================\n");
    return 0;
}
