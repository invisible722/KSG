# app.py
import io
import math
import textwrap
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

st.set_page_config(layout="wide")
st.title("🖼️ AI Agent — Ảnh ghép lưới kèm mô tả + Preview")

# ---------- Hàm đo text ----------
def measure_text(draw, text, font):
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        return w, h
    except Exception:
        try:
            return font.getsize(text)
        except Exception:
            return (len(text) * 6, 12)

# ---------- Hàm tạo ảnh ghép ----------
def make_grid_with_captions(cells, cols=4, size=(300, 300), caption_height=60, bg_color=(255,255,255)):
    total = len(cells)
    if total == 0:
        return None

    rows = math.ceil(total / cols)
    w = cols * size[0]
    h = rows * (size[1] + caption_height)
    grid = Image.new("RGB", (w, h), bg_color)
    draw = ImageDraw.Draw(grid)

    # Font hỗ trợ tiếng Việt
    font = None
    for fname in ("NotoSans-Regular.ttf", "DejaVuSans.ttf", "arial.ttf"):
        try:
            font = ImageFont.truetype(fname, 18)
            break
        except Exception:
            font = None
    if font is None:
        font = ImageFont.load_default()

    for i, cell in enumerate(cells):
        r, c = divmod(i, cols)
        x = c * size[0]
        y = r * (size[1] + caption_height)

        fb = cell.get("file_bytes")
        desc = (cell.get("caption") or "").strip()

        if fb:
            try:
                img = Image.open(io.BytesIO(fb)).convert("RGB")
                img = img.resize(size)
                grid.paste(img, (x, y))
            except Exception:
                pass

        if desc:
            lines = textwrap.wrap(desc, width=25)
            lines = lines[:2]
            for li, line in enumerate(lines):
                tw, th = measure_text(draw, line, font)
                tx = x + (size[0] - tw) // 2
                ty = y + size[1] + li * (th + 4) + 6
                draw.text((tx, ty), line, fill=(0, 0, 0), font=font)

    return grid


# ---------- Session init ----------
if "uploader_key" not in st.session_state:
    st.session_state["uploader_key"] = 0
if "confirm_reset" not in st.session_state:
    st.session_state["confirm_reset"] = False

# ---------- Giao diện ----------
st.markdown("### 👉 Tải lên nhiều ảnh, xem preview 100x100 và nhập mô tả")

uploaded_files = st.file_uploader(
    "Chọn nhiều ảnh (PNG/JPG)",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True,
    key=f"uploader_{st.session_state.uploader_key}"
)

cells = []
if uploaded_files:
    st.markdown("### ✍️ Nhập mô tả cho từng ảnh")
    for i, file in enumerate(uploaded_files):
        fb = file.getvalue()
        col1, col2 = st.columns([1, 5])
        with col1:
            try:
                img_preview = Image.open(io.BytesIO(fb)).convert("RGB")
                img_preview = img_preview.resize((100, 100))
                st.image(img_preview)
            except Exception:
                st.write("❌ Không xem được")
        with col2:
            caption = st.text_input(f"Mô tả cho ảnh {i+1} ({file.name})", key=f"cap_{i}")
        cells.append({"file_bytes": fb, "caption": caption})

if cells:
    col_a, col_b = st.columns([1,1])
    with col_a:
        cols_input = st.number_input("Số cột trong lưới", min_value=1, max_value=10, value=4)

    with col_b:
        if st.button("🔄 Reset (Xoá tất cả)"):
            st.session_state["confirm_reset"] = True
            st.rerun()

    # Popup xác nhận reset
    if st.session_state["confirm_reset"]:
        st.warning("Bạn có chắc muốn xoá hết dữ liệu và tải lại từ đầu?")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ Yes, xoá hết"):
                st.session_state.clear()
                st.session_state["uploader_key"] = st.session_state.get("uploader_key", 0) + 1
                st.rerun()
        with c2:
            if st.button("❌ No, giữ lại"):
                st.session_state["confirm_reset"] = False
                st.rerun()

    if st.button("🚀 Tạo ảnh ghép"):
        grid_img = make_grid_with_captions(
            cells,
            cols=cols_input,
            size=(300, 300),
            caption_height=70
        )
        if grid_img:
            st.success("✅ Ảnh ghép đã tạo xong")
            st.image(grid_img, use_container_width=True)

            buf = io.BytesIO()
            grid_img.save(buf, format="PNG")
            buf.seek(0)
            st.download_button(
                "📥 Tải ảnh PNG",
                data=buf.getvalue(),
                file_name="grid_custom.png",
                mime="image/png"
            )
