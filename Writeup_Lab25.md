# BÀI BÁO CÁO THU HOẠCH: GPU FINOPS OPTIMIZATION — LAB 25

**Họ và tên:** Nguyễn Thị Minh Tiến
**Mã sinh viên:** 2A202602997
**Tên Repository:** K4-L3-DAY25-NguyenThiMinhTien-2A202602997-GpuFinOps
**Dự án:** NimbusAI — GPU Cost Optimization

---

## 1. Baseline vs. Optimized

| Chỉ số / Hạng mục | Baseline (Ban đầu) | Optimized (Tối ưu) | Mức giảm / Tiết kiệm |
|---|---|---|---|
| **Tổng chi phí GPU** | **$27,133 / tháng** | **$14,626 / tháng** | **$12,507 / tháng (46.1%)** |
| **Đơn giá Inference** | **$6.488 / 1M token** | **$1.126 / 1M token** | **Giảm 82.6%** |
| **Chi phí Inference / ngày** | $48.87 / ngày | $8.48 / ngày | Giảm $40.39 / ngày |
| **Chi phí Purchasing / tháng** | $25,667 / tháng | $15,627 / tháng | Giảm $10,040 / tháng (39.1%) |

**Tổng kết:** Sau khi áp dụng đầy đủ 4 đòn bẩy FinOps, NimbusAI cắt giảm thành công **46.1% tổng chi phí hàng tháng** và giảm đơn giá phục vụ **82.6% trên mỗi triệu token** (dựa trên mẫu 2,400 request / 7,533,027 token).

---

## 2. Phân Tích Chi Tiết Từng Đòn Bẩy Tiết Kiệm

Tổng chi phí tiết kiệm được **$12,507 / tháng** được phân bổ cụ thể qua các đòn bẩy:

1. **Purchasing Strategy (Đóng góp lớn nhất — $10,040 / tháng):**
   * **Lý do đóng góp nhiều nhất:** Hoạt động huấn luyện (training/finetune) và phục vụ inference chiếm tỷ trọng chi phí GPU cố định cao nhất.
   * **Giải pháp:**
     - Chuyển các job training có cờ `interruptible=1` (`job-train-llm`, `job-train-embed`, `job-finetune`) sang **Spot Instance** giúp cắt giảm 40–60% giá giờ GPU.
     - Chuyển các job inference 24/7 (`job-infer-chat`, `job-infer-rag`, `job-infer-search`) sang **Reserved Instance 3 năm** do duty cycle vượt mốc hòa vốn (55%).

2. **Inference Optimization (Cascade + Caching + Batch — $1,212 / tháng):**
   * **Giải pháp:**
     - Định tuyến Cascade Routing đưa các câu hỏi đơn giản về model nhỏ rẻ hơn ~15×.
     - Áp dụng Prompt Caching (giảm 90% chi phí input) và Batch API (giảm 50% chi phí request offline).
     - Kết hợp cả Batch + 100% Cache Hit giúp tạo ra **Discount Stack hiệu dụng lên đến 95%** (chỉ trả 5% so với giá gốc).

3. **Right-size Util-Lies ($655 / tháng):**
   * **Giải pháp:** Hạ cấp các GPU bị "Util Lie" (nghẽn băng thông/memory-bound) về dòng GPU đúng quy mô tài nguyên, tránh lãng phí năng lượng GPU cao cấp.

4. **Kill Idle GPUs ($600 / tháng):**
   * **Giải pháp:** Tắt bỏ tài nguyên chạy vô ích. Phát hiện `gpu-h100-5` bị bỏ trống 8 giờ/ngày, loại bỏ lãng phí $20.00/ngày tương đương $600/tháng.

---

## 3. GPU-Util Lie & Tác Động Tài Chính

* **GPU bị gắn cờ Lie (`util >= 90%` nhưng `MFU < 30%`):**
  - `gpu-h100-4`: `GPU-Util = 98.2%`, nhưng `MFU = 0.194` (19.4%).
  - `gpu-a10g-1`: `GPU-Util = 96.9%`, nhưng `MFU = 0.268` (26.8%).
