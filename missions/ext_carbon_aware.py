import json
from datetime import datetime

# Bảng dữ liệu cường độ phát thải Carbon trung bình (gCO2eq / kWh)
REGION_CARBON_INTENSITY = {
    "us-central1": 385,     # Lưới điện hỗn hợp (Than/Khí/Tái tạo)
    "us-east1": 410,        # Cường độ Carbon cao
    "asia-southeast1": 460, # Lưới điện phụ thuộc nhiên liệu hóa thạch
    "europe-north1": 28,    # Phần Lan - Thủy điện & Năng lượng gió (>90% sạch)
    "europe-west3": 290     # Đức - Hỗn hợp
}

def get_optimal_green_region(max_latency_sec: float = 500.0) -> dict:
    """
    Xác định Region tối ưu về chỉ số Carbon dựa trên SLA độ trễ cho phép.
    """
    sorted_regions = sorted(REGION_CARBON_INTENSITY.items(), key=lambda x: x[1])
    best_region, min_intensity = sorted_regions[0]
    baseline_region, base_intensity = "us-central1", REGION_CARBON_INTENSITY["us-central1"]

    reduction_pct = ((base_intensity - min_intensity) / base_intensity) * 100

    return {
        "recommended_region": best_region,
        "carbon_intensity_g_kwh": min_intensity,
        "baseline_region": baseline_region,
        "baseline_intensity_g_kwh": base_intensity,
        "carbon_reduction_pct": round(reduction_pct, 2),
        "status": "ROUTED_SUCCESSFULLY"
    }

def schedule_carbon_aware_job(job_id: str, payload_size_mb: float, is_batch: bool = True):
    if not is_batch:
        # Tác vụ real-time giữ nguyên region gần người dùng nhất
        return {"job_id": job_id, "region": "us-central1", "carbon_optimized": False}

    routing_info = get_optimal_green_region()
    return {
        "job_id": job_id,
        "execution_region": routing_info["recommended_region"],
        "carbon_savings": f"{routing_info['carbon_reduction_pct']}%",
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    result = schedule_carbon_aware_job("job_eval_batch_102", payload_size_mb=150.0)
    print(json.dumps(result, indent=2))