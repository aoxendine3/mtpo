CC ?= clang
CFLAGS ?= -Wall -Wextra -Werror -O3 -pthread -std=c11 -fPIC -Iinclude -Isrc
AR ?= ar
PREFIX ?= /usr/local

TARGET = bin/mtpo_test
HOTSPOT_TARGET = bin/hotspot_test
STATIC_LIB = bin/libmtpo.a

UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
    DYNLIB = bin/libmtpo.dylib
    DYNLIB_FLAGS = -dynamiclib
else
    DYNLIB = bin/libmtpo.so
    DYNLIB_FLAGS = -shared
endif

SRCS = src/mtpo_saga.c tests/test_mtpo_concurrency.c
HOTSPOT_SRCS = src/mtpo_saga.c tests/test_hotspot_latency.c
LIB_SRCS = src/mtpo_saga.c

all: $(TARGET) $(HOTSPOT_TARGET) $(STATIC_LIB) $(DYNLIB)

$(TARGET): $(SRCS)
	@mkdir -p bin
	$(CC) $(CFLAGS) -o $(TARGET) $(SRCS)

$(HOTSPOT_TARGET): $(HOTSPOT_SRCS)
	@mkdir -p bin
	$(CC) $(CFLAGS) -o $(HOTSPOT_TARGET) $(HOTSPOT_SRCS)

$(STATIC_LIB): $(LIB_SRCS)
	@mkdir -p bin
	$(CC) $(CFLAGS) -c -o bin/mtpo_saga.o $(LIB_SRCS)
	$(AR) rcs $(STATIC_LIB) bin/mtpo_saga.o

$(DYNLIB): $(LIB_SRCS)
	@mkdir -p bin
	$(CC) $(CFLAGS) $(DYNLIB_FLAGS) -o $(DYNLIB) $(LIB_SRCS)

test: $(TARGET) $(HOTSPOT_TARGET) $(DYNLIB)
	@echo "=== [1/4] Bare-Metal C11 Concurrency Stress Test ==="
	@./$(TARGET)
	@echo "\n=== [2/4] Hot-Spot Key p99 Latency Pressure Test (Single Cache Line) ==="
	@./$(HOTSPOT_TARGET)
	@echo "\n=== [3/4] Z3 Formal SMT2 Proofs (Pre-Order & Saga Inverse Confluence) ==="
	@if command -v z3 >/dev/null 2>&1; then \
		echo "  [Z3] mtpo_preorder_invariant.smt2:"; \
		z3 proofs/mtpo_preorder_invariant.smt2; \
		echo "  [Z3] saga_inverse_confluence.smt2:"; \
		z3 proofs/saga_inverse_confluence.smt2; \
	else \
		echo "  [INFO] z3 not detected in PATH. Skipping raw SMT solver check."; \
		echo "         Install via 'brew install z3' or 'apt install z3' to re-verify."; \
	fi
	@echo "\n=== [4/4] Python Invariant & Multi-Agent Tests ==="
	@python3 -m unittest discover -s tests -v

install: $(STATIC_LIB) $(DYNLIB)
	@mkdir -p $(DESTDIR)$(PREFIX)/include/mtpo
	@mkdir -p $(DESTDIR)$(PREFIX)/lib
	cp src/mtpo_saga.h $(DESTDIR)$(PREFIX)/include/mtpo/
	cp $(STATIC_LIB) $(DESTDIR)$(PREFIX)/lib/
	cp $(DYNLIB) $(DESTDIR)$(PREFIX)/lib/
	@echo "MTPO libraries and headers installed to $(DESTDIR)$(PREFIX)"

clean:
	rm -rf bin build *.egg-info dist

.PHONY: all test clean install
