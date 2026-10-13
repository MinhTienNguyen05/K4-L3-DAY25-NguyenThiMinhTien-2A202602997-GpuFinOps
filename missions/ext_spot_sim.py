import random

def simulate_spot_job(job_hours: float, interrupt_rate_per_hr: float = 0.05, ckpt_interval_hrs: float = 1.0):
    total_rework_hours = 0.0
    interruptions = 0
    current_time = 0.0

    while current_time < job_hours:
        # Giả lập xác suất bị ngắt node
        if random.random() < interrupt_rate_per_hr:
            interruptions += 1
            # Mất khoảng thời gian từ checkpoint gần nhất đến thời điểm bị ngắt
            lost_work = random.uniform(0, ckpt_interval_hrs)
            total_rework_hours += lost_work
        current_time += 1.0

    return {
        "job_hours": job_hours,
        "interruptions": interruptions,
        "rework_hours_lost": round(total_rework_hours, 2),
        "effective_hours": round(job_hours + total_rework_hours, 2)
    }

if __name__ == "__main__":
    print(simulate_spot_job(job_hours=24.0))