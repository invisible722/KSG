import streamlit as st
import pandas as pd
import io
import base64
import warnings

# ============================================================
# CẤU HÌNH VÀ HÀM HỖ TRỢ
# ============================================================

st.set_page_config(page_title="Phiếu đề nghị thanh toán", layout="wide")

# Hàm rerun an toàn (Giữ nguyên)
def safe_rerun():
    """Sử dụng st.rerun() để làm mới ứng dụng một cách an toàn."""
    st.rerun()

# Hàm định dạng tiền tệ (Giữ nguyên)
def format_currency(value):
    """Định dạng giá trị số thành chuỗi tiền tệ (ví dụ: 1000000 -> 1,000,000)."""
    try:
        if isinstance(value, str):
            value = float(value.replace(",", "").strip() or 0)
        elif value is None:
            return ""
        
        return f"{value:,.0f}"
    except:
        return value

# ===== HÀM CALLBACK RESET INPUT (ĐÃ THÊM) =====
def reset_table1_inputs():
    """Reset các giá trị input của Bảng 1 về trạng thái mặc định."""
    # Chỉ reset session state, Streamlit sẽ tự cập nhật widget khi rerun
    st.session_state["mota_input_key"] = ""
    st.session_state["donvi_input_key"] = ""
    st.session_state["soluong_input_key"] = 0.0
    st.session_state["dongia_input_key"] = ""
    st.session_state["ghichu1_input_key"] = ""

def reset_table2_inputs():
    """Reset các giá trị input của Bảng 2 về trạng thái mặc định."""
    st.session_state["goi_input"] = ""
    st.session_state["dutoan_raw"] = 0.0
    st.session_state["dachi_raw"] = 0.0
    st.session_state["dexuat_raw"] = 0.0
    st.session_state["ghichu2_input"] = ""

def reset_app_data():
    """Xóa tất cả dữ liệu và reset các input fields."""
    st.session_state.table1 = []
    st.session_state.table2 = []
    st.session_state.uploaded_images = []
    
    # Reset input fields Bảng 1 & Bảng 2
    reset_table1_inputs() 
    reset_table2_inputs()

# ===== HÀM CALLBACK THÊM DÒNG (ĐÃ THÊM) =====
def add_row_table1_and_reset():
    """Xử lý logic thêm dòng cho Bảng 1 và reset input."""
    # Lấy giá trị từ session state
    dongia_raw = st.session_state.dongia_input_key
    mota = st.session_state.mota_input_key
    soluong = st.session_state.soluong_input_key
    donvi = st.session_state.donvi_input_key
    ghichu1 = st.session_state.ghichu1_input_key
    
    try:
        dongia_value = float(str(dongia_raw).replace(",", "").strip() or 0)
        
        if not mota.strip():
             # Dùng warning ở đây sẽ bị xóa khi rerun, cần kiểm tra lại logic hiển thị.
             # Tuy nhiên, ta vẫn reset để đảm bảo trạng thái sạch.
             return # Thoát hàm nếu lỗi
        
        total = dongia_value * soluong
        
        st.session_state.table1.append({
            "Mô tả": mota,
            "Đơn vị": donvi,
            "Số lượng": soluong,
            "Đơn giá": format_currency(dongia_value),
            "Đơn giá_raw": dongia_value,
            "Tổng": format_currency(total),
            "Tổng_raw": total,
            "Ghi chú": ghichu1
        })
        
        # Reset inputs sau khi thêm thành công (tránh lỗi APIException)
        reset_table1_inputs()
        
    except ValueError:
        # Nếu có lỗi, không reset input để người dùng sửa
        st.error("⚠️ Vui lòng nhập đơn giá hợp lệ (chỉ số).") # Dùng st.error để thông báo rõ hơn
        # KHÔNG GỌI rerun Ở ĐÂY để cho phép callback hoàn thành

