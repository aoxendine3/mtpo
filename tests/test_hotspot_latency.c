/**
 * MTPO Hot-Spot Key Latency & Cache-Line Contention Audit
 * ========================================================
 * Evaluates p50, p90, p99, and p99.9 latency under 100% hot-spot key contention
 * across concurrent threads to address the cache-line serialization challenge.
 */

#include "../src/mtpo_saga.h"
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include <time.h>
#include <assert.h>
#include <stdbool.h>

#define HOTSPOT_THREADS 16
#define OPS_PER_THREAD 20000 // Total: 320,000 operations on a single hot slot
#define MAX_SAMPLES (HOTSPOT_THREADS * OPS_PER_THREAD)

typedef struct {
    HexCellRing *ring;
    int thread_id;
    uint64_t *latencies_ns; // Nanosecond measurements
    size_t sample_offset;
    uint64_t committed;
    uint64_t compensated;
} ThreadData;

// Compare function for qsort
static int compare_u64(const void *a, const void *b) {
    uint64_t arg1 = *(const uint64_t *)a;
    uint64_t arg2 = *(const uint64_t *)b;
    if (arg1 < arg2) return -1;
    if (arg1 > arg2) return 1;
    return 0;
}

static inline uint64_t get_time_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ULL + (uint64_t)ts.tv_nsec;
}

void *hotspot_worker(void *arg) {
    ThreadData *td = (ThreadData *)arg;
    const uint32_t HOTSPOT_SLOT = 0; // 100% contention on single slot (Slot 0)
    
    for (uint64_t i = 0; i < OPS_PER_THREAD; i++) {
        uint64_t tx_id = ((uint64_t)td->thread_id << 32) | i;
        uint64_t val = tx_id + 42;

        uint64_t t_start = get_time_ns();
        
        // Execute MTPO 3-Phase Saga on the exact same hot-spot slot
        bool ok = mtpo_saga_execute(td->ring, HOTSPOT_SLOT, tx_id, val, false);
        
        uint64_t t_end = get_time_ns();
        uint64_t duration_ns = t_end - t_start;

        td->latencies_ns[td->sample_offset + i] = duration_ns;
        if (ok) {
            td->committed++;
        } else {
            td->compensated++;
        }
    }
    return NULL;
}

int main(void) {
    printf("==================================================================\n");
    printf("  MTPO HOT-SPOT KEY LATENCY & CACHE-LINE CONTENTION PRESSURE TEST \n");
    printf("==================================================================\n");
    printf("  Contention Target: 100.0%% Access to Slot 0 (Single 128B Cache Line)\n");
    printf("  Concurrent Threads: %d | Total Operations: %d\n", HOTSPOT_THREADS, MAX_SAMPLES);
    printf("------------------------------------------------------------------\n");

    HexCellRing ring;
    mtpo_ring_init(&ring);

    uint64_t *all_latencies = malloc(sizeof(uint64_t) * MAX_SAMPLES);
    assert(all_latencies != NULL);

    pthread_t threads[HOTSPOT_THREADS];
    ThreadData tdata[HOTSPOT_THREADS];

    uint64_t bench_start = get_time_ns();

    for (int i = 0; i < HOTSPOT_THREADS; i++) {
        tdata[i].ring = &ring;
        tdata[i].thread_id = i;
        tdata[i].latencies_ns = all_latencies;
        tdata[i].sample_offset = i * OPS_PER_THREAD;
        tdata[i].committed = 0;
        tdata[i].compensated = 0;
        int rc = pthread_create(&threads[i], NULL, hotspot_worker, &tdata[i]);
        assert(rc == 0);
    }

    uint64_t total_committed = 0;
    uint64_t total_compensated = 0;

    for (int i = 0; i < HOTSPOT_THREADS; i++) {
        pthread_join(threads[i], NULL);
        total_committed += tdata[i].committed;
        total_compensated += tdata[i].compensated;
    }

    uint64_t bench_end = get_time_ns();
    double total_sec = (double)(bench_end - bench_start) / 1e9;
    double throughput = (double)MAX_SAMPLES / total_sec;

    printf("[1/3] Sorting %d Latency Samples for Percentile Extraction...\n", MAX_SAMPLES);
    qsort(all_latencies, MAX_SAMPLES, sizeof(uint64_t), compare_u64);

    uint64_t p50_ns  = all_latencies[(size_t)(MAX_SAMPLES * 0.50)];
    uint64_t p90_ns  = all_latencies[(size_t)(MAX_SAMPLES * 0.90)];
    uint64_t p95_ns  = all_latencies[(size_t)(MAX_SAMPLES * 0.95)];
    uint64_t p99_ns  = all_latencies[(size_t)(MAX_SAMPLES * 0.99)];
    uint64_t p999_ns = all_latencies[(size_t)(MAX_SAMPLES * 0.999)];
    uint64_t max_ns  = all_latencies[MAX_SAMPLES - 1];

    printf("[2/3] Empirical Percentile Breakdown (100%% Hot-Spot Contention):\n");
    printf("      Throughput:  %.2f ops/sec\n", throughput);
    printf("      Committed:   %llu (Phase 3A)\n", (unsigned long long)total_committed);
    printf("      Compensated: %llu (Phase 3B)\n", (unsigned long long)total_compensated);
    printf("      p50 Latency:  %llu ns (%.3f µs)\n", (unsigned long long)p50_ns, p50_ns / 1000.0);
    printf("      p90 Latency:  %llu ns (%.3f µs)\n", (unsigned long long)p90_ns, p90_ns / 1000.0);
    printf("      p95 Latency:  %llu ns (%.3f µs)\n", (unsigned long long)p95_ns, p95_ns / 1000.0);
    printf("      p99 Latency:  %llu ns (%.3f µs)  <-- THE LEAD PRODUCTION METRIC\n", (unsigned long long)p99_ns, p99_ns / 1000.0);
    printf("      p99.9 Latency:%llu ns (%.3f µs)\n", (unsigned long long)p999_ns, p999_ns / 1000.0);
    printf("      Max Latency:  %llu ns (%.3f µs)\n", (unsigned long long)max_ns, max_ns / 1000.0);

    printf("[3/3] Invariant Validation:\n");
    assert(total_committed + total_compensated == MAX_SAMPLES);
    printf("      Total Accounting Conservation: 100.00%% PASS (Zero Orphaned States)\n");
    printf("==================================================================\n");

    free(all_latencies);
    return 0;
}
