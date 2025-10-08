import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Phiếu đề nghị thanh toán", layout="wide")

# ===== Hàm rerun an toàn =====
def safe_rerun():
    # Sử dụng st.rerun() để làm mới ứng dụng
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()

# ===== Hàm định dạng tiền tệ =====
def format_currency(value):
    """Định dạng giá trị số thành chuỗi tiền tệ (ví dụ: 1000000 -> 1,000,000)."""
    try:
        # Loại bỏ dấu phẩy (,) và khoảng trắng, sau đó chuyển sang float
        value = float(str(value).replace(",", "").strip())
        # Định dạng lại với dấu phẩy phân cách hàng nghìn
        return f"{value:,.0f}"
    except:
        return value

# ===== Khởi tạo session =====
if "table1" not in st.session_state:
    st.session_state.table1 = []
if "table2" not in st.session_state:
    st.session_state.table2 = []

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
        # Xử lý ValueError ở đây để tránh lỗi nếu dongia_raw không phải là số
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
    
    # Hiển thị tiêu đề cột (Bổ sung cột Stt)
    header_cols = st.columns([0.5, 2, 1, 1, 1, 2, 0.3])
    headers = ["Stt", "Mô tả", "Đơn vị", "Số lượng", "Đơn giá", "Tổng", ""]
    for i, header in enumerate(headers):
        header_cols[i].markdown(f"**{header}**")

    # Hiển thị dữ liệu (Bổ sung cột Stt)
    for i, row in enumerate(st.session_state.table1):
        cols = st.columns([0.5, 2, 1, 1, 1, 2, 0.3])
        cols[0].write(i + 1)  # Stt
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
        # Kiểm tra tính hợp lệ của tất cả 3 trường nhập liệu số
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
            "Còn lại": format_currency(con_lai_value), # Thêm cột Còn lại
            "Ghi chú": ghichu2
        })
        safe_rerun()
    except ValueError:
        st.warning("⚠️ Vui lòng nhập đúng định dạng số tiền cho Dự toán/Đã chi/Đề xuất chi.")

if st.session_state.table2:
    st.markdown("#### 📋 Danh sách theo dõi thanh toán")
    
    # Hiển thị tiêu đề cột (Bổ sung cột Stt và Còn lại)
    # 8 cột: Stt, Gói, Dự toán, Đã chi, Đề xuất, Còn lại, Ghi chú, X
    header_cols = st.columns([0.4, 1.3, 1.3, 1.3, 1.3, 1.3, 2.5, 0.3]) 
    headers = ["Stt", "Gói", "Dự toán", "Đã chi", "Đề xuất chi tuần này", "Còn lại", "Ghi chú", ""]
    for i, header in enumerate(headers):
        header_cols[i].markdown(f"**{header}**")
        
    # Hiển thị dữ liệu (Bổ sung cột Stt và Còn lại)
    for i, row in enumerate(st.session_state.table2):
        # 8 cột
        cols = st.columns([0.4, 1.3, 1.3, 1.3, 1.3, 1.3, 2.5, 0.3]) 
        cols[0].write(i + 1) # Stt
        cols[1].write(row["Gói"])
        cols[2].write(row["Dự toán"])
        cols[3].write(row["Đã chi"])
        cols[4].write(row["Đề xuất chi tuần này"])
        cols[5].write(row["Còn lại"]) # Dữ liệu cột Còn lại
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
# XUẤT HTML + XEM TRƯỚC + XUẤT PDF
# ============================================================
st.markdown("### 📤 Xuất tài liệu & Xem trước")

