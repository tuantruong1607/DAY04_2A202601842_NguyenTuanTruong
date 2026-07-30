# Football News VAR

Football News VAR là chatbot thông tin bóng đá bằng tiếng Việt. Chatbot tìm dữ liệu công khai bằng tool thật, kiểm tra chất lượng nguồn, tổng hợp lại bằng tiếng Việt và giữ liên kết evidence bên cạnh từng câu trả lời.

## Agent loop

```text
User question
    |
    v
LLM hiểu intent và chọn tool
    |
    v
Tool tìm dữ liệu thật
    |
    v
LLM kiểm tra lỗi, nguồn và mâu thuẫn
    |
    +---- thiếu bằng chứng ----> gọi tool vòng tiếp theo
    |
    v
Tổng hợp tiếng Việt + mức tin cậy + nguồn
```

Next.js, Streamlit legacy và CLI đều tái sử dụng `run_model_tool_loop` trong `chat.py`. UI không có một agent loop riêng. `api.py` chỉ là cầu nối HTTP, không thay đổi quyết định tool-calling của agent.

## Chạy local

Từ thư mục `starter_v0`, mở hai cửa sổ PowerShell.

Backend:

```powershell
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Mở `http://localhost:3000`. Next.js proxy các request `/backend/*` sang FastAPI tại `http://127.0.0.1:8000/api/*`, nên API key không đi vào JavaScript phía trình duyệt.

Nếu cổng 3000 đã được một dịch vụ khác sử dụng, chạy `npm.cmd run dev -- --port 3001` và mở `http://localhost:3001`.

Kiểm tra trước khi demo:

```powershell
cd frontend
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run build
```

Giao diện Streamlit cũ vẫn có thể chạy tại cổng 8501 để đối chiếu, nhưng Next.js là frontend chính.

## Cách dùng

- Hỏi tin mới: `Tìm tin mới nhất về Liverpool hôm nay.`
- Kiểm tra claim: cung cấp player, CLB, nội dung claim và thời gian nếu có.
- Đọc nguồn: dán URL trực tiếp.
- Kiểm tra Instagram: cung cấp URL hoặc handle.
- Kiểm tra Facebook Page: cung cấp Page ID dạng số.

Trong giao diện, mở `Nguồn đã kiểm tra` để xem evidence. Mỗi output luôn có phần `Công cụ đã sử dụng`; nếu agent trả lời trực tiếp, UI ghi rõ `Không sử dụng công cụ`. Bật `Chế độ chuyên gia` nếu cần xem tool name, arguments và raw result.

## Chất lượng hiện tại

- Base eval v5: `20/20`, không provider error.
- Group eval bóng đá v5: `10/10`.
- Freshness regression v5: `5/5`; unit regression: `8/8`.
- Live lookup smoke test đã qua các nhóm hợp đồng, tin hôm nay, chấn thương và kết quả trận; evidence giữ ngày xuất bản.

Run và transcript chi tiết nằm trong `runs/` và `transcripts/`. Báo cáo đầy đủ nằm tại `artifacts/REPORT.md`.

## Bảo mật

- `.env` được Git ignore.
- Không hiển thị API key trong UI, transcript hoặc error message.
- Social/profile metadata chỉ là bằng chứng hỗ trợ.
- `send` luôn yêu cầu xác nhận trước khi thực hiện hành động bên ngoài.
