"""
MTPO Python SDK Integration & Multi-Thread Unit Tests
=====================================================
Validates that the Python SDK correctly binds to the C11 native library,
maintains atomic multi-threaded consistency, and executes 3-Phase Saga rollbacks.
"""

import sys
import os
import unittest
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
import mtpo


class TestMtpoPythonSdk(unittest.TestCase):
    def setUp(self):
        self.ring = mtpo.HexCellRing()

    def test_01_native_binding_active(self):
        self.assertTrue(self.ring.is_native, "MTPO Python SDK must load native C library")

    def test_02_basic_saga_commit_and_read(self):
        for slot in range(mtpo.HEXCELL_SLOTS):
            val = (slot + 1) * 1000
            committed = self.ring.execute_saga(slot, 100 + slot, val, inject_fault=False)
            self.assertTrue(committed, f"Slot {slot} should commit cleanly")
            self.assertEqual(self.ring.read(slot), val, f"Slot {slot} value mismatch")

    def test_03_fault_injection_preserves_previous_state(self):
        slot = 2
        initial_val = 555
        self.ring.execute_saga(slot, 201, initial_val)
        self.assertEqual(self.ring.read(slot), initial_val)

        # Inject fault on subsequent transaction
        committed = self.ring.execute_saga(slot, 202, 9999, inject_fault=True)
        self.assertFalse(committed, "Injected fault must trigger Phase 3B compensation")
        self.assertEqual(self.ring.read(slot), initial_val, "Committed state must remain unpolluted after rollback")

    def test_04_concurrent_agent_threads(self):
        threads = []
        errors = []

        def agent_worker(agent_id, slot):
            try:
                for i in range(100):
                    val = agent_id * 10000 + i
                    self.ring.execute_saga(slot, agent_id * 1000 + i, val)
            except Exception as e:
                errors.append(e)

        for agent_id in range(12):
            slot = agent_id % mtpo.HEXCELL_SLOTS
            t = threading.Thread(target=agent_worker, args=(agent_id, slot))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Thread errors encountered: {errors}")
        for slot in range(mtpo.HEXCELL_SLOTS):
            read_val = self.ring.read(slot)
            self.assertGreater(read_val, 0, f"Slot {slot} should contain committed value")


if __name__ == "__main__":
    unittest.main()
