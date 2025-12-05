import streamlit as st
import pandas as pd
import gspread
from gspread.exceptions import APIError, WorksheetNotFound, SpreadsheetNotFound
from datetime import datetime
import json
import time

# --- CẤU HÌNH TRANG VÀ CACHE ---
# 1. Điều chỉnh tự co dãn cho full màn hình
st.set_page_config(layout="wide") 

# Khởi tạo hoặc cập nhật trạng thái session để reset form
if 'form_key' not in st.session_state:
    st.session_state['form_key'] = 0

# Giả sử bạn đã lưu nội dung file service account JSON vào st.secrets["gcp_service_account"]
try:
    # Lấy thông tin xác thực từ Streamlit Secrets
    service_account_info = st.secrets["gcp_service_account"]
except KeyError:
    st.error("Lỗi: Không tìm thấy thông tin xác thực Google Service Account. Vui lòng kiểm tra file secrets.toml.")
    st.stop()


def connect_to_gsheet(spreadsheet_name, worksheet_name):
    """
    Thiết lập kết nối với Google Sheet bằng gspread.
    """
    try:
        # Xác thực bằng service account JSON
        gc = gspread.service_account_from_dict(service_account_info)
        
        # Mở Spreadsheet
        spreadsheet = gc.open(spreadsheet_name)
        
        # Mở Worksheet
        worksheet = spreadsheet.worksheet(worksheet_name)
        return worksheet
        
    except SpreadsheetNotFound:
        st.error(f"⚠️ Lỗi: Không tìm thấy Google Sheet có tên '{spreadsheet_name}'. Vui lòng kiểm tra lại tên file.")
        return None
    except WorksheetNotFound:
        st.error(f"⚠️ Lỗi: Không tìm thấy Sheet (tab) có tên '{worksheet_name}' trong file. Vui lòng kiểm tra lại tên tab.")
        return None
    except Exception as e:
        # Lỗi chung (bao gồm cả Response 200 do Permission Denied)
        st.error(f"⚠️ Lỗi kết nối Google Sheet: {e}")
        return None


# --- ĐỊNH NGHĨA HÀM load_data ---

@st.cache_data(ttl=60) # Tải lại dữ liệu sau mỗi 60 giây
def load_data(sheet_name, worksheet_name):
    ws = connect_to_gsheet(sheet_name, worksheet_name)
    if ws:
        # Lấy tất cả dữ liệu từ Sheet (bao gồm cả header)
        data = ws.get_all_values()
        if len(data) > 1:
             # Chuyển đổi thành DataFrame (bỏ hàng header đầu tiên)
            df = pd.DataFrame(data[1:], columns=data[0])
            return df
    return pd.DataFrame()


# Tên Spreadsheet và Worksheet
SPREADSHEET_NAME = "momijicustomer"
WORKSHEET_NAME = "Sheet1"

# --- THIẾT LẬP GIAO DIỆN STREAMLIT ---
st.title("🏡 Hệ Thống Theo Dõi Đặt Hàng Dịch Vụ Sửa Chữa BeniHOME")
st.markdown("---")

# 1. Nhập dữ liệu người đặt hàng dịch vụ
st.header("1. Nhập Thông Tin Đặt Hàng Mới")

# Sử dụng st.session_state['form_key'] để reset form
with st.form(key=f'order_form_{st.session_state["form_key"]}'):
    
    col1, col2 = st.columns(2)
    
    with col1:
        customer_name = st.text_input("📝 **Tên Khách Hàng**", max_chars=100)
        phone_number = st.text_input("📱 **Số Điện Thoại** (VD: 090xxxxxxx)", max_chars=15)
        service_request = st.selectbox(
            "🛠️ **Yêu Cầu Dịch Vụ**",
            options=[
                "Thay sàn gỗ",
                "Sơn nhà",
                "Sửa chữa nhà (Tổng thể)",
                "Sửa đồ nội thất",
                "Sửa điện nước",
                "Vệ sinh công nghiệp",
                "Khác"
            ]
        )
    with col2:
        address = st.text_area("📍 **Địa Chỉ Cần Sửa Chữa**", max_chars=200, height=200)

    # Nút submit nằm ngoài cột để dễ quản lý
    submit_button = st.form_submit_button(label='Lưu Đơn Hàng')

