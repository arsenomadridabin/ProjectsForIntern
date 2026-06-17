import time
 
TARGET = 10_000_000_000
ESTIMATED_ANSWER = 252_097_800_623
 
def is_prime(n):
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True
 
count = 0
num = 2
start = time.time()
 
while True:
    if is_prime(num):
        count += 1
        if count % 1_000_000 == 0:
            elapsed = time.time() - start
            pct = (num / ESTIMATED_ANSWER) * 100
            eta = (elapsed / pct) * (100 - pct) if pct > 0 else 0
            print(f"{pct:.2f}% | primes: {count:,} | current: {num:,} | elapsed: {elapsed:.0f}s | ETA: {eta:.0f}s")
        if count == TARGET:
            elapsed = time.time() - start
            print(f"\nThe 10 billionth prime is: {num}")
            print(f"Total time: {elapsed:.1f}s ({elapsed/3600:.1f} hours)")
            break
    num += g
