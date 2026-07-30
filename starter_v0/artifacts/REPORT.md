# Day 04 Lab Report: Football News VAR

## Team

- Team: Football News VAR (Nhóm A1-1)
- Members: Nguyễn Tuấn Trường (2A202601842 - Lead), Nguyễn Minh Hiếu (2A202601816), Nguyễn Văn Đức (2A202601422), Đào Hải Đăng (2A202601814), Vũ Xuân Đức (2A202601668)
- Provider/model: OpenRouter, `openai/gpt-4o-mini`
- Artifact cuối: `v5+p520f36050b86+tb303857e6606`
- UI: `http://localhost:8501` (Streamlit) & `http://localhost:3000` (Next.js)

## PHẦN A: Giới thiệu agent

### A1. Agent làm được gì

Football News VAR là chatbot bóng đá ưu tiên bằng chứng. Mỗi câu hỏi factual đi qua loop `LLM chọn nguồn -> tool lấy dữ liệu thật -> LLM kiểm tra chéo -> tổng hợp và dịch sang tiếng Việt`, sau đó hiển thị nguồn, mức tin cậy và giới hạn của kết luận.

Sản phẩm tập trung vào tin chuyển nhượng, chấn thương, thông báo đội bóng và độ tin cậy của nguồn. Ngoài phạm vi gồm tỷ số trực tiếp, cá cược, odds, vé, tài khoản riêng tư và kết luận gây tổn hại về cá nhân.

Link dùng thử trên máy demo: `http://localhost:8501`

### A2. Tool agent có

| Tool | Khả năng | Tool mới của nhóm? |
|---|---|---|
| `clarify` | Hỏi một câu khi thiếu input hoặc cần xác nhận | Không |
| `lookup` | Tìm web/news qua Tavily, có topic và timeframe | Không |
| `fetch` | Đọc nội dung một URL qua Firecrawl | Không |
| `timeline` | Lấy bài công khai gần đây của một tài khoản X | Không, đã bổ sung backend fallback |
| `social_search` | Tìm thảo luận công khai theo từ khóa trên X | Không, đã bổ sung backend fallback |
| `instagram_profile` | Lấy follower, engagement, quality và verified công khai | Có |
| `facebook_page_transparency` | Lấy tên Page, verified, admin countries, lịch sử đổi tên và cờ quảng cáo | Có |
| `format` | Định dạng evidence đã có thành digest | Không |
| `send` | Gửi Telegram sau khi có xác nhận rõ ràng | Không, không live-send trong eval |
| `policy` | Tìm chính sách nội bộ | Không |
| `papers` | Tìm paper arXiv | Không |
| `paper_text` | Trích text từ paper arXiv đã chỉ định | Không |

### A3. Câu hỏi mẫu

1. `Tìm tin mới nhất về Liverpool hôm nay.`
2. `Kiểm tra tin chuyển nhượng này giúp tôi.`
3. `Kiểm tra số liệu công khai của tài khoản Instagram @realmadrid.`
4. `Kiểm tra thông tin minh bạch của Facebook Page ID 20531316728.`
5. `Đọc trang này và tóm tắt nguồn chính: https://www.liverpoolfc.com/news`

### A4. Kịch bản demo đã rehearse

| Scenario | Trace cần thấy | Câu chuyện cải thiện | Fallback evidence |
|---|---|---|---|
| Tin Liverpool hôm nay | `lookup(query=Liverpool, topic=news, timeframe=day)` | v0 thêm sai chữ `news`; từ v1 giữ đúng subject | `runs/v0...json`, `runs/v1...json`, transcript turn 3 |
| Thiếu claim rồi bổ sung | `clarify(text)` sau đó `lookup` và supporting social evidence | Không đoán player/club khi input thiếu | transcript turn 1 và 2 |
| Facebook Page identity | `facebook_page_transparency(page_id=20531316728)` | Tool mới trả metadata công khai có guardrail | transcript turn 4 |
| Đăng Telegram | `clarify(response_type=yes_no)`, không gọi `send` | Action boundary được giữ trong demo thật | transcript turn 5 |
| Chat Liverpool end-to-end | `lookup`, 5 evidence item, câu trả lời tiếng Việt | UI hiển thị tiến trình collect, verify, synthesize | transcript UI v4 |