# Khởi tạo biến worksheet để có thể kiểm tra ở phần load_data
worksheet = None 

if submit_button:
    # Kiểm tra dữ liệu bắt buộc
    if not all([customer_name, phone_number, address, service_request]):
        st.error("Vui lòng điền đầy đủ tất cả các trường thông tin.")
    else:
        # 2. Lưu dữ liệu vào Google Sheet
        worksheet = connect_to_gsheet(
            spreadsheet_name=SPREADSHEET_NAME,
            worksheet_name=WORKSHEET_NAME
        )

        if worksheet:
            try:
                # Lấy tất cả dữ liệu hiện có (bao gồm header) để tính Số thứ tự
                existing_data = worksheet.get_all_values()
                next_order_id = len(existing_data)
                
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # Chuẩn bị dữ liệu để lưu theo thứ tự 7 cột (Đã thêm Tình trạng):
                new_order_data = [
                    next_order_id,     # Số thứ tự
                    timestamp,         # Thời Gian
                    customer_name,     # Tên Khách Hàng
                    phone_number,      # Số Điện Thoại
                    address,           # Địa Chỉ
                    service_request,   # Yêu Cầu Dịch Vụ
                    "Mới"              # Tình trạng (Giá trị mặc định)
                ]

                # Thêm một hàng dữ liệu mới vào Sheet
                worksheet.append_row(new_order_data)
                st.success("✅ **Lưu đơn hàng thành công!**")
                st.balloons()
                
                # --- THAO TÁC RESET FORM ---
                load_data.clear() 
                st.session_state['form_key'] += 1
                st.rerun() 
                # -------------------------
                
            except APIError as e:
                st.error(f"⚠️ Lỗi GHI DỮ LIỆU vào Google Sheet (API Error): {e}")
                st.warning("Vui lòng kiểm tra: 1. Quyền **Editor** đã chia sẻ cho Service Account chưa? 2. Tiêu đề các cột trong Sheet có khớp không?")
            except Exception as e:
                st.error(f"⚠️ Lỗi KHÔNG XÁC ĐỊNH khi lưu dữ liệu: {e}")

st.markdown("---")
## 2. Danh Sách Đơn Hàng và Cập Nhật Tình Trạng
st.header("2. Danh Sách Đơn Hàng")

# Tải và hiển thị dữ liệu
data_load_state = st.text('Đang tải dữ liệu...')
df = load_data(SPREADSHEET_NAME, WORKSHEET_NAME)
data_load_state.text('Đã tải dữ liệu thành công!')

