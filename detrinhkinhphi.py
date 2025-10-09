import streamlit as st
import pandas as pd
import io
import base64
import warnings

st.set_page_config(page_title="Phiếu đề nghị thanh toán", layout="wide")

# ===== Hàm rerun an toàn =====
def safe_rerun():
    """Sử dụng st.rerun() để làm mới ứng dụng một cách an toàn."""
    st.rerun()

# ===== Hàm định dạng tiền tệ =====
def format_currency(value):
    """Định dạng giá trị số thành chuỗi tiền tệ (ví dụ: 1000000 -> 1,000,000)."""
    try:
        value = float(str(value).replace(",", "").strip())
        return f"{value:,.0f}"
    except:
        return value

# ===== Khởi tạo session state =====
if "table1" not in st.session_state:
    st.session_state.table1 = []
if "table2" not in st.session_state:
    st.session_state.table2 = []
if "uploaded_images" not in st.session_state:
    st.session_state.uploaded_images = []

st.title("📄 PHIẾU ĐỀ NGHỊ THANH TOÁN")

# ============================================================
# THÔNG TIN DỰ ÁN
# ============================================================
st.markdown("### 🏗️ Thông tin dự án")
col1, col2, col3, col4 = st.columns(4)
with col1:
    ma_du_an = st.text_input("Mã dự án")
with col2:
    ten_du_an = st.text_input("Tên dự án")
with col3:
    ngay_de_xuat = st.date_input("Ngày đề xuất")
with col4:
    stk_nhan = st.text_input("Số tài khoản nhận tiền")

# ============================================================
# BẢNG 1: Đề nghị thanh toán chi tiết
# ============================================================
st.markdown("### Bảng 🧾1: Đề nghị thanh toán chi tiết")

col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 2])
with col1:
    mota = st.text_input("Mô tả")
with col2:
    donvi = st.text_input("Đơn vị")
with col3:
    soluong = st.number_input("Số lượng", min_value=0.0, step=1.0)
with col4:
    dongia_raw = st.text_input("Đơn giá", key="dongia_raw")
    dongia_formatted = format_currency(dongia_raw)
    st.caption(f"💰 {dongia_formatted if dongia_formatted else ''}")
with col5:
    ghichu1 = st.text_input("Ghi chú")

if st.button("➕ Thêm dòng vào bảng 1", key="add_row_1"):
    try:
        dongia_value = float(str(dongia_raw).replace(",", ""))
        total = dongia_value * soluong
        st.session_state.table1.append({
            "Mô tả": mota,
            "Đơn vị": donvi,
            "Số lượng": soluong,
            "Đơn giá": format_currency(dongia_raw),
            "Tổng": format_currency(total),
            "Ghi chú": ghichu1
        })
        safe_rerun()
    except ValueError:
        st.warning("⚠️ Vui lòng nhập đơn giá hợp lệ (chỉ số).")

if st.session_state.table1:
    st.markdown("#### 📋 Danh sách chi tiết thanh toán")
    
    # Hiển thị tiêu đề cột
    header_cols = st.columns([0.5, 2, 1, 1, 1, 2, 0.3])
    headers = ["Stt", "Mô tả", "Đơn vị", "Số lượng", "Đơn giá", "Tổng", ""]
    for i, header in enumerate(headers):
        header_cols[i].markdown(f"**{header}**")

    # Hiển thị dữ liệu
    for i, row in enumerate(st.session_state.table1):
        cols = st.columns([0.5, 2, 1, 1, 1, 2, 0.3])
        cols[0].write(i + 1)
        cols[1].write(row["Mô tả"])
        cols[2].write(row["Đơn vị"])
        cols[3].write(row["Số lượng"])
        cols[4].write(row["Đơn giá"])
        cols[5].write(row["Tổng"])
        if cols[6].button("❌", key=f"del1_{i}"):
            st.session_state.table1.pop(i)
            safe_rerun()

    # Tính tổng cộng
    total_sum = sum(float(str(r["Tổng"]).replace(",", "")) for r in st.session_state.table1 if r.get("Tổng"))

    st.markdown(f"**Tổng cộng:** 💰 {format_currency(total_sum)}")

