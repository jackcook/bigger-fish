#include <time.h>
#include <stdint.h>
#include <math.h>
#include <stdbool.h>

static const uint64_t c1 = 0xFF51AFD7ED558CCD;
static const uint64_t c2 = 0xC4CEB9FE1A85EC53;

static const uint64_t kMantissaMask = 0x000FFFFFFFFFFFFF;
static const uint64_t kExponentBits = 0x3FF0000000000000;

static const uint64_t secret = 0x7CAD93BF4A120ED1;

double timeResolutionSeconds = 1e-4;
bool enableJitter = true;

typedef union
{
    uint64_t i;
    double d;
} u;

uint64_t bit_cast_to_int(double x)
{
    u u1;
    u1.d = x;
    return u1.i;
}

double bit_cast_to_double(uint64_t x)
{
    u u1;
    u1.i = x;
    return u1.d;
}

uint64_t murmur_hash_3(uint64_t value)
{
    value ^= value >> 33;
    value *= c1;
    value ^= value >> 33;
    value *= c2;
    value ^= value >> 33;
    return value;
}

double to_double(uint64_t value)
{
    uint64_t random = (value & kMantissaMask) | kExponentBits;
    return bit_cast_to_double(random) - 1;
}

double threshold_for(double clamped_time)
{
    uint64_t time_hash = murmur_hash_3(bit_cast_to_int(clamped_time) ^ secret);
    return clamped_time + timeResolutionSeconds * to_double(time_hash);
}

double clamp_time_resolution(double time_seconds)
{
    double clamped_time =
        floor(time_seconds / timeResolutionSeconds) * timeResolutionSeconds;

    if (enableJitter)
    {
        double tick_threshold = threshold_for(clamped_time);

        if (time_seconds >= tick_threshold)
            return clamped_time + timeResolutionSeconds;
    }

    return clamped_time;
}

void configure_timer(double resolution, bool use_jitter)
{
    timeResolutionSeconds = resolution;
    enableJitter = use_jitter;
}

double timer()
{
    struct timespec time;
    clock_gettime(CLOCK_REALTIME, &time);
    double time_seconds = time.tv_sec + time.tv_nsec / 1e9;
    return clamp_time_resolution(time_seconds);
}