# Phase 3: Schema entity type HSCC (YAML)

## Context
* LightRAG nạp profile từ `${PROMPT_DIR:-./prompts}/entity_type/<file>.yml`. Chạy từ repo root → `prompts/entity_type/hscc_vi.yml`. Format mẫu: `prompts/samples/entity_type_prompt.sample.yml` trong repo LightRAG. JSON mode bắt buộc có `entity_extraction_json_examples`.
* Entity JSON: `{name, type, description}`. Relationship JSON: `{source, target, keywords, description}`. Quan hệ LightRAG không có kiểu → ép loại quan hệ vào `keywords` (từ đầu tiên).
* Report gốc đòn bẩy 1 và 3: schema đóng 10 loại, 1 đến 2 ví dụ tiếng Việt.

## Overview
Priority P1. Viết `prompts/entity_type/hscc_vi.yml`: 10 loại thực thể ASCII snake_case (ổn định cho validator/stats), mô tả tiếng Việt, 1 ví dụ JSON lấy từ bài Suy hô hấp cấp.

## Steps
1. `entity_types_guidance` (tiếng Việt), kết thúc bằng "Không có loại phù hợp thì dùng `khac`":
   | type | nghĩa | ví dụ |
   |---|---|---|
   | `benh` | bệnh, hội chứng, tình trạng | suy hô hấp cấp, ARDS, sốc nhiễm khuẩn |
   | `trieu_chung` | triệu chứng, dấu hiệu lâm sàng | tím môi, thở nhanh, co kéo cơ hô hấp |
   | `xet_nghiem` | xét nghiệm, chẩn đoán hình ảnh, thang điểm | khí máu động mạch, X quang phổi, SOFA |
   | `thuoc` | thuốc, dịch truyền | noradrenalin, heparin, NaCl 0,9% |
   | `thu_thuat` | thủ thuật, kỹ thuật, chế độ máy | thở máy, lọc máu liên tục, PEEP |
   | `nguyen_nhan` | nguyên nhân, tác nhân | cúm A H1N1, viêm phổi, ngộ độc |
   | `yeu_to_nguy_co` | yếu tố nguy cơ, bệnh nền | COPD, tuổi cao, suy giảm miễn dịch |
   | `bien_chung` | biến chứng, hậu quả | tràn khí màng phổi, suy đa tạng |
   | `chi_so` | chỉ số, ngưỡng, giá trị | PaO2/FiO2 < 200, SpO2 < 90% |
   | `doi_tuong` | nhóm người bệnh, điều kiện | người bệnh thở máy, phụ nữ có thai |
2. Thêm vào guidance: "Tên thực thể phải là cụm từ xuất hiện nguyên văn trong văn bản. Giữ tiếng Việt, không dịch." (khớp validator phase 4).
3. Quy ước quan hệ trong guidance: `keywords` bắt đầu bằng 1 trong: `dieu_tri`, `trieu_chung_cua`, `chan_doan_bang`, `nguyen_nhan_cua`, `bien_chung_cua`, `yeu_to_nguy_co_cua`, `chong_chi_dinh`, `nguong_cua`, `phong_ngua`; tiếp theo là từ khoá tự do. Ví dụ `"dieu_tri, thở máy xâm nhập, ARDS nặng"`.
4. `entity_extraction_json_examples`: 1 khuôn placeholder tiếng Việt (mã loại, mã quan hệ), không dùng ví dụ y khoa thật: 1.5.7 đặt mục này dưới "Output Format Template ... never source text", SLM dễ chép ARDS/PEEP sang chunk khác, prune theo nút không bắt được. Pilot thưa (token out/chunk < 400, prefix < 60%) thì thử ví dụ ARDS Berlin (hstc 04 ĐẠI CƯƠNG, xem git history).
5. Không viết `entity_extraction_examples` (text mode không dùng). Giữ file < 120 dòng để prompt hệ thống không phình (report: prompt gốc đã 1.501 token).
6. Kiểm YAML: `pixi run python -c "import yaml;d=yaml.safe_load(open('prompts/entity_type/hscc_vi.yml'));print(d.keys())"`.

## Files
* create `/home/k1en/kg-textbooks/prompts/entity_type/hscc_vi.yml`

## Acceptance
* YAML load được, có 2 key `entity_types_guidance`, `entity_extraction_json_examples`.
* Ví dụ JSON parse được bằng `json.loads` sau khi lấy chuỗi từ YAML.
* 10 loại + `khac`, 10 mã quan hệ (thêm `phan_biet_voi`).

## Commit
```
git add prompts && git commit -m "feat: HSCC Vietnamese entity type profile for LightRAG"
```

## Risks
* SLM bỏ qua quy ước keywords → stats phase 4 đếm tỉ lệ quan hệ có prefix hợp lệ; < 60% thì thêm ví dụ thứ 2 thay vì đổi kiến trúc.
* Loại ASCII làm WebUI hiển thị `trieu_chung` thay vì "Triệu chứng". Chấp nhận, đổi sau chỉ cần sửa YAML + rebuild.
