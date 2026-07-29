# Yêu cầu xây dựng Flight Search & Monitoring Agent

## 1. Mục tiêu

Xây dựng Agent hỗ trợ:

* Tra cứu mã sân bay IATA.
* Tìm giá vé một chiều và khứ hồi.
* Tra cứu chuyến bay đến và đi tại sân bay.
* Kiểm tra trạng thái chuyến bay.
* So sánh và gợi ý chuyến bay phù hợp.
* Lưu lịch sử và phân tích biến động giá.
* Theo dõi giá hoặc trạng thái và gửi cảnh báo.

Agent chỉ tìm kiếm, phân tích và theo dõi; không đặt vé hoặc thanh toán.

## 2. Nguồn dữ liệu

Sử dụng:

* **FlightAPI** cho tra cứu mã sân bay và tìm giá vé.
* **AeroDataBox qua RapidAPI** cho trạng thái chuyến bay, bảng chuyến đến/đi và cảnh báo chuyến bay.

Đọc đúng các phần tài liệu liên quan đến:

* Airport/IATA lookup.
* One-way flight price.
* Round-trip flight price.
* Flight status.
* Airport arrivals and departures.
* Flight alert hoặc webhook.

Không cần đọc hoặc triển khai các API ngoài phạm vi trên.

Trước khi viết code, hãy tạo bảng:

```text
Tool nội bộ → Provider → Endpoint → Request fields → Response fields
```

Nếu tài liệu và ví dụ không thống nhất, ghi rõ vấn đề và chọn contract an toàn nhất; không tự đoán.

## 3. Bảo mật cấu hình

Không hardcode hoặc ghi log API key.

Đọc khóa từ:

```env
FLIGHT_API_KEY=
RAPIDAPI_KEY=
RAPIDAPI_HOST=aerodatabox.p.rapidapi.com
```

Tạo `.env.example` nhưng không đưa key thật vào file.

## 4. Dữ liệu tìm kiếm chuẩn hóa

```json
{
  "tripType": "ONE_WAY",
  "origin": "HAN",
  "destination": "SGN",
  "departureDate": "2026-08-15",
  "returnDate": null,
  "cabinClass": "ECONOMY",
  "adults": 1,
  "children": 0,
  "infants": 0,
  "currency": "VND",
  "filters": {
    "maxPrice": 2000000,
    "maxStops": 0,
    "departureTimeFrom": "06:00",
    "departureTimeTo": "12:00",
    "baggageRequired": true
  }
}
```

Quy tắc:

* `returnDate` bắt buộc với chuyến khứ hồi.
* Điểm đi và điểm đến phải là mã IATA đã được xác minh.
* Không tự đoán mã sân bay.
* `maxPrice`, `maxStops`, khoảng giờ và hành lý là bộ lọc nội bộ, trừ khi tài liệu provider xác nhận có tham số tương ứng.
* Không khẳng định có hành lý nếu response không xác nhận.

## 5. Các tool của Agent

### Tool gọi API

```text
search_airports
search_flight_prices
get_flight_status
get_airport_arrivals
get_airport_departures
```

### Tool xử lý nội bộ

```text
compare_flight_offers
analyze_price_history
create_price_watch
create_flight_status_watch
cancel_watch
```

Mỗi tool phải có:

* Mục đích.
* Input schema.
* Output schema chuẩn hóa.
* Validation.
* Timeout.
* Xử lý lỗi.
* Log không chứa dữ liệu bí mật.

## 6. Luồng xử lý Agent

1. Nhận diện ý định người dùng.
2. Trích xuất các trường đã cung cấp.
3. Chỉ hỏi những trường bắt buộc còn thiếu.
4. Tra cứu mã sân bay khi người dùng nhập tên thành phố hoặc sân bay.
5. Gọi đúng provider adapter.
6. Chuẩn hóa response về mô hình nội bộ.
7. Áp dụng bộ lọc.
8. Xếp hạng kết quả.
9. Trả lời kèm nguồn và thời điểm cập nhật.
10. Tạo yêu cầu theo dõi khi người dùng yêu cầu rõ ràng.

LLM không được tự tạo giá vé, trạng thái, giờ bay hoặc mã sân bay.

