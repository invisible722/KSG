import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
import json
import base64
import pytz

# Thiết lập múi giờ Việt Nam
vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')

# Lấy thời gian hiện tại theo giờ VN
now_vn = datetime.now(vn_tz)

# Định dạng thời gian để ghi vào sheet
formatted_time = now_vn.strftime('%Y-%m-%d %H:%M:%S')

# --- CẤU HÌNH GOOGLE SHEETS ---
try:
    SHEET_ID = st.secrets["sheet_id"] 
    WORKSHEET_NAME = st.secrets["worksheet_name"]
    BASE64_CREDS = st.secrets["base64_service_account"] 
except Exception:
    st.error("Lỗi: Không tìm thấy cấu hình trong Streamlit Secrets.")
    st.stop()

COLUMNS = ['Số thứ tự', 'Tên người dùng', 'Thời gian Check in', 'Thời gian Check out', 'Ghi chú', 'Tình trạng', 'Người duyệt'] 

# --- KẾT NỐI ---
try:
    decoded_json_bytes = base64.b64decode(BASE64_CREDS)
    CREDS_DICT = json.loads(decoded_json_bytes.decode('utf-8')) 
    CLIENT = gspread.service_account_from_dict(CREDS_DICT)
    SHEET = CLIENT.open_by_key(SHEET_ID).worksheet(WORKSHEET_NAME)
except Exception as e:
    st.error(f"Lỗi kết nối: {e}")
    st.stop()

# --- FUNCTIONS ---

@st.cache_data(ttl=2)
def load_data():
    try:
        all_values = SHEET.get_all_values()
        if len(all_values) <= 1:
            return pd.DataFrame(columns=COLUMNS)
        df = pd.DataFrame(all_values[1:], columns=COLUMNS)
        df['Thời gian Check in'] = pd.to_datetime(df['Thời gian Check in'], errors='coerce')
        df['Thời gian Check out'] = pd.to_datetime(df['Thời gian Check out'], errors='coerce')
        return df
    except Exception as e:
        return pd.DataFrame(columns=COLUMNS)

def find_next_available_row():
    # Chỉ đếm những dòng có dữ liệu thực sự ở cột B (Email)
    # Loại bỏ hoàn toàn các ô trống hoặc chỉ có dấu cách
    col_b = SHEET.col_values(2)
    filled_rows = [row for row in col_b if row.strip()]
    return len(filled_rows) + 1

def append_check_in_to_sheet(user_email, now):
    vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    now_vn = datetime.now(vn_tz) # Lấy giờ VN ngay lúc này
    
    # KIỂM TRA CUỐI CÙNG TRƯỚC KHI GHI
    clean_email = str(user_email).strip()
    if not clean_email:
        return False

    load_data.clear()
    next_row = find_next_available_row() + 1
    
    stt_column = SHEET.col_values(1)[1:] 
    stt_numbers = [int(x) for x in stt_column if str(x).isdigit()]
    new_stt = max(stt_numbers) + 1 if stt_numbers else 1
    
    new_row = [new_stt, clean_email, now_vn.strftime('%Y-%m-%d %H:%M:%S'), '', '', 'Chờ duyệt']
    SHEET.update(f"A{next_row}:G{next_row}", [new_row], value_input_option='USER_ENTERED')
    return True

def update_check_out_in_sheet(user_email, now, note):
    vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    now_vn = datetime.now(vn_tz) # Lấy giờ VN ngay lúc này
    clean_email = str(user_email).strip()
    if not clean_email:
        return False

    load_data.clear()
    emails = SHEET.col_values(2)
    checkouts = SHEET.col_values(4)
    
    target_row = -1
    for i in range(len(emails) - 1, 0, -1):
        if emails[i].strip() == clean_email:
            if i >= len(checkouts) or not checkouts[i].strip():
                target_row = i + 1
                break
    
    if target_row != -1:
        SHEET.update_cell(target_row, 4, now_vn.strftime('%Y-%m-%d %H:%M:%S'))
        SHEET.update_cell(target_row, 5, note)
        return True
    return False

# --- STREAMLIT UI ---

st.set_page_config(layout="wide", page_title="Hệ thống Chấm công")
st.title("⏰ Hệ thống Chấm công")

# Xử lý Email đầu vào
# --- VỊ TRÍ CHÈN: THAY THẾ TOÀN BỘ PHẦN INPUT VÀ NÚT BẤM CŨ ---

# 1. Tạo một Form để quản lý dữ liệu nhập vào đồng bộ
with st.form("attendance_form", clear_on_submit=False):
    st.subheader("📝 Thông tin Chấm công")
    
    # Nhập Email/Tên
    raw_email = st.text_input(
        "📧 Email hoặc Tên người dùng", 
        value=st.session_state.get('last_user_email', ''), 
        placeholder="Nhập chính xác tên/email để hệ thống tìm đúng dòng"
    )
    
    # Nhập Ghi chú
    note_val = st.text_input(
        "📍 Ghi chú Địa điểm làm việc (Bắt buộc khi Check Out)", 
        placeholder="VD: Làm việc tại văn phòng / Remote tại nhà"
    )
    
    st.markdown("---")
    # Chia cột cho 2 nút bấm bên trong Form
    col_in, col_out = st.columns(2)
    
    with col_in:
        btn_checkin = st.form_submit_button("🟢 CHECK IN", use_container_width=True)
    with col_out:
        btn_checkout = st.form_submit_button("🔴 CHECK OUT", use_container_width=True)

# 2. XỬ LÝ LOGIC SAU KHI NHẤN NÚT (Nằm ngoài khối 'with st.form')
user_email = raw_email.strip()
st.session_state.last_user_email = user_email

if btn_checkin:
    if not user_email:
        st.error("❗ LỖI: Vui lòng nhập Email/Tên trước khi Check In.")
    else:
        # Lấy giờ Việt Nam (như đã hướng dẫn ở bước trước)
        vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
        if append_check_in_to_sheet(user_email, datetime.now(vn_tz)):
            st.toast("Check In thành công!")
            st.rerun()

if btn_checkout:
    # --- KIỂM TRA ĐIỀU KIỆN GHI CHÚ TẠI ĐÂY ---
    if not user_email:
        st.error("❗ LỖI: Vui lòng nhập Email/Tên.")
    elif not note_val.strip():
        # NẾU GHI CHÚ TRỐNG -> HIỆN CẢNH BÁO VÀ DỪNG LẠI LUÔN
        st.warning("⚠️ KHÔNG THỂ CHECK OUT: Bạn phải nhập Ghi chú địa điểm làm việc!")
    else:
        # CHỈ KHI CÓ GHI CHÚ MỚI CHẠY LỆNH NÀY
        vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
        if update_check_out_in_sheet(user_email, datetime.now(vn_tz), note_val.strip()):
            st.toast("Check Out thành công!")
            st.rerun()
        else:
            st.error("❌ Không tìm thấy phiên Check In nào chưa đóng của bạn.")

# --- TIẾP THEO LÀ PHẦN HIỂN THỊ BẢNG DỮ LIỆU (Giữ nguyên phần load_data cũ) ---
st.markdown("---")
# ... (phần code df_display bên dưới giữ nguyên)



st.markdown("---")
df_display = load_data()
if not df_display.empty:
    # Hiển thị dữ liệu, lọc bỏ các dòng mà cột 'Tên người dùng' bị trống (nếu lỡ có dòng lỗi cũ)
    valid_df = df_display[df_display['Tên người dùng'].str.strip() != ""]
    st.dataframe(valid_df.iloc[::-1], use_container_width=True, hide_index=True)