Transcript rehearsal cuối: `transcripts/v4_openrouter_football_demo_20260729T122510500773.transcript.json`. Interaction test qua Streamlit: `transcripts/v4_openrouter_chat_20260729T122845560741.transcript.json`.

## PHẦN B: Chi tiết và bằng chứng

### B1. Version evidence

Mọi base run có `provider_error_cases=0` và `measured_cases=total_cases=20`.

| Version | Artifact thay đổi | Hypothesis | Case accuracy | Routing | Args | Multi-turn | Run |
|---|---|---|---:|---:|---:|---:|---|
| v0 | Baseline | Đo hành vi trước tối ưu | 0.70 | 0.80 | 0.70 | 1.00 | `runs/v0_B_base_openrouter_20260729T111414471467.json` |
| v1 | `system_prompt.md` | Decision policy rõ sẽ chặn input bịa, action chưa xác nhận và giữ subject | 0.80 | 0.95 | 0.80 | 0.8333 | `runs/v1_B_base_openrouter_20260729T112127908704.json` |
| v2 | `tools.yaml` | Tool contract bắt buộc response type và negative routing sẽ giảm lỗi boundary | 0.90 | 0.95 | 0.90 | 0.8333 | `runs/v2_B_base_openrouter_20260729T113305214588.json` |
| v3 | `system_prompt.md` | Thứ tự ưu tiên action và source cancellation sẽ sửa hai lỗi còn lại | 0.90 | 0.95 | 0.90 | 0.8333 | `runs/v3_B_base_openrouter_20260729T113504578561.json` |
| v4 | `system_prompt.md` | Contract collect, verify, synthesize sẽ giữ routing và tạo câu trả lời bóng đá tiếng Việt có nguồn | 0.90 | 0.95 | 0.90 | 0.8333 | `runs/v4_B_base_openrouter_20260729T122342377504.json` |

v3 và v4 đều plateau ở fixed routing metric. v4 cải thiện runtime synthesis, một phần không được fixed eval đo. Kết quả plateau vẫn được giữ nguyên trong version log thay vì chọn lại run thuận lợi. Artifact hash đầy đủ nằm trong từng run JSON và `artifacts/version_log.csv`.

### B2. Failure analysis

| Version/case | Failure type | Actual calls | What failed | Fix hoặc kết luận |
|---|---|---|---|---|
| v0 R03 | `wrong_arg_value` | `lookup` | Query là `AI news` thay vì `AI` | v1 thêm convention giữ nguyên subject; case PASS |
| v0 R08 | `out_of_scope` | `send` | Gọi action tool cho câu hỏi không cần tool | v1 thêm no-tool boundary; case PASS |
| v0 R10 | `missing_info` | `timeline` | Đoán handle thay vì hỏi | v1 cấm bịa handle; chuyển sang `clarify` |
| v0 R11 | `missing_info` | `fetch` | Bịa URL thay vì hỏi | v1 cấm bịa URL; chuyển sang `clarify` |
| v0 R12 | `wrong_boundary` | `send` | Gửi trước khi xác nhận | v1 chuyển sang `clarify`; v2 bắt buộc response type |
| v0 R13 | `wrong_arg_value` | `lookup`, `social_search` | Query/topic của lookup sai | v1 quy định multi-tool và argument mapping; case PASS |
| v1 R10/R11 | `missing_info` | `clarify` | Đúng tool nhưng thiếu `response_type=text` | v2 đưa `response_type` vào required schema; cả hai PASS |
| v1-v4 R12 | `wrong_boundary` | `clarify` | Model hỏi nội dung bằng `text` thay vì xác nhận `yes_no` trong fixed case | Residual base failure; live demo turn 5 lại chọn đúng `yes_no` |
| v1-v4 M06 | `wrong_tool` | `lookup`, `social_search` | Gọi thừa social tool sau source switch | Residual fixed-case failure; 5 group multi-turn case cuối đạt 5/5 |

Manual tool review: v1 M04 routing PASS nhưng Firecrawl trả `ConnectTimeout` cho `https://anthropic.com/news/claude`. Retest thủ công cùng URL sau đó thành công, nên được phân loại là lỗi mạng tạm thời, không phải lỗi key/config hoặc routing. v0, v2, v3, v4 base và group run cuối không có core tool execution error.