## 7. Logic gợi ý

Đánh giá dựa trên:

* Tổng giá.
* Tổng thời gian.
* Số điểm dừng.
* Giờ khởi hành và giờ đến.
* Thời gian quá cảnh.
* Hãng hàng không.
* Hành lý nếu được provider xác nhận.

Trả về tối đa ba đề xuất:

1. **Rẻ nhất**
2. **Cân bằng nhất**
3. **Thuận tiện nhất**

Mỗi đề xuất phải nêu lý do và không được lặp lại cùng một hành trình ở nhiều nhóm nếu không cần thiết.

## 8. Theo dõi giá

Lưu:

```text
Route
Departure date
Return date
Cabin class
Passenger count
Current price
Lowest price
Provider
Observed time
Target price
Watch expiration
Last notification
```

Scheduler kiểm tra theo chu kỳ cấu hình.

Chỉ thông báo khi:

* Giá nhỏ hơn hoặc bằng mức mục tiêu.
* Giá giảm vượt ngưỡng phần trăm cấu hình.
* Xuất hiện hành trình tốt hơn rõ rệt.
* Yêu cầu theo dõi hết hạn hoặc gặp lỗi kéo dài.

Không gửi lại cảnh báo nếu dữ liệu không thay đổi đáng kể.

## 9. Theo dõi trạng thái

Hỗ trợ cảnh báo khi:

* Chuyến bay bị hoãn hoặc hủy.
* Độ trễ vượt ngưỡng.
* Thay đổi nhà ga.
* Thay đổi cửa ra máy bay.
* Chuyến bay khởi hành hoặc đến nơi.

Ưu tiên webhook nếu gói AeroDataBox hỗ trợ; nếu không, sử dụng polling có giới hạn.

## 10. Kiến trúc tích hợp

Tạo interface chung:

```text
FlightProvider
├── searchAirports()
├── searchPrices()
├── getFlightStatus()
├── getAirportBoard()
└── createFlightAlert()
```

Implement:

```text
FlightApiAdapter
AeroDataBoxAdapter
```

Không để logic Agent phụ thuộc trực tiếp vào JSON của provider.

## 11. Xử lý lỗi

Phải xử lý:

* Thiếu hoặc sai API key.
* Sai mã IATA.
* Ngày không hợp lệ.
* Không có chuyến bay.
* Timeout.
* Rate limit.
* Provider tạm ngừng.
* Response thiếu trường.
* Hai nguồn trả về dữ liệu khác nhau.

Không trả dữ liệu cũ mà không ghi rõ thời điểm lấy dữ liệu.

## 12. Đầu ra cần tạo

Tạo đầy đủ:

* Cấu trúc source code.
* Agent orchestration.
* Tool definitions và schemas.
* Provider adapters.
* Models chuẩn hóa.
* Database models cho lịch sử và yêu cầu theo dõi.
* Scheduler hoặc webhook handler.
* REST API để chat, tìm kiếm và quản lý watch.
* Unit test cho logic xếp hạng.
* Mock test cho external API.
* File `.env.example`.
* README hướng dẫn cài đặt và chạy thử.
* Ví dụ request và response.

Không triển khai chức năng đặt vé hoặc thanh toán.

## 13. Tiêu chí nghiệm thu

Hệ thống phải chạy được các kịch bản:

1. Tra cứu “Nội Bài” và trả về `HAN`.
2. Tìm vé một chiều `HAN → SGN`.
3. Tìm vé khứ hồi.
4. Lọc chuyến dưới ngân sách.
5. Trả về ba nhóm gợi ý.
6. Tra cứu trạng thái bằng số hiệu và ngày.
7. Xem chuyến đến hoặc đi tại một sân bay.
8. Tạo và hủy theo dõi giá.
9. Không gửi cảnh báo trùng lặp.
10. External API được mock trong test.
11. Không có API key thật trong repository.


Key rapid API: 5549b40544mshee6e22a6f770b01p102c9ajsnd5dbbee3b2c4
Key Flight API: 6a69abe2555eba909d5e7f2e
https://www.flightapi.io/documentation/
https://aerodatabox.p.rapidapi.com/