if not df.empty:
    
    # --- 1. Chuẩn bị DataFrame cho st.data_editor ---
    
    # Tạo bản sao DataFrame và đặt 'Số thứ tự' làm index để theo dõi thay đổi
    df_edit = df.copy() 
    try:
        df_edit['Số thứ tự'] = pd.to_numeric(df_edit['Số thứ tự'], errors='coerce', downcast='integer')
        df_edit.set_index('Số thứ tự', inplace=True)
    except Exception as e:
        st.warning(f"Không thể đặt 'Số thứ tự' làm chỉ mục: {e}. Vui lòng đảm bảo cột này không có giá trị trống.")

    # Đổi tên cột để hiển thị tiếng Việt thân thiện hơn
    df_edit.rename(columns={
        'Tên Khách Hàng': 'Tên khách', 
        'Số Điện Thoại': 'Số điện thoại', 
        'Thời Gian': 'Ngày tạo',
        'Địa Chỉ': 'Địa chỉ',
        'Yêu Cầu Dịch Vụ': 'Yêu cầu dịch vụ',
        'Tình trạng': 'Tình trạng' # Giữ nguyên tên này cho việc update gsheet
    }, inplace=True)

    # Định nghĩa lại thứ tự và tập hợp các cột hiển thị
    display_columns = [
        'Ngày tạo', 
        'Tên khách', 
        'Số điện thoại', 
        'Địa chỉ', 
        'Yêu cầu dịch vụ',
        'Tình trạng' 
    ]
    df_display = df_edit[[col for col in display_columns if col in df_edit.columns]]

    # --- 2. Thêm Nút Xuất JSON ---
    def to_json(df):
        # Chuyển DataFrame sang dạng record JSON (list of dicts)
        return df.to_json(orient="records", force_ascii=False, indent=4)

    json_string = to_json(df_display.reset_index()) # Đưa Số thứ tự về cột thường khi xuất

    st.download_button(
        label="⬇️ Xuất Dữ Liệu sang JSON",
        data=json_string,
        file_name=f'don_hang_benihome_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json',
        mime='application/json',
        help="Tải toàn bộ danh sách đơn hàng hiện tại dưới dạng tệp JSON."
    )

    st.caption("💡 **Nhấn đúp chuột vào cột 'Tình trạng' để thay đổi trạng thái.**")

    # --- 3. Hiển thị bảng có thể chỉnh sửa (data_editor) ---
    edited_df = st.data_editor(
        df_display,
        key="data_editor",
        # Cấu hình cột 'Tình trạng' thành Selectbox (Dropdown)
        column_config={
            "Tình trạng": st.column_config.SelectboxColumn(
                "Tình trạng",
                help="Cập nhật tình trạng của đơn hàng",
                width="medium",
                options=["Mới", "Đang chăm sóc", "Hoàn thành", "Hủy"],
                required=True,
            ),
        },
        # Chỉ cho phép chỉnh sửa cột 'Tình trạng'
        disabled=df_display.columns.difference(['Tình trạng']), 
        width='stretch'
    )
    
    # --- 4. Logic Ghi lại thay đổi vào Google Sheet ---
    
    # Kiểm tra xem có hàng nào được chỉnh sửa không
    if st.session_state["data_editor"]["edited_rows"]:
        with st.spinner("🔄 Đang cập nhật trạng thái đơn hàng..."):
            
            worksheet = connect_to_gsheet(SPREADSHEET_NAME, WORKSHEET_NAME)
            if worksheet:
                changes = st.session_state["data_editor"]["edited_rows"]
                
                # Lấy toàn bộ dữ liệu (bao gồm header) từ Sheet để tìm đúng số hàng
                all_records = worksheet.get_all_values()
                header = all_records[0]
                
                try:
                    status_col_index = header.index("Tình trạng") + 1 
                    id_col_index = header.index("Số thứ tự") + 1
                except ValueError:
                    st.error("Lỗi: Không tìm thấy cột 'Tình trạng' hoặc 'Số thứ tự' trong Google Sheet. Vui lòng kiểm tra tiêu đề cột.")
                    st.stop()
                

                updated_successfully = False
                
                for index, updated_data in changes.items():
                    order_id = index 
                    new_status = updated_data.get("Tình trạng")
                    
                    if new_status:
                        # Tìm số hàng (row number) trong Google Sheet dựa trên 'Số thứ tự'
                        gsheet_row_number = -1
                        for i, row in enumerate(all_records):
                            # So sánh giá trị cột 'Số thứ tự' trong sheet (row[id_col_index - 1]) với order_id
                            if str(row[id_col_index - 1]) == str(order_id): 
                                # gsheet_row_number là số hàng (1-based)
                                gsheet_row_number = i + 1 
                                break
                        
                        if gsheet_row_number > 1: # Đảm bảo không ghi đè lên hàng header
                            # Cập nhật ô cụ thể (Hàng: gsheet_row_number, Cột: status_col_index)
                            try:
                                worksheet.update_cell(gsheet_row_number, status_col_index, new_status)
                                updated_successfully = True
                                st.toast(f"✅ Đã cập nhật Đơn hàng ID {order_id} sang trạng thái: {new_status}")
                            except Exception as e:
                                st.error(f"Lỗi khi cập nhật ID {order_id}: {e}")
                        
        if updated_successfully:
            load_data.clear()
            st.session_state["data_editor"]["edited_rows"] = {}
            st.rerun() 

else:
    st.info("Chưa có đơn hàng nào được lưu hoặc không thể kết nối Google Sheet. Vui lòng kiểm tra permissions và tên Sheet.")

st.markdown("---")
st.info("Ứng dụng được lập trình bởi NNT.")