# ============================================================
# BẢNG 2: Theo dõi thanh toán
# ============================================================
st.markdown("### Bảng 💰2: Theo dõi thanh toán")

col1, col2, col3, col4, col5 = st.columns([1.5, 1.5, 1.5, 1.5, 2])
with col1:
    goi = st.text_input("Gói")
with col2:
    dutoan_raw = st.text_input("Dự toán (nhập số)", key="dutoan_raw")
    st.caption(f"💰 {format_currency(dutoan_raw) if dutoan_raw else ''}")
with col3:
    dachi_raw = st.text_input("Đã chi (nhập số)", key="dachi_raw")
    st.caption(f"💰 {format_currency(dachi_raw) if dachi_raw else ''}")
with col4:
    dexuat_raw = st.text_input("Đề xuất chi tuần này (nhập số)", key="dexuat_raw")
    st.caption(f"💰 {format_currency(dexuat_raw) if dexuat_raw else ''}")
with col5:
    ghichu2 = st.text_input("Ghi chú (bảng 2)")

if st.button("➕ Thêm dòng vào bảng 2", key="add_row_2"):
    try:
        dutoan_value = float(str(dutoan_raw).replace(",", ""))
        dachi_value = float(str(dachi_raw).replace(",", ""))
        dexuat_value = float(str(dexuat_raw).replace(",", ""))
        
        # TÍNH TOÁN CỘT "CÒN LẠI"
        con_lai_value = dutoan_value - dachi_value - dexuat_value
        
        st.session_state.table2.append({
            "Gói": goi,
            "Dự toán": format_currency(dutoan_raw),
            "Đã chi": format_currency(dachi_raw),
            "Đề xuất chi tuần này": format_currency(dexuat_raw),
            "Còn lại": format_currency(con_lai_value),
            "Ghi chú": ghichu2
        })
        safe_rerun()
    except ValueError:
        st.warning("⚠️ Vui lòng nhập đúng định dạng số tiền cho Dự toán/Đã chi/Đề xuất chi.")

if st.session_state.table2:
    st.markdown("#### 📋 Danh sách theo dõi thanh toán")
    
    # Hiển thị tiêu đề cột
    header_cols = st.columns([0.4, 1.3, 1.3, 1.3, 1.3, 1.3, 2.5, 0.3])
    headers = ["Stt", "Gói", "Dự toán", "Đã chi", "Đề xuất chi tuần này", "Còn lại", "Ghi chú", ""]
    for i, header in enumerate(headers):
        header_cols[i].markdown(f"**{header}**")
        
    # Hiển thị dữ liệu
    for i, row in enumerate(st.session_state.table2):
        cols = st.columns([0.4, 1.3, 1.3, 1.3, 1.3, 1.3, 2.5, 0.3])
        cols[0].write(i + 1)
        cols[1].write(row["Gói"])
        cols[2].write(row["Dự toán"])
        cols[3].write(row["Đã chi"])
        cols[4].write(row["Đề xuất chi tuần này"])
        cols[5].write(row["Còn lại"])
        cols[6].write(row["Ghi chú"])
        if cols[7].button("❌", key=f"del2_{i}"):
            st.session_state.table2.pop(i)
            safe_rerun()

# ============================================================
# PHẦN PHÊ DUYỆT
# ============================================================
st.markdown("### ✍️ Phần phê duyệt")

col1, col2, col3 = st.columns(3)
with col1:
    nguoi_lap = st.text_input("Người đề nghị (CTY/DA)")
    nguoi_kiemtra1 = st.text_input("Người kiểm (CTY/DA)")
with col2:
    nguoi_duyet1 = st.text_input("Người duyệt (CTY/DA)")
    nguoi_kiemtra2 = st.text_input("Người kiểm (HO)")
with col3:
    ke_toan = st.text_input("Kế toán trưởng (HO)")
    giam_doc = st.text_input("Giám đốc phê duyệt (HO)")

