import streamlit as st
import pandas as pd
import gspread
import json
import base64

# --- CẤU HÌNH TRANG ---
st.set_page_config(layout="wide", page_title="Admin - Quản lý Chấm công")

# --- KẾT NỐI GOOGLE SHEETS (Dùng chung cấu hình với App nhân viên) ---
try:
    SHEET_ID = st.secrets["sheet_id"] 
    WORKSHEET_NAME = st.secrets["worksheet_name"]
    BASE64_CREDS = st.secrets["base64_service_account"] 
    
    decoded_json_bytes = base64.b64decode(BASE64_CREDS)
    CREDS_DICT = json.loads(decoded_json_bytes.decode('utf-8')) 
    CLIENT = gspread.service_account_from_dict(CREDS_DICT)
    SHEET = CLIENT.open_by_key(SHEET_ID).worksheet(WORKSHEET_NAME)
except Exception as e:
    st.error(f"Lỗi cấu hình/kết nối: {e}")
    st.stop()

COLUMNS = ['Số thứ tự', 'Tên người dùng', 'Thời gian Check in', 'Thời gian Check out', 'Ghi chú', 'Tình trạng']

# --- FUNCTIONS ---

def load_data():
    try:
        all_values = SHEET.get_all_values()
        if len(all_values) <= 1:
            return pd.DataFrame(columns=COLUMNS)
        # Lấy dữ liệu và đảm bảo đủ số cột (6 cột)
        df = pd.DataFrame(all_values[1:], columns=COLUMNS)
        return df
    except Exception as e:
        st.error(f"Lỗi tải dữ liệu: {e}")
        return pd.DataFrame(columns=COLUMNS)

def approve_entry(row_index):
    try:
        # Cột 'Tình trạng' là cột thứ 6 (F)
        SHEET.update_cell(row_index, 6, "Đã duyệt ✅")
        return True
    except:
        return False

def delete_entry(row_index):
    try:
        SHEET.delete_rows(row_index)
        return True
    except:
        return False

# --- GIAO DIỆN ADMIN ---

st.title("🔑 Trang Quản trị Chấm công")
st.info("Hệ thống phê duyệt các lượt Check-in/Check-out của nhân viên.")

# Tạo bộ lọc nhanh
df = load_data()

# Tabs chức năng
tab_pending, tab_history = st.tabs(["⏳ Chờ phê duyệt", "📜 Toàn bộ lịch sử"])

with tab_pending:
    # Lọc các dòng có trạng thái 'Chờ duyệt'
    pending_df = df[df['Tình trạng'] == "Chờ duyệt"]
    
    if pending_df.empty:
        st.success("Không có yêu cầu nào cần xử lý.")
    else:
        for index, row in pending_df.iterrows():
            # index + 2 vì: index 0 của DF là dòng 2 trong Google Sheets
            real_row_index = index + 2
            
            with st.expander(f"Yêu cầu từ: {row['Tên người dùng']} ({row['Thời gian Check in']})"):
                col1, col2, col3 = st.columns(3)
                col1.write(f"**Ghi chú:** {row['Ghi chú'] or 'Không có'}")
                col2.write(f"**Trạng thái hiện tại:** {row['Tình trạng']}")
                
                # Nút bấm xử lý
                if col3.button("PHÊ DUYỆT ✅", key=f"app_{real_row_index}", use_container_width=True):
                    if approve_entry(real_row_index):
                        st.toast("Đã phê duyệt!")
                        st.rerun()
                
                if col3.button("XÓA DÒNG 🗑️", key=f"del_{real_row_index}", use_container_width=True):
                    if delete_entry(real_row_index):
                        st.toast("Đã xóa bản ghi!")
                        st.rerun()

with tab_history:
    st.subheader("Dữ liệu tổng hợp")
    
    # Bộ lọc tìm kiếm
    search = st.text_input("🔍 Tìm kiếm tên nhân viên")
    display_df = df.copy()
    if search:
        display_df = display_df[display_df['Tên người dùng'].str.contains(search, case=False)]
    
    st.dataframe(
        display_df.iloc[::-1], 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "Tình trạng": st.column_config.TextColumn("Trạng thái", help="Chờ duyệt hoặc Đã duyệt")
        }
    )

    # Nút tải dữ liệu về Excel/CSV
    csv = display_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 Tải báo cáo (.CSV)", data=csv, file_name="cham_cong.csv", mime="text/csv")