def add_row_table2_and_reset():
    """Xử lý logic thêm dòng cho Bảng 2 và reset input."""
    goi = st.session_state.goi_input
    dutoan_value = st.session_state.dutoan_raw
    dachi_value = st.session_state.dachi_raw
    dexuat_value = st.session_state.dexuat_raw

    # TÍNH TOÁN CỘT "CÒN LẠI"
    con_lai_value = dutoan_value - dachi_value - dexuat_value
    
    st.session_state.table2.append({
        "Gói": goi,
        "Dự toán": format_currency(dutoan_value),
        "Đã chi": format_currency(dachi_value),
        "Đề xuất chi tuần này": format_currency(dexuat_value),
        "Còn lại": format_currency(con_lai_value),
        "Ghi chú": st.session_state.ghichu2_input
    })
    
    # Reset inputs sau khi thêm thành công
    reset_table2_inputs()


# ============================================================
# KHỞI TẠO SESSION STATE
# ============================================================
# Khởi tạo keys cho input Bảng 1 (Cải tiến 1)
if "table1" not in st.session_state: st.session_state.table1 = []
if "table2" not in st.session_state: st.session_state.table2 = []
if "uploaded_images" not in st.session_state: st.session_state.uploaded_images = []

if "mota_input_key" not in st.session_state: st.session_state.mota_input_key = ""
if "donvi_input_key" not in st.session_state: st.session_state.donvi_input_key = ""
if "soluong_input_key" not in st.session_state: st.session_state.soluong_input_key = 0.0
if "dongia_input_key" not in st.session_state: st.session_state.dongia_input_key = ""
if "ghichu1_input_key" not in st.session_state: st.session_state.ghichu1_input_key = ""

# Khởi tạo keys cho input Bảng 2 (Cải tiến 4)
if "goi_input" not in st.session_state: st.session_state.goi_input = ""
if "dutoan_raw" not in st.session_state: st.session_state.dutoan_raw = 0.0
if "dachi_raw" not in st.session_state: st.session_state.dachi_raw = 0.0
if "dexuat_raw" not in st.session_state: st.session_state.dexuat_raw = 0.0
if "ghichu2_input" not in st.session_state: st.session_state.ghichu2_input = ""


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
    mota = st.text_input("Mô tả", key="mota_input_key") 
with col2:
    donvi = st.text_input("Đơn vị", key="donvi_input_key")
with col3:
    soluong = st.number_input("Số lượng", min_value=0.0, step=1.0, key="soluong_input_key")
with col4:
    dongia_raw = st.text_input("Đơn giá", key="dongia_input_key") 
    dongia_formatted = format_currency(dongia_raw)
    st.caption(f"💰 {dongia_formatted if dongia_formatted else ''}")
with col5:
    ghichu1 = st.text_input("Ghi chú", key="ghichu1_input_key")

# SỬ DỤNG CALLBACK FUNCTION on_click
if st.button("➕ Thêm dòng vào bảng 1", key="add_row_1", on_click=add_row_table1_and_reset):
    # Sau khi callback hoàn thành, rerun để cập nhật giao diện
    safe_rerun() 

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

    # Tính tổng cộng (Sử dụng giá trị thô)
    total_sum = sum(r["Tổng_raw"] for r in st.session_state.table1 if r.get("Tổng_raw") is not None)

    st.markdown(f"**Tổng cộng:** 💰 {format_currency(total_sum)}")

# ============================================================
# BẢNG 2: Theo dõi thanh toán
# ============================================================
st.markdown("### Bảng 💰2: Theo dõi thanh toán")

col1, col2, col3, col4, col5 = st.columns([1.5, 1.5, 1.5, 1.5, 2])
with col1:
    goi = st.text_input("Gói", key="goi_input")
with col2:
    # Cải tiến 4: Đổi sang st.number_input
    dutoan_value = st.number_input("Dự toán", min_value=0.0, step=1000.0, format="%.0f", key="dutoan_raw")
    st.caption(f"💰 {format_currency(dutoan_value) if dutoan_value else ''}")