# ============================================================
# UPLOAD HÌNH ẢNH (ĐÃ DI CHUYỂN RA SAU PHÊ DUYỆT)
# ============================================================
st.markdown("### 🖼️ Tải lên & Cập nhật Hình ảnh")
uploaded_files = st.file_uploader(
    "Chọn các hình ảnh (PNG, JPG, JPEG, GIF) để đính kèm vào báo cáo.",
    type=["png", "jpg", "jpeg", "gif"],
    accept_multiple_files=True
)

if uploaded_files:
    if st.button("⬆️ Cập nhật hình ảnh đã chọn", key="update_images_btn"):
        st.session_state.uploaded_images = [] # Xóa các ảnh cũ
        for uploaded_file in uploaded_files:
            # Đọc nội dung file
            bytes_data = uploaded_file.read()
            # Mã hóa base64 để nhúng vào HTML
            base64_encoded_image = base64.b64encode(bytes_data).decode("utf-8")
            # Lưu vào session state
            st.session_state.uploaded_images.append({
                "name": uploaded_file.name,
                "data": base64_encoded_image,
                "type": uploaded_file.type
            })
        st.success(f"Đã tải lên {len(st.session_state.uploaded_images)} hình ảnh.")
        safe_rerun()

if st.session_state.uploaded_images:
    st.markdown("#### Hình ảnh đã tải lên:")
    cols_img = st.columns(len(st.session_state.uploaded_images) if len(st.session_state.uploaded_images) <= 5 else 5)
    for i, img_data in enumerate(st.session_state.uploaded_images):
        if i < 5:
            with cols_img[i]:
                st.image(f"data:{img_data['type']};base64,{img_data['data']}", caption=img_data['name'], width=150)
    if st.button("🗑️ Xóa tất cả hình ảnh đã tải lên", key="clear_images_btn"):
        st.session_state.uploaded_images = []
        safe_rerun()

# ============================================================
# XUẤT HTML + XEM TRƯỚC + XUẤT PDF
# ============================================================
st.markdown("### 📤 Xuất tài liệu & Xem trước")

