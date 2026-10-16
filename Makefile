CC ?= clang
CFLAGS ?= -Wall -Wextra -Werror -O3 -pthread -std=c11
TARGET = bin/mtpo_test
HOTSPOT_TARGET = bin/hotspot_test

SRCS = src/mtpo_saga.c tests/test_mtpo_concurrency.c
HOTSPOT_SRCS = src/mtpo_saga.c tests/test_hotspot_latency.c

all: $(TARGET) $(HOTSPOT_TARGET)

$(TARGET): $(SRCS)
	@mkdir -p bin
	$(CC) $(CFLAGS) -o $(TARGET) $(SRCS)

$(HOTSPOT_TARGET): $(HOTSPOT_SRCS)
	@mkdir -p bin
	$(CC) $(CFLAGS) -o $(HOTSPOT_TARGET) $(HOTSPOT_SRCS)

test: $(TARGET) $(HOTSPOT_TARGET)
	@echo "=== [1/3] Bare-Metal C11 Concurrency Stress Test ==="
	@./$(TARGET)
	@echo "\n=== [2/3] Hot-Spot Key p99 Latency Pressure Test (Single Cache Line) ==="
	@./$(HOTSPOT_TARGET)
	@echo "\n=== [3/3] Z3 Formal SMT2 Proofs (Pre-Order & Saga Inverse Confluence) ==="
	@z3 proofs/mtpo_preorder_invariant.smt2
	@z3 proofs/saga_inverse_confluence.smt2
	@python3 -m unittest discover -s tests -v

clean:
	rm -rf bin

.PHONY: all test clean