### B3. Team eval cases

File `data/eval_group.json` có đúng 10 case: 5 single-turn dùng `query`, 5 multi-turn dùng `turns`.

| Case | Loại | Nội dung kiểm tra | Expected | Final |
|---|---|---|---|---|
| G01 | Single | Liverpool news hôm nay | `lookup`, news/day | PASS |
| G02 | Single | Đọc URL trang tin CLB | `fetch` | PASS |
| G03 | Single | Instagram club profile | `instagram_profile` | PASS |
| G04 | Single | Facebook Page identity | `facebook_page_transparency` | PASS |
| G05 | Single | Claim thiếu subject | `clarify(text)` | PASS |
| G06 | Multi | Giữ Arsenal, đổi timeframe sang hôm nay | `lookup`, day | PASS |
| G07 | Multi | Sửa player Mbappe thành Haaland | `lookup(query=Haaland)` | PASS |
| G08 | Multi | Bỏ web search, chuyển sang URL | Chỉ `fetch` | PASS |
| G09 | Multi | Bổ sung Facebook Page ID ở lượt sau | `facebook_page_transparency` | PASS |
| G10 | Multi | Hủy research rồi hỏi capability | Không tool | PASS |

Run cuối: `runs/v4_B_group_openrouter_20260729T122432496314.json`.

- `total_cases=10`
- `measured_cases=10`
- `provider_error_cases=0`
- `case_accuracy=1.0`
- `tool_routing_accuracy=1.0`
- `argument_accuracy=1.0`
- `multiturn_accuracy=1.0`

Group run đầu chấm cứng `@realmadrid`; model gửi bare handle `realmadrid`, backend vẫn chuẩn hóa và trả đúng profile. Case được sửa để chỉ chấm routing vì cả hai input đều hợp lệ theo tool contract, sau đó chạy lại toàn bộ 10 case.

### B4. Live chat evidence

| Turn | Version | Tool calls | Outcome |
|---|---|---|---|
| 1: claim thiếu dữ kiện | v4 | hỏi trực tiếp để bổ sung | Không đoán claim hoặc player |
| 2: bổ sung claim Arsenal | v4 | `lookup(news/day)` | 5 evidence item, trả lời tiếng Việt có mức tin cậy |
| 3: Liverpool hôm nay | v4 | `lookup(query=Liverpool, news/day)` | 5 evidence item, đúng subject và timeframe |
| 4: Facebook Page ID | v4 | `facebook_page_transparency(20531316728)` | Trình bày metadata tiếng Việt và nguồn Facebook |
| 5: đăng Telegram | v4 | `clarify(response_type=yes_no)` | `waiting_for_user`, không live-send |

Transcript: `transcripts/v4_openrouter_football_demo_20260729T122510500773.transcript.json`. Cả 5 lượt không có provider error hoặc tool execution error. Streamlit interaction test cũng chạy thật một câu Liverpool, gọi `lookup`, thu 5 nguồn và render câu trả lời có mục `Mức tin cậy` mà không có UI exception.

### B5. Tool capability evidence

| Category | Evidence | What worked | Risk / guardrail |
|---|---|---|---|
| Must-have new tool | `tools/instagram_profile/TOOL.md`, `tool.py`, group G03 | RapidAPI trả profile Real Madrid thật, verified và thống kê công khai | Không lộ contact email; follower/verified chỉ là supporting evidence |
| New project tool | `tools/facebook_page_transparency/TOOL.md`, `tool.py`, group G04/G09 | RapidAPI trả Page name, verification, admin country aggregate, rename/ad flags | Chỉ nhận Page ID số; metadata không tự chứng minh claim |
| Core backend fix | `tools/timeline/tool.py`, `tools/social_search/tool.py` | Tavily public-X fallback trả URL X/Twitter khi Twitter RapidAPI backend chưa cấu hình | Luôn ghi `backend` và `fallback_reason`; dữ liệu index có thể trễ |
| Optional built-in | `send` | Confirmation boundary được kiểm tra, không thực hiện live-send | Credentials để unset trong eval; không gửi khi chưa xác nhận |
| Bonus | Không khai báo | Nhóm có 2 tool mới, không nhận bonus yêu cầu hơn 3 tool mới | Không phóng đại phạm vi hoàn thành |

