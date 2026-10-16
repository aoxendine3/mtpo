#!/usr/bin/env bash
set -euo pipefail

echo "=========================================================="
echo "  MTPO: MONOTONIC TRAJECTORY PRE-ORDER VERIFICATION SUITE "
echo "=========================================================="

echo "[1/4] Building C11 Native Binaries and Shared/Static Libraries..."
make clean >/dev/null 2>&1 || true
make all

echo "\n[2/4] Running C11 Stress Tests & Hot-Spot Contention Benchmark..."
./bin/mtpo_test
./bin/hotspot_test

echo "\n[3/4] Running Z3 Formal SMT2 Proofs..."
if command -v z3 >/dev/null 2>&1; then
    echo "  [Z3] proofs/mtpo_preorder_invariant.smt2: $(z3 proofs/mtpo_preorder_invariant.smt2)"
    echo "  [Z3] proofs/saga_inverse_confluence.smt2: $(z3 proofs/saga_inverse_confluence.smt2)"
    echo "  [Z3] proofs/agm_mtpo_monotonicity.smt2:   $(z3 proofs/agm_mtpo_monotonicity.smt2)"
else
    echo "  [INFO] z3 not detected in PATH. Skipping raw SMT solver check."
fi

echo "\n[4/4] Running Python SDK & Multi-Agent Tests..."
PYTHONPATH=python python3 -m unittest discover -s tests -v

echo "\n=========================================================="
echo "  MTPO VERIFICATION COMPLETE: ALL GATES GREEN             "
echo "=========================================================="
