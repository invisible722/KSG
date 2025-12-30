import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
import json
import base64
import pytz

# --- CẤU HÌNH GOOGLE SHEETS ---
try:
    SHEET_ID = st.secrets["sheet_id"] 
    WORKSHEET_NAME = st.secrets["worksheet_name"]
    BASE64_CREDS = st.secrets["base64_service_account"] 
except Exception:
    st.error("Lỗi: Không tìm thấy cấu hình trong Streamlit Secrets.")
    st.stop()

# Đảm bảo đủ 7 cột để khớp với Google Sheet của bạn
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
@st.cache_data(ttl=1) # Giảm TTL xuống 1 giây để cập nhật dữ liệu tức thì
def load_data():
    try:
        all_values = SHEET.get_all_values()
        if len(all_values) <= 1:
            return pd.DataFrame(columns=COLUMNS)
        df = pd.DataFrame(all_values[1:], columns=COLUMNS)
        return df
    except Exception:
        return pd.DataFrame(columns=COLUMNS)

def find_next_available_row():
    col_b = SHEET.col_values(2)
    filled_rows = [row for row in col_b if row.strip()]
    return len(filled_rows) + 1

def append_check_in_to_sheet(user_email, now_vn):
    clean_email = str(user_email).strip()
    load_data.clear()
    next_row = find_next_available_row() + 1
    
    stt_column = SHEET.col_values(1)[1:] 
    stt_numbers = [int(x) for x in stt_column if str(x).isdigit()]
    new_stt = max(stt_numbers) + 1 if stt_numbers else 1
    
    # Ghi 7 cột (cột cuối để trống)
    new_row = [new_stt, clean_email, now_vn.strftime('%Y-%m-%d %H:%M:%S'), '', '', 'Chờ duyệt', '']
    SHEET.update(f"A{next_row}:G{next_row}", [new_row], value_input_option='USER_ENTERED')
    return True

def update_check_out_in_sheet(user_email, now_vn, note):
    # --- KHÓA BẢO VỆ CỨNG TẠI TẦNG DỮ LIỆU ---
    # Nếu vì lý do nào đó code giao diện bị bỏ qua, hàm này sẽ chặn lại nếu note trống
    clean_note = str(note).strip()
    if not clean_note:
        return False
        
    clean_email = str(user_email).strip()
    load_data.clear()
    emails = SHEET.col_values(2)
    checkouts = SHEET.col_values(4)
    
    target_row = -1
    for i in range(len(emails) - 1, 0, -1):
        if emails[i].strip() == clean_email:
            # Kiểm tra dòng chưa có Check out (cột 4 trống)
            if i >= len(checkouts) or not checkouts[i].strip():
                target_row = i + 1
                break
    
    if target_row != -1:
        # Cập nhật giờ Out (cột 4) và Ghi chú (cột 5)
        SHEET.update_cell(target_row, 4, now_vn.strftime('%Y-%m-%d %H:%M:%S'))
        SHEET.update_cell(target_row, 5, clean_note)
        return True
    return False

# --- GIAO DIỆN CHÍNH ---
st.set_page_config(layout="wide", page_title="Chấm công TTS")
vn_tz = pytz.timezone('Asia/Ho_Chi_Minh') # Múi giờ Việt Nam

st.title("⏰ Hệ thống Chấm công Thực tập sinh")

# Dùng st.form để chốt dữ liệu tại thời điểm bấm nút
with st.form("form_cham_cong", clear_on_submit=False):
    st.info("Lưu ý: Bạn phải nhập Ghi chú địa điểm làm việc khi thực hiện Check Out.")
    
    email_input = st.text_input("📧 Email / Tên người dùng", 
                                value=st.session_state.get('last_user_email', ''),
                                placeholder="Ví dụ: nguyenvana@gmail.com")
    
    # Biến ghi chú quan trọng
    note_input = st.text_input("📝 Ghi chú Địa điểm làm việc (Bắt buộc khi Check Out)", 
                               placeholder="VD: Làm tại văn phòng / Remote tại nhà")
    
    st.markdown("---")
    col_in, col_out = st.columns(2)
    btn_in = col_in.form_submit_button("🟢 CHECK IN", use_container_width=True)
    btn_out = col_out.form_submit_button("🔴 CHECK OUT", use_container_width=True)

# --- XỬ LÝ LOGIC ---
user_email = email_input.strip()
st.session_state.last_user_email = user_email
current_now = datetime.now(vn_tz)

if btn_in:
    if not user_email:
        st.error("❗ Vui lòng nhập Email/Tên trước khi Check In.")
    else:
        if append_check_in_to_sheet(user_email, current_now):
            st.success(f"Đã Check In: {current_now.strftime('%H:%M:%S')}")
            st.rerun()

if btn_out:
    # 1. Kiểm tra Email
    if not user_email:
        st.error("❗ Vui lòng nhập Email/Tên để Check Out.")
    # 2. Kiểm tra Ghi chú cực kỳ nghiêm ngặt
    elif not note_input or note_input.strip() == "":
        st.error("❌ LỖI: Bạn KHÔNG THỂ Check Out nếu không có ghi chú địa điểm!")
        st.warning("Vui lòng điền thông tin vào ô Ghi chú phía trên.")
        st.stop() # Dừng hẳn script, không cho phép chạy code bên dưới
    else:
        # 3. Chỉ khi có ghi chú mới gọi hàm ghi sheet
        if update_check_out_in_sheet(user_email, current_now, note_input.strip()):
            st.success(f"Đã Check Out: {current_now.strftime('%H:%M:%S')}")
            st.rerun()
        else:
            st.error("❌ Không tìm thấy lượt Check In nào đang mở cho tên này.")

# --- HIỂN THỊ BẢNG ---
st.markdown("---")
df_display = load_data()
if not df_display.empty:
    st.write("### Lịch sử chấm công gần đây")
    # Đảo ngược bảng để xem mới nhất lên đầu
    st.dataframe(df_display.