with col3:
    # Cải tiến 4: Đổi sang st.number_input
    dachi_value = st.number_input("Đã chi", min_value=0.0, step=1000.0, format="%.0f", key="dachi_raw")
    st.caption(f"💰 {format_currency(dachi_value) if dachi_value else ''}")
with col4:
    # Cải tiến 4: Đổi sang st.number_input
    dexuat_value = st.number_input("Đề xuất chi tuần này", min_value=0.0, step=1000.0, format="%.0f", key="dexuat_raw")
    st.caption(f"💰 {format_currency(dexuat_value) if dexuat_value else ''}")
with col5:
    ghichu2 = st.text_input("Ghi chú (bảng 2)", key="ghichu2_input")

# SỬ DỤNG CALLBACK FUNCTION on_click
if st.button("➕ Thêm dòng vào bảng 2", key="add_row_2", on_click=add_row_table2_and_reset):
    # Sau khi callback hoàn thành, rerun để cập nhật giao diện
    safe_rerun() 

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
# PHẦN PHÊ DUYỆT (ĐÃ GỢI Ý TÊN MẶC ĐỊNH)
# ============================================================
st.markdown("### ✍️ Phần phê duyệt")

col1, col2, col3 = st.columns(3)
with col1:
    nguoi_lap = st.text_input("Người đề nghị (CTY/DA)", value="Trần Thị Ngọc Giàu")
    nguoi_kiemtra1 = st.text_input("Người kiểm (CTY/DA)", value="Nguyễn Ngọc Nghĩa")
with col2:
    nguoi_duyet1 = st.text_input("Người duyệt (CTY/DA)", value="Nguyễn Duy Lộc")
    nguoi_kiemtra2 = st.text_input("Người kiểm (HO)", value="Trần Thị Hải Yến")
with col3:
    ke_toan = st.text_input("Kế toán trưởng (HO)", value="Nguyễn Thị Ngọc Mai")
    giam_doc = st.text_input("Giám đốc phê duyệt (HO)", value="Ngô Hoài Đức")

# ============================================================
# UPLOAD HÌNH ẢNH
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
            bytes_data = uploaded_file.read()
            base64_encoded_image = base64.b64encode(bytes_data).decode("utf-8")
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
    
    # Bảng 1 (Sử dụng dữ liệu không có _raw để xuất HTML)
    df1_data = [{k: v for k, v in row.items() if k not in ["Đơn giá_raw", "Tổng_raw"]} for row in st.session_state.table1]
    df1 = pd.DataFrame(df1_data)
    if not df1.empty:
        df1.insert(0, 'Stt', range(1, 1 + len(df1)))
        columns_order_1 = ["Stt", "Mô tả", "Đơn vị", "Số lượng", "Đơn giá", "Tổng", "Ghi chú"]
        df1_html = df1[columns_order_1].to_html(index=False)
    else:
        df1_html = "<p><i>(Chưa có dữ liệu chi tiết thanh toán)</i></p>"

    # Bảng 2 (Giữ nguyên)
    df2 = pd.DataFrame(st.session_state.table2)
    if not df2.empty:
        df2.insert(0, 'Stt', range(1, 1 + len(df2)))
        columns_order_2 = ["Stt", "Gói", "Dự toán", "Đã chi", "Đề xuất chi tuần này", "Còn lại", "Ghi chú"]
        df2_html = df2[columns_order_2].to_html(index=False)
    else:
        df2_html = "<p><i>(Chưa có dữ liệu theo dõi thanh toán)</i></p>"
    
    # Tạo phần HTML cho hình ảnh (Giữ nguyên)
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
    
    # Tính Tổng cộng (Sử dụng cột _raw)
    total_sum = sum(r["Tổng_raw"] for r in st.session_state.table1 if r.get("Tổng_raw") is not None)
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
# SỬ DỤNG CALLBACK FUNCTION on_click
if st.button("🧹 Xóa tất cả dữ liệu", key="reset_app_btn", on_click=reset_app_data):
    # Sau khi callback hoàn thành, rerun để cập nhật giao diện
    safe_rerun()