def generate_html():
    """Tạo chuỗi HTML hoàn chỉnh cho phiếu đề nghị thanh toán với CSS được tối ưu hóa cho in ấn."""
    
    # Bảng 1
    df1 = pd.DataFrame(st.session_state.table1)
    if not df1.empty:
        df1.insert(0, 'Stt', range(1, 1 + len(df1)))
        columns_order_1 = ["Stt", "Mô tả", "Đơn vị", "Số lượng", "Đơn giá", "Tổng", "Ghi chú"]
        df1_html = df1[columns_order_1].to_html(index=False)
    else:
        df1_html = "<p><i>(Chưa có dữ liệu chi tiết thanh toán)</i></p>"

    # Bảng 2
    df2 = pd.DataFrame(st.session_state.table2)
    if not df2.empty:
        df2.insert(0, 'Stt', range(1, 1 + len(df2)))
        columns_order_2 = ["Stt", "Gói", "Dự toán", "Đã chi", "Đề xuất chi tuần này", "Còn lại", "Ghi chú"]
        df2_html = df2[columns_order_2].to_html(index=False)
    else:
        df2_html = "<p><i>(Chưa có dữ liệu theo dõi thanh toán)</i></p>"
    
    # Tạo phần HTML cho hình ảnh
    images_html = ""
    if st.session_state.uploaded_images:
        images_html += "<h3>3. Hình ảnh đính kèm</h3>"
        images_html += "<div class='image-gallery'>"
        for img_data in st.session_state.uploaded_images:
            images_html += f"""
            <div class='image-item'>
                <img src='data:{img_data['type']};base64,{img_data['data']}' alt='{img_data['name']}' style='max-width: 100%; height: auto; display: block; margin: 5px auto;'>
                <p style='text-align: center; font-size: 10px; margin: 2px 0;'>{img_data['name']}</p>
            </div>
            """
        images_html += "</div>"
    
    # Tính Tổng cộng
    total_sum = sum(float(str(r["Tổng"]).replace(",", "")) for r in st.session_state.table1 if r.get("Tổng"))
    total_sum_formatted = format_currency(total_sum)
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Phiếu Đề Nghị Thanh Toán</title>
        <style>
        /* CSS cho in ấn (PDF) */
        @page {{ size: A4 landscape; margin: 10mm; }} 
        body {{
            font-family: DejaVu Sans, Arial, sans-serif;
            font-size: 12px;
            margin: 0;
            padding: 0;
        }}
        h2 {{ text-align: center; margin: 10px 0 15px 0; font-size: 18px; }}
        h3 {{ text-align: left; margin: 15px 0 8px 0; font-size: 14px; }}

        /* Thông tin Header */
        .header-info {{ display: grid; grid-template-columns: 1fr 1fr; gap: 5px; margin-bottom: 10px; font-size: 12px; }}

        /* Bảng Dữ Liệu */
        table {{ border-collapse: collapse; width: 100%; margin-top: 5px; }}
        th, td {{
            border: 1px solid #000;
            padding: 4px;
            text-align: center;
            font-size: 10px;
            line-height: 1.2;
        }}
        th {{ background-color: #e0e0e0; font-weight: bold; }}
        /* Căn chỉnh cột */
        td:nth-child(2), th:nth-child(2) {{ text-align: left; }} 
        td:nth-child(1), th:nth-child(1) {{ text-align: center; }} 

        .total-row {{ margin-top: 8px; font-weight: bold; font-size: 12px; text-align: right; padding-right: 5px; }}

        /* Bảng Chữ Ký */
        .signature-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 25px;
            font-size: 10px;
            page-break-before: auto;
        }}
        .signature-table th, .signature-table td {{ border: 1px solid #000; text-align: center; padding: 5px 3px; line-height: 1.1; }}
        .signature-table th {{ vertical-align: top; background-color: #f2f2f2; font-weight: bold;}}
        .signature-table td {{ vertical-align: bottom; height: 100px; padding-bottom: 5px; }}
        .signature-name {{ font-weight: bold; font-style: italic; margin-top: 5px; }}
        .signature-date {{ font-style: italic; font-size: 9px; padding-top: 2px; }}

        /* CSS cho hình ảnh đính kèm */
        .image-gallery {{
            display: grid;
            /* ĐÃ SỬA: Thay minmax(200px, 1fr) thành minmax(400px, 1fr) */
            /* Điều này giảm số cột và tăng kích thước tối thiểu/phần trăm cho mỗi hình ảnh */
            grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
            gap: 10px;
            margin-top: 15px;
            page-break-inside: avoid;
        }}
        .image-item {{
            padding: 5px;
            text-align: center;
            page-break-inside: avoid;
            background-color: #fff;
        }}
        .image-item img {{
            /* ĐÃ SỬA: Thử tăng max-width lên 200% để vượt qua giới hạn container nếu cần */
            max-width: 200%; 
            height: auto;
            max-height: 600px; 
            display: block;
            margin: 0 auto;
        }}
        </style>
    </head>
    <body>
        <h2>PHIẾU ĐỀ NGHỊ THANH TOÁN</h2>
        
        <div class="header-info">
            <div><b>Mã dự án:</b> {ma_du_an}</div>
            <div><b>Tên dự án:</b> {ten_du_an}</div>
            <div><b>Ngày đề xuất:</b> {ngay_de_xuat}</div>
            <div><b>Số TK nhận tiền:</b> {stk_nhan}</div>
        </div>

        <h3>1. Đề nghị thanh toán chi tiết</h3>
        {df1_html}
        <p class="total-row"><b>Tổng cộng:</b> 💰 {total_sum_formatted}</p>

        <h3>2. Theo dõi thanh toán</h3>
        {df2_html}

        <table class='signature-table'>
            <tr class='signature-header'>
                <th colspan='3'>KSG / Head Office</th>
                <th colspan='3'>Công ty, Dự án / Company, Project</th>
            </tr>
            <tr>
                <th class="signature-title">Giám đốc (HO)</th>
                <th class="signature-title">Kế toán trưởng (HO)</th>
                <th class="signature-title">Người kiểm (HO)</th>
                <th class="signature-title">Người duyệt (CTY/DA)</th>
                <th class="signature-title">Người kiểm (CTY/DA)</th>
                <th class="signature-title">Người đề nghị (CTY/DA)</th>
            </tr>
            <tr class="signature-content-row">
                <td style="vertical-align: bottom;">
                    <div style="height: 60px;"></div>
                    <div class="signature-name">({giam_doc or ' '})</div>
                    <div class="signature-date">Ngày: </div>
                </td>
                <td style="vertical-align: bottom;">
                    <div style="height: 60px;"></div>
                    <div class="signature-name">({ke_toan or ' '})</div>
                    <div class="signature-date">Ngày: </div>
                </td>
                <td style="vertical-align: bottom;">
                    <div style="height: 60px;"></div>
                    <div class="signature-name">({nguoi_kiemtra2 or ' '})</div>
                    <div class="signature-date">Ngày: </div>
                </td>
                <td style="vertical-align: bottom;">
                    <div style="height: 60px;"></div>
                    <div class="signature-name">({nguoi_duyet1 or ' '})</div>
                    <div class="signature-date">Ngày: </div>
                </td>
                <td style="vertical-align: bottom;">
                    <div style="height: 60px;"></div>
                    <div class="signature-name">({nguoi_kiemtra1 or ' '})</div>
                    <div class="signature-date">Ngày: </div>
                </td>
                <td style="vertical-align: bottom;">
                    <div style="height: 60px;"></div>
                    <div class="signature-name">({nguoi_lap or ' '})</div>
                    <div class="signature-date">Ngày: </div>
                </td>
            </tr>
        </table>
        
        {images_html} 

        <div style="margin-top: 20px; font-size: 10px; text-align: center;">Phiếu đề nghị thanh toán - Tự động tạo bởi Streamlit App</div>
        
    </body>
    </html>
    """
    return html

def create_pdf_from_html(html_content):
    """Sử dụng JavaScript để mở tab mới và kích hoạt lệnh in-to-PDF của trình duyệt."""
    
    escaped_html = html_content.replace('`', '\\`').replace('$', '\\$')
    
    js_code = f"""
    <script>
        const htmlContent = `{escaped_html}`;
        const blob = new Blob([htmlContent], {{type: 'text/html;charset=utf-8'}});
        const url = URL.createObjectURL(blob);
        const newWindow = window.open(url, '_blank');
        
        if (newWindow) {{
            newWindow.onload = () => {{
                // Đảm bảo CSS @page được áp dụng trước khi in
                setTimeout(() => {{ 
                    newWindow.print();
                }}, 500); // Chờ 0.5s để đảm bảo tài liệu được render
            }};
        }}
    </script>
    """
    
    st.components.v1.html(js_code, height=0)
    st.info("💡 **Lưu ý:** Trình duyệt sẽ mở một tab mới và hiển thị hộp thoại in. Vui lòng chọn **'Lưu dưới dạng PDF'** (Save as PDF). Để đảm bảo lề 10mm, hãy kiểm tra tùy chọn **Margins/Lề** trong hộp thoại in.")


col_preview, col_html_download, col_pdf_export = st.columns(3)

with col_preview:
    if st.button("👁️ Xem trước HTML", key="preview_btn"):
        st.components.v1.html(generate_html(), height=750, scrolling=True)

with col_html_download:
    html_content = generate_html()
    html_bytes = io.BytesIO(html_content.encode("utf-8"))
    st.download_button("⬇️ Xuất file HTML", data=html_bytes, file_name="phieu_de_nghi.html", mime="text/html", key="download_html_btn")

with col_pdf_export:
    if st.button("⬇️ Xuất file PDF", key="export_pdf_btn"):
        create_pdf_from_html(generate_html())

# ============================================================
# RESET APP
# ============================================================
st.markdown("---")
if st.button("🧹 Xóa tất cả dữ liệu", key="reset_app_btn"):
    st.session_state.table1 = []
    st.session_state.table2 = []
    st.session_state.uploaded_images = []
    safe_rerun()