* **Nguyên nhân kỹ thuật:** Chỉ số `GPU-Util` từ `nvidia-smi` chỉ đo tỷ lệ thời gian GPU đang có kernel hoạt động, không đo lượng tính toán FLOPs thực sự sinh ra. Trong giai đoạn decode của LLM, hệ thống bị nghẽn băng thông bộ nhớ (memory-bound/stall), GPU bận "chờ dữ liệu" nên báo Util ~98% dù hiệu suất tính toán thực tế (MFU) chỉ đạt dưới 20%.
* **Tác động tài chính:** Dẫn đến việc ngộ nhận GPU đang quá tải để yêu cầu cấp thêm ngân sách mua mới, gây lãng phí hàng nghìn USD hàng tháng cho tài nguyên không được khai thác hiệu quả.

---

## 4. Các Phần Mở Rộng (Your Turn Extensions)

### Extension 1: Dynamic Context Pruning (`ext_context_pruning.py`)
* **Mô tả:** Xây dựng pipeline cắt tỉa lịch sử hội thoại tự động dựa trên ngưỡng token (`max_tokens`), giữ lại System Prompt và các câu thoại gần nhất.
* **Kết quả đo lường:** Cắt giảm số lượng message từ **4 xuống 2 items** (giảm 50% payload token gửi đi API mà vẫn đảm bảo giữ ngữ cảnh chính).

### Extension 2: Spot Interruption & Checkpoint Simulator (`ext_spot_sim.py`)
* **Mô tả:** Giả lập xác suất bị thu hồi node Spot (Interrupt Rate ~5%/giờ) và đánh giá chi phí thời gian do mất việc (`rework_hours`) dựa trên tần suất ghi Checkpoint.
* **Kết quả đo lường (Job 24 giờ):**
  * Số lần bị ngắt node (Interruptions): **1 lần**.
  * Thời gian tính toán bị lãng phí (Rework lost): **0.72 giờ**.
  * Tổng thời gian chạy thực tế (Effective hours): **24.72 giờ** (chỉ tăng 3% thời gian nhưng giảm tới 50–60% chi phí GPU so với On-Demand).

### Extension 3: Ngưỡng Hòa Vốn Caching (`cache_is_worth_it`)
* **Công thức hòa vốn:** $\text{Breakeven Reads } (R_{\text{min}}) = \left\lceil \frac{\text{Price}_{\text{write}}}{\text{Price}_{\text{full}} - \text{Price}_{\text{read}}} \right\rceil$
* **Kết quả đo lường thực tế:**
  * **1 lượt đọc (`read_count = 1`):** Chi phí $7.80 vs $6.00 $\rightarrow$ **Lỗ -$1.80** (`is_worth_it: false`).
  * **2 lượt đọc (`read_count = 2`):** Chi phí $8.40 vs $12.00 $\rightarrow$ **Lời +$3.60** (`is_worth_it: true`, tiết kiệm 30%).
* **Kết luận:** Prompt Caching chỉ phát huy hiệu quả kinh tế khi đoạn context được tái sử dụng **từ 2 lần trở lên** (`breakeven_reads_required = 2`).

### Extension 5: Điều Phối Nhận Thức Carbon (`ext_carbon_aware.py`)
* **Cơ chế:** Tự động điều phối các tác vụ batch offline từ vùng phát thải cao (`us-central1`: 385 gCO2e/kWh) sang vùng năng lượng xanh (`europe-north1`: 28 gCO2e/kWh).
* **Kết quả:** Tác vụ `job_eval_batch_102` cắt giảm **92.73%** lượng phát thải CO₂.

---

## 5. Khuyến Nghị Cho NimbusAI (Top 3 Action Items)

| Ưu tiên | Hành động Chiến lược | Tác động Chi phí & Vận hành | Độ phức tạp |
| :--- | :--- | :--- | :--- |
| **P0 (Ngay)** | Bật **Prompt Caching** ($R \ge 2$) & **Cascade Routing** tại API Gateway | Cắt giảm **35% - 45%** chi phí API Inference; giảm 30% Latency | Thấp |
| **P1 (30 ngày)** | Chuyển Training sang **Spot Instance** + Định tuyến Carbon cho Batch Jobs | Tiết kiệm **$10,040/tháng** (39.1%); giảm **92.73%** phát thải CO₂ | Trung bình |
| **P2 (60 ngày)** | Đo lường hiệu suất theo **MFU** (thay vì GPU-Util) & Triển khai **Chargeback** | Loại bỏ "GPU-Util Lie"; minh bạch hóa chi phí theo Tag (đạt 92%) | Trung bình - Cao |