import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
import json
import base64
import pytz

# --- 1. CẤU HÌNH & KẾT NỐI (Giữ nguyên) ---
try:
    SHEET_ID = st.secrets["sheet_id"] 
    WORKSHEET_NAME = st.secrets["worksheet_name"]
    BASE64_CREDS = st.secrets["base64_service_account"] 
    decoded_json_bytes = base64.b64decode(BASE64_CREDS)
    CREDS_DICT = json.loads(decoded_json_bytes.decode('utf-8')) 
    CLIENT = gspread.service_account_from_dict(CREDS_DICT)
    SHEET = CLIENT.open_by_key(SHEET_ID).worksheet(WORKSHEET_NAME)
except Exception as e:
    st.error(f"Lỗi cấu hình: {e}")
    st.stop()

COLUMNS = ['Số thứ tự', 'Tên người dùng', 'Thời gian Check in', 'Thời gian Check out', 'Ghi chú', 'Tình trạng', 'Người duyệt']
VN_TZ = pytz.timezone('Asia/Ho_Chi_Minh')

# --- 2. HÀM XỬ LÝ (CHẶN TẠI GỐC) ---

@st.cache_data(ttl=1)
def load_data():
    try:
        all_values = SHEET.get_all_values()
        if len(all_values) <= 1: return pd.DataFrame(columns=COLUMNS)
        return pd.DataFrame(all_values[1:], columns=COLUMNS)
    except: return pd.DataFrame(columns=COLUMNS)

def update_check_out_in_sheet(user_email, now_vn, note_to_save):
    # LỚP BẢO VỆ 1: CHẶN TẠI HÀM (Nếu note trống, hàm này sẽ thoát ngay)
    if not note_to_save or str(note_to_save).strip() == "":
        return False

    load_data.clear()
    emails = SHEET.col_values(2)
    checkouts = SHEET.col_values(4)
    target_row = -1
    for i in range(len(emails) - 1, 0, -1):
        if emails[i].strip() == str(user_email).strip():
            if i >= len(checkouts) or not checkouts[i].strip():
                target_row = i + 1
                break
    
    if target_row != -1:
        SHEET.update_cell(target_row, 4, now_vn.strftime('%Y-%m-%d %H:%M:%S'))
        SHEET.update_cell(target_row, 5, str(note_to_save).strip())
        return True
    return False

# --- 3. GIAO DIỆN (UI) ---

st.set_page_config(layout="wide", page_title="Chấm Công")
st.title("⏰ Hệ thống Chấm công")

# LỚP BẢO VỆ 2: DÙNG FORM ĐỂ ĐÓNG GÓI DỮ LIỆU
with st.form("attendance_form"):
    st.write("### Nhập thông tin")
    input_email = st.text_input("📧 Email / Tên", value=st.session_state.get('saved_email', ''))
    
    # Ô nhập ghi chú
    input_note = st.text_input("📝 Ghi chú địa điểm (BẮT BUỘC KHI CHECK OUT)")
    
    st.write("---")
    c1, c2 = st.columns(2)
    do_in = c1.form_submit_button("🟢 CHECK IN", use_container_width=True)
    do_out = c2.form_submit_button("🔴 CHECK OUT", use_container_width=True)

# --- 4. LOGIC XỬ LÝ (LỚP BẢO VỆ 3 - QUAN TRỌNG NHẤT) ---

email_final = input_email.strip()
st.session_state.saved_email = email_final
now = datetime.now(VN_TZ)

# Biến cờ (Flag) - Mặc định là không cho phép ghi
allow_update = False 

if do_in:
    if not email_final:
        st.error("Vui lòng nhập tên!")
    else:
        # Code check in... (như cũ)
        pass 

if do_out:
    # KIỂM TRA GHI CHÚ TRƯỚC KHI LÀM BẤT CỨ ĐIỀU GÌ
    clean_note = input_note.strip()
    
    if not email_final:
        st.error("Vui lòng nhập tên!")
    elif clean_note == "":
        # NẾU TRỐNG -> HIỆN LỖI VÀ DỪNG LUÔN
        st.error("❌ LỖI: Ghi chú không được để trống khi Check Out!")
        st.stop() 
    else:
        # CHỈ KHI CÓ GHI CHÚ MỚI BẬT CỜ CHO PHÉP
        allow_update = True

# CHỈ KHI CỜ allow_update LÀ TRUE THÌ MỚI GỌI ĐẾN GOOGLE SHEET
if do_out and allow_update:
    if update_check_out_in_sheet(email_final, now, clean_note):
        st.success("Check Out thành công!")
        st.rerun()
    else:
        st.error("Không tìm thấy lượt Check In nào chưa đóng.")

# --- 5. HIỂN THỊ (Phần còn lại giữ nguyên) ---
st.write("---")
df_view = load_data()
if not df_view.empty:
    st.dataframe(df_view.iloc[::-1], use_container_width=True, hide_index=True)