def generate_html():
    """Tạo chuỗi HTML hoàn chỉnh cho phiếu đề nghị thanh toán với CSS được tối ưu hóa cho in ấn."""
    
    # Bảng 1: Tạo DataFrame và chuyển sang HTML (Bổ sung Stt)
    df1 = pd.DataFrame(st.session_state.table1)
    if not df1.empty:
        df1.insert(0, 'Stt', range(1, 1 + len(df1))) # Thêm cột Stt
        columns_order_1 = ["Stt", "Mô tả", "Đơn vị", "Số lượng", "Đơn giá", "Tổng", "Ghi chú"]
        df1_html = df1[columns_order_1].to_html(index=False)
    else:
        df1_html = ""

    # Bảng 2: Tạo DataFrame và chuyển sang HTML (Bổ sung Stt và Còn lại)
    df2 = pd.DataFrame(st.session_state.table2)
    if not df2.empty:
        df2.insert(0, 'Stt', range(1, 1 + len(df2))) # Thêm cột Stt
        columns_order_2 = ["Stt", "Gói", "Dự toán", "Đã chi", "Đề xuất chi tuần này", "Còn lại", "Ghi chú"] # Cột Còn lại được thêm
        df2_html = df2[columns_order_2].to_html(index=False)
    else:
        df2_html = ""
    
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
        /* Đã sửa: Thiết lập khổ A4 nằm ngang và giảm margin tối đa để fit 1 trang */
        @page {{ size: A4 landscape; margin: 5mm; }} 
        body {{
            font-family: DejaVu Sans, Arial, sans-serif; /* Hỗ trợ tiếng Việt */
            font-size: 12px; /* Giảm từ 14px */
            margin: 0;
            padding: 0;
        }}
        h2 {{
            text-align: center;
            margin: 10px 0 15px 0; /* Giảm margin */
            font-size: 18px; /* Giảm size */
        }}
        h3 {{
            text-align: left;
            margin: 15px 0 8px 0; /* Giảm margin */
            font-size: 14px; /* Giảm size */
        }}
        /* Thông tin Header */
        .header-info {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 5px; /* Giảm khoảng cách */
            margin-bottom: 10px; /* Giảm margin */
            font-size: 12px; /* Giảm size */
        }}
        /* Bảng */
        table {{
            border-collapse: collapse;
            width: 100%;
            margin-top: 5px; /* Giảm margin */
        }}
        th, td {{
            border: 1px solid #000;
            padding: 4px; /* Giảm padding */
            text-align: center;
            font-size: 10px; /* Giảm từ 12px */
            line-height: 1.2;
        }}
        th {{
            background-color: #e0e0e0;
            font-weight: bold;
        }}
        /* Đảm bảo cột Mô tả/Gói căn trái */
        td:nth-child(2), th:nth-child(2) {{ 
            text-align: left; 
        }}
        /* Đảm bảo cột Stt căn giữa */
        td:nth-child(1), th:nth-child(1) {{ 
            text-align: center; 
        }}

        .total-row {{
            margin-top: 8px; /* Giảm margin */
            font-weight: bold;
            font-size: 12px;
            text-align: right;
            padding-right: 5px;
        }}
        /* Bảng chữ ký */
        .signature-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 25px; /* Giảm margin */
            font-size: 10px; /* Giảm size */
            border: none;
        }}
        .signature-table th, .signature-table td {{
            border: 1px solid #000;
            text-align: center;
            padding: 5px 3px; /* Giảm padding */
            line-height: 1.1;
        }}
        .signature-table th {{
            vertical-align: top;
        }}
        .signature-table td {{
            vertical-align: bottom; /* Đảm bảo căn dưới cùng */
            height: 100px; /* Giảm từ 120px */
            padding-bottom: 5px;
        }}
        .signature-header th {{
            background-color: #f2f2f2;
            font-weight: bold;
        }}
        .signature-title {{
            text-align: center;
            font-weight: bold;
            padding: 0px;
        }}
        .signature-name {{
            font-weight: bold;
            font-style: italic;
            margin-top: 5px;
        }}
        .signature-date {{
            font-style: italic;
            font-size: 9px;
            padding-top: 2px;
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
            <!-- Hàng Chữ Ký (Gồm khoảng trống ký, tên và ngày - Tên và Ngày được căn dưới) -->
            <tr class="signature-content-row">
                <td style="vertical-align: bottom;">
                    <div style="height: 60px;"></div> <!-- Khoảng trống cho chữ ký -->
                    <div class="signature-name">({giam_doc or ' '})</div>
                    <div class="signature-date">Ngày: </div>
                </td>
                <td style="vertical-align: bottom;">
                    <div style="height: 60px;"></div> <!-- Khoảng trống cho chữ ký -->
                    <div class="signature-name">({ke_toan or ' '})</div>
                    <div class="signature-date">Ngày: </div>
                </td>
                <td style="vertical-align: bottom;">
                    <div style="height: 60px;"></div> <!-- Khoảng trống cho chữ ký -->
                    <div class="signature-name">({nguoi_kiemtra2 or ' '})</div>
                    <div class="signature-date">Ngày: </div>
                </td>
                <td style="vertical-align: bottom;">
                    <div style="height: 60px;"></div> <!-- Khoảng trống cho chữ ký -->
                    <div class="signature-name">({nguoi_duyet1 or ' '})</div>
                    <div class="signature-date">Ngày: </div>
                </td>
                <td style="vertical-align: bottom;">
                    <div style="height: 60px;"></div> <!-- Khoảng trống cho chữ ký -->
                    <div class="signature-name">({nguoi_kiemtra1 or ' '})</div>
                    <div class="signature-date">Ngày: </div>
                </td>
                <td style="vertical-align: bottom;">
                    <div style="height: 60px;"></div> <!-- Khoảng trống cho chữ ký -->
                    <div class="signature-name">({nguoi_lap or ' '})</div>
                    <div class="signature-date">Ngày: </div>
                </td>
            </tr>
        </table>
        
        <div style="margin-top: 20px; font-size: 10px; text-align: center;">Phiếu đề nghị thanh toán - Tự động tạo bởi Streamlit App</div>
        
    </body>
    </html>
    """
    return html

def create_pdf_from_html(html_content):
    """Sử dụng JavaScript để mở tab mới và kích hoạt lệnh in-to-PDF của trình duyệt."""
    
    # 1. Chuẩn bị nội dung HTML đã được escape.
    escaped_html = html_content.replace('`', '\\`').replace('$', '\\$')
    
    # 2. Tạo mã JS bằng f-string, chèn nội dung đã escape.
    # Kích hoạt JavaScript để mở cửa sổ mới và gọi lệnh in
    js_code = f"""
    <script>
        // Nội dung HTML được chèn vào template literal
        const htmlContent = `{escaped_html}`;
        
        // Để sử dụng {{ và }} bên trong f-string, cần phải double-brace chúng
        const blob = new Blob([htmlContent], {{type: 'text/html;charset=utf-8'}});
        const url = URL.createObjectURL(blob);
        
        // Mở cửa sổ mới
        const newWindow = window.open(url, '_blank');
        
        // Kích hoạt lệnh in sau khi cửa sổ được tải
        if (newWindow) {{
            newWindow.onload = () => {{
                newWindow.print();
            }};
        }}
    </script>
    """
    
    # Nhúng JavaScript vào Streamlit
    st.components.v1.html(js_code, height=0)
    st.info("💡 **Lưu ý:** Trình duyệt sẽ mở một tab mới và hiển thị hộp thoại in. Vui lòng chọn **'Lưu dưới dạng PDF'** (Save as PDF) và chọn tùy chọn **'Fit to page'** hoặc **'Scale'** (Tỷ lệ) thấp hơn 100% trong cài đặt in của trình duyệt nếu nội dung vẫn bị tràn.")


col_preview, col_html_download, col_pdf_export = st.columns(3)

with col_preview:
    if st.button("👁️ Xem trước HTML"):
        st.components.v1.html(generate_html(), height=750, scrolling=True)

with col_html_download:
    html_content = generate_html()
    html_bytes = io.BytesIO(html_content.encode("utf-8"))
    st.download_button("⬇️ Xuất file HTML", data=html_bytes, file_name="phieu_de_nghi.html", mime="text/html")

with col_pdf_export:
    # Nút xuất PDF
    if st.button("⬇️ Xuất file PDF"):
        create_pdf_from_html(generate_html())

# ============================================================
# RESET APP
# ============================================================
if st.button("🧹 Xóa tất cả dữ liệu"):
    st.session_state.table1 = []
    st.session_state.table2 = []
    safe_rerun()