### B6. Reflection

- `system_prompt.md` phù hợp cho decision policy xuyên tool: không bịa input, source correction, no-tool scope, confirmation boundary và cách dùng bằng chứng hỗ trợ.
- `tools.yaml` phù hợp cho hợp đồng cục bộ: khi nào dùng/không dùng từng tool, field bắt buộc, enum và argument convention.
- Grader tự động không đủ để đánh giá execution health. Ví dụ M04 v1 chấm routing PASS dù Firecrawl timeout; ngược lại G03 lần đầu chấm FAIL dù bare handle là input hợp lệ và backend trả dữ liệu đúng.
- Base v4 còn hai case cố định chưa ổn định với `gpt-4o-mini`, trong khi group eval và live transcript đều xác nhận các luồng sản phẩm chính hoạt động. Bước tiếp theo nên thêm canonical conversation-state reducer trước model hoặc đánh giá model khác, thay vì tiếp tục thêm các câu luật gần trùng nhau vào prompt.
- UI dùng chung `run_model_tool_loop` từ `chat.py` và được thiết kế lại theo hướng chat-first. Người dùng thấy câu trả lời và nguồn trước; trạng thái collect/verify/synthesize xuất hiện khi chạy; args, raw result, transcript và artifact version nằm trong chế độ chuyên gia.

## C. Cập nhật v5 — freshness và relevance

Phần này thay thế các kết luận chất lượng v4 ở trên cho artifact hiện tại
`v5+p520f36050b86+tb303857e6606`.

- `lookup` tách subject (`query`) khỏi mục đích tìm kiếm (`intent`), giữ
  `published_date`, lọc kết quả lệch chủ đề và tự thử lại với truy vấn giàu ngữ
  cảnh hơn.
- Runtime chỉ cho phép nới timeframe khi người dùng không nêu cửa sổ thời gian
  rõ ràng. `hôm nay` luôn giữ `day`; câu hỏi trạng thái/hợp đồng không ngày không
  còn bị ép sai xuống 24 giờ.
- Kết quả rỗng hoặc relevance thấp được đánh dấu `inconclusive`, không được dùng
  để kết luận sự kiện không xảy ra.
- `fetch` gửi `maxAge=0` và giữ metadata ngày để tránh dùng nhầm nội dung cache
  cho trang tin thay đổi thường xuyên.
- X/Twitter fallback chỉ giữ URL X thật và luôn công khai rằng đây là dữ liệu
  index có thể trễ, không phải live timeline.
- Runtime và tool schema cùng bảo vệ `clarify(yes_no)` trước external action.

Kết quả kiểm thử cuối:

| Suite | Kết quả | Provider error | Run |
|---|---:|---:|---|
| Base v5 | 20/20 | 0 | `runs/v5_B_base_openrouter_20260729T134241152755.json` |
| Group v5 | 10/10 | 0 | `runs/v5_B_group_openrouter_20260729T134513412901.json` |
| Freshness targeted v5 | 5/5 | 0 | `runs/v5_B_cross_openrouter_20260729T134017834266.json` |
| Unit regression | 9/9 | n/a | `tests/test_freshness.py` |

Live smoke test bao phủ bốn nhóm hợp đồng, tin trong ngày, chấn thương và kết quả
trận. Transcript end-to-end ba case nằm tại
`transcripts/v5_openrouter_freshness_20260729T132822709238.transcript.json`.

### C1. Next.js frontend

- Frontend chính được chuyển từ Streamlit sang Next.js App Router trong `frontend/`.
- FastAPI bridge trong `api.py` giữ session history, gọi trực tiếp `run_model_tool_loop` và ghi transcript JSON như luồng CLI.
- Mỗi câu trả lời hiển thị tool name và số lần gọi; câu trả lời không cần tool được ghi rõ là không sử dụng công cụ.
- Evidence, trạng thái provider error và technical trace được trình bày riêng, technical trace chỉ mở khi bật chế độ chuyên gia.
- API key chỉ được nạp ở Python backend. Next.js gọi đường dẫn proxy `/backend`, không nhúng secret vào client bundle.
- Frontend đã qua ESLint, TypeScript strict và production build của Next.js 16.
