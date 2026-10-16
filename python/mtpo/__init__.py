"""
MTPO: Monotonic Trajectory Pre-Order Python SDK
===============================================
Python bindings for the MTPO HexCell lock-free memory ring and 3-Phase Saga Engine.
Provides high-performance multi-agent atomic synchronization and compensation.
"""

import ctypes
import os
import platform
import subprocess
import threading
from typing import Optional

HEXCELL_SLOTS = 6
CACHE_LINE_SIZE = 64

# Try to locate or build the native C library
def _get_native_lib():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    lib_name = "libmtpo.dylib" if platform.system() == "Darwin" else "libmtpo.so"
    lib_path = os.path.join(base_dir, "bin", lib_name)

    if not os.path.exists(lib_path):
        # Attempt just-in-time compilation via Makefile or CC
        src_path = os.path.join(base_dir, "src", "mtpo_saga.c")
        if os.path.exists(src_path):
            os.makedirs(os.path.join(base_dir, "bin"), exist_ok=True)
            cc = os.environ.get("CC", "clang" if platform.system() == "Darwin" else "gcc")
            cmd = [cc, "-O3", "-shared", "-fPIC", "-pthread", "-std=c11", "-o", lib_path, src_path]
            try:
                subprocess.run(cmd, check=True, capture_output=True)
            except Exception:
                return None

    if os.path.exists(lib_path):
        try:
            lib = ctypes.CDLL(lib_path)
            # Setup argument and return types
            # void mtpo_ring_init(HexCellRing *ring);
            lib.mtpo_ring_init.argtypes = [ctypes.c_void_p]
            lib.mtpo_ring_init.restype = None

            # bool mtpo_saga_execute(HexCellRing *ring, uint32_t slot_idx, uint64_t tx_id, uint64_t new_val, bool inject_fault);
            lib.mtpo_saga_execute.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint64, ctypes.c_uint64, ctypes.c_bool]
            lib.mtpo_saga_execute.restype = ctypes.c_bool

            # uint64_t mtpo_ring_read(HexCellRing *ring, uint32_t slot_idx);
            lib.mtpo_ring_read.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
            lib.mtpo_ring_read.restype = ctypes.c_uint64

            return lib
        except Exception:
            return None
    return None

_NATIVE_LIB = _get_native_lib()


class HexCellRing:
    """
    6-fold symmetrical lock-free memory ring with 3-Phase Saga compensation.
    Wraps bare-metal C11 implementation when available, with thread-safe pure Python fallback.
    """
    def __init__(self):
        self._native = _NATIVE_LIB
        if self._native is not None:
            # Allocate 1024 bytes buffer for C struct HexCellRing
            self._buf = ctypes.create_string_buffer(1024)
            self._native.mtpo_ring_init(self._buf)
        else:
            # Fallback pure-python state
            self._lock = threading.Lock()
            self._active_slots = [0] * HEXCELL_SLOTS
            self._shadow_slots = [0] * HEXCELL_SLOTS
            self._total_committed = 0
            self._total_compensated = 0

    def execute_saga(self, slot_idx: int, tx_id: int, new_val: int, inject_fault: bool = False) -> bool:
        """
        Executes a 3-Phase Saga transaction on the specified slot:
          Phase 1: Reserve optimistic lease
          Phase 2: Mutate in isolated shadow slot
          Phase 3A: Commit via atomic CAS
          Phase 3B: Compensate (rollback) on failure or fault injection
        Returns True if committed, False if rolled back.
        """
        if slot_idx < 0 or slot_idx >= HEXCELL_SLOTS:
            raise ValueError(f"slot_idx must be between 0 and {HEXCELL_SLOTS - 1}")

        if self._native is not None:
            return bool(self._native.mtpo_saga_execute(self._buf, slot_idx, tx_id, new_val, inject_fault))

        with self._lock:
            # Phase 1: Reserve
            initial_val = self._active_slots[slot_idx]

            # Phase 2: Mutate shadow
            self._shadow_slots[slot_idx] = new_val

            if inject_fault:
                # Phase 3B: Compensate
                self._shadow_slots[slot_idx] = initial_val
                self._total_compensated += 1
                return False

            # Phase 3A: Commit
            self._active_slots[slot_idx] = new_val
            self._total_committed += 1
            return True

    def read(self, slot_idx: int) -> int:
        """
        Reads the currently committed active state for the given slot.
        """
        if slot_idx < 0 or slot_idx >= HEXCELL_SLOTS:
            raise ValueError(f"slot_idx must be between 0 and {HEXCELL_SLOTS - 1}")

        if self._native is not None:
            return int(self._native.mtpo_ring_read(self._buf, slot_idx))

        with self._lock:
            return self._active_slots[slot_idx]

    @property
    def is_native(self) -> bool:
        """True if backed by bare-metal C11 library, False if pure-python fallback."""
        return self._native is not None

__all__ = ["HexCellRing", "HEXCELL_SLOTS"]
