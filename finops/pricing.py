"""Pricing & purchasing economics — measure in $/1M-token, not $/GPU-hr.

Figures are June-2026 as-of snapshots from the deck's RESEARCH dossier; treat
live prices as fast-moving (re-baseline before each cohort).
"""
from __future__ import annotations

from numpy import ceil


def request_cost(
    input_tok: int,
    output_tok: int,
    price_in_per_m: float,
    price_out_per_m: float,
    cached_in: int = 0,
    cache_discount: float = 0.10,   # Anthropic cached-read ~0.1x (=-90%)
    batch: bool = False,
    batch_discount: float = 0.50,   # Batch API ~ -50%
) -> float:
    """USD cost of a single request. Cached input billed at cache_discount x price."""
    cached_in = min(max(0, cached_in), input_tok)
    uncached_in = input_tok - cached_in
    cost = (
        (uncached_in / 1e6) * price_in_per_m
        + (cached_in / 1e6) * price_in_per_m * cache_discount
        + (output_tok / 1e6) * price_out_per_m
    )
    if batch:
        cost *= batch_discount
    return cost


def dollars_per_million(total_cost_usd: float, total_tokens: int) -> float:
    """Aggregate unit economics: $ per 1,000,000 tokens served."""
    if total_tokens <= 0:
        return 0.0
    return total_cost_usd / (total_tokens / 1e6)


def discount_stack(
    batch: bool = False,
    cache_hit_frac: float = 0.0,
    batch_discount: float = 0.50,
    cache_discount: float = 0.10,
) -> float:
    """Effective fraction of the naive bill after stacking discounts (input-heavy view).

    Discounts MULTIPLY: cache applies to the cached share of input, batch to the
    whole bill. batch + 100% cache-hit -> 0.5 * 0.1 = 0.05 (~95% off).
    """
    cache_mult = cache_hit_frac * cache_discount + (1.0 - cache_hit_frac)
    batch_mult = batch_discount if batch else 1.0
    return cache_mult * batch_mult


def break_even_utilization(discount_frac: float) -> float:
    """Utilization at which a commitment pays off ~= 1 - discount.

    A 45% reserved discount needs ~55% utilization (~13.2h/day) to beat on-demand.
    """
    return max(0.0, min(1.0, 1.0 - discount_frac))


def recommend_tier(hours_per_day: float, interruptible: bool, reserved_discount: float = 0.45) -> str:
    """Pick a purchasing tier from a workload's duty cycle + interruptibility.

    DOCUMENTED simple policy (instructor extension point — swap in your own):
      - interruptible & not 24/7  -> 'spot'      (checkpoint and ride the discount)
      - duty cycle >= break-even  -> 'reserved'  (steady, high utilization)
      - otherwise                 -> 'on_demand' (spiky / low duty)
    """
    duty = max(0.0, hours_per_day) / 24.0
    be = break_even_utilization(reserved_discount)
    if interruptible and hours_per_day < 24:
        return "spot"
    if duty >= be:
        return "reserved"
    return "on_demand"


def spot_checkpoint_cost(
    job_hours: float,
    spot_hr: float,
    on_demand_hr: float,
    interrupt_rate: float = 0.05,      # per-hour chance (H100 spot ~<5%)
    ckpt_overhead_frac: float = 0.03,  # steady cost of writing checkpoints
    rework_hours_per_interrupt: float = 0.5,
) -> dict:
    """Effective cost of running a checkpointable job on spot vs on-demand.

    Interruptions waste the compute since the last checkpoint (rework); checkpointing
    adds a small steady overhead. Spot still wins for interruptible jobs.
    """
    expected_interrupts = job_hours * interrupt_rate
    rework_hours = expected_interrupts * rework_hours_per_interrupt
    effective_hours = job_hours * (1.0 + ckpt_overhead_frac) + rework_hours
    spot_cost = effective_hours * spot_hr
    on_demand_cost = job_hours * on_demand_hr
    savings_pct = (1.0 - spot_cost / on_demand_cost) * 100.0 if on_demand_cost > 0 else 0.0
    return {
        "spot_effective_hours": round(effective_hours, 2),
        "spot_cost": round(spot_cost, 2),
        "on_demand_cost": round(on_demand_cost, 2),
        "savings_pct": round(savings_pct, 1),
    }


def cache_is_worth_it(
    prompt_tokens: int,
    read_count: int,
    storage_hours: float = 1.0,
    price_full_input_per_m: float = 2.50,   # $2.50 / 1M input tokens
    price_cache_read_per_m: float = 0.25,   # $0.25 / 1M cache read tokens
    price_cache_write_per_m: float = 3.00,  # $3.00 / 1M cache write tokens
    price_storage_per_m_hour: float = 0.00   # Chi phí lưu trữ theo giờ nếu có
) -> dict:
    """
    Tính toán hiệu quả kinh tế của Prompt Caching.
    """
    # Chi phí nếu không dùng Cache (đọc full input R lần)
    cost_without_cache = read_count * (prompt_tokens / 1_000_000) * price_full_input_per_m

    # Chi phí khi dùng Cache (1 lần ghi + R lần đọc + chi phí lưu trữ)
    write_cost = (prompt_tokens / 1_000_000) * price_cache_write_per_m
    read_cost = read_count * (prompt_tokens / 1_000_000) * price_cache_read_per_m
    storage_cost = (prompt_tokens / 1_000_000) * storage_hours * price_storage_per_m_hour

    total_cached_cost = write_cost + read_cost + storage_cost
    net_savings = cost_without_cache - total_cached_cost

    # Điểm hòa vốn tối thiểu về số lần đọc
    savings_per_read = (prompt_tokens / 1_000_000) * (price_full_input_per_m - price_cache_read_per_m)
    breakeven_reads = (write_cost + storage_cost) / savings_per_read if savings_per_read > 0 else float('inf')

    return {
        "is_worth_it": net_savings > 0,
        "net_savings_usd": round(net_savings, 4),
        "cost_without_cache_usd": round(cost_without_cache, 4),
        "cost_with_cache_usd": round(total_cached_cost, 4),
        "breakeven_reads_required": ceil(breakeven_reads),
        "actual_reads": read_count
    }


if __name__ == "__main__":
    import json

    # Kịch bản 1: Chỉ đọc 1 lần (Chưa đạt ngưỡng hòa vốn)
    res_1 = cache_is_worth_it(prompt_tokens=2_400_000, read_count=1)
    res_1["breakeven_reads_required"] = int(res_1["breakeven_reads_required"]) # Convert numpy int to standard int
    print("\n--- [Test Case 1: Read Count = 1] ---")
    print(json.dumps(res_1, indent=2))

    # Kịch bản 2: Đọc 2 lần (Đã vượt ngưỡng hòa vốn & sinh lời)
    res_2 = cache_is_worth_it(prompt_tokens=2_400_000, read_count=2)
    res_2["breakeven_reads_required"] = int(res_2["breakeven_reads_required"])
    print("\n--- [Test Case 2: Read Count = 2] ---")
    print(json.dumps(res_2, indent=2))