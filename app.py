import streamlit as st
from google import genai
from google.genai import types
import PIL.Image
import io

# --- CẤU HÌNH TRANG ---
st.set_page_config(
    page_title="TruthGuard AI - National Final",
    page_icon="🛡️",
    layout="wide"
)

# --- TÙY CHỈNH CSS ĐỂ GIAO DIỆN ĐẸP HƠN ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 20px; height: 3em; background-color: #007bff; color: white; }
    .report-card { padding: 20px; border-radius: 15px; background-color: white; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

# --- KHỞI TẠO AI ---
# Đảm bảo bạn đã thêm GEMINI_API_KEY vào .streamlit/secrets.toml
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=API_KEY)
except:
    st.error("Thiếu API Key! Vui lòng kiểm tra lại Secrets.")

# --- SIDEBAR: HƯỚNG DẪN & THÔNG TIN ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/7542/7542190.png", width=100)
    st.title("TruthGuard AI")
    st.info("Hệ thống đa tác nhân cảnh báo tin giả dựa trên AI và dữ liệu thời gian thực.")
    st.divider()
    st.write("📌 **Hướng dẫn:**")
    st.caption("1. Nhập văn bản hoặc dán Link bài báo.")
    st.caption("2. Tải lên ảnh (chụp tin nhắn, bài đăng) hoặc video nghi vấn.")
    st.caption("3. Chờ AI đối chiếu với Google Search.")

# --- GIAO DIỆN CHÍNH ---
st.title("🛡️ Kiểm Chứng Tin Tức Đa Phương Tiện")
st.write("Hệ thống tự động phân tích độ tin cậy dựa trên hình ảnh, video và văn bản.")

# Chia cột cho phần nhập liệu
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📝 Nội dung & Liên kết")
    tin_tuc_nghi_ngo = st.text_area("Nhập nội dung hoặc dán link cần kiểm tra:", height=150, placeholder="Ví dụ: Link bài báo hoặc nội dung tin đồn trên Facebook...")
    
with col2:
    st.subheader("🖼️ Hình ảnh / Video")
    uploaded_file = st.file_uploader("Tải lên bằng chứng (Ảnh/Video):", type=["jpg", "jpeg", "png", "mp4", "mov"])
    if uploaded_file:
        if uploaded_file.type.startswith('image'):
            st.image(uploaded_file, caption="Ảnh đã tải lên", use_container_width=True)
        else:
            st.video(uploaded_file)

# --- NÚT XỬ LÝ ---
if st.button("🔍 BẮT ĐẦU PHÂN TÍCH CHUYÊN SÂU"):
    if not tin_tuc_nghi_ngo and not uploaded_file:
        st.warning("Vui lòng nhập thông tin hoặc tải file lên!")
    else:
        with st.spinner("🚀 TruthGuard đang quét dữ liệu toàn cầu..."):
            # Chuẩn bị nội dung gửi đi (Multimodal)
            contents = []
            
            # 1. Thêm text
            prompt_text = f"""
            Bạn là chuyên gia kiểm chứng sự thật cấp cao. Hãy sử dụng công cụ Tìm kiếm để xác minh:
            Nội dung/Link: {tin_tuc_nghi_ngo}
            
            YÊU CẦU TRẢ VỀ:
            1. PHẦN TRĂM ĐỘ CHÍNH XÁC: (Số từ 0-100 kèm dấu %)
            2. PHÂN TÍCH CHI TIẾT: (Đối chiếu với các báo lớn, nguồn chính thống)
            3. ĐIỂM NGHI VẤN: (Nếu là tin giả, hãy chỉ ra các dấu hiệu lừa đảo/sai lệch)
            4. LỜI KHUYÊN: (Hành động cụ thể cho người dùng)
            
            Trình bày bằng Markdown đẹp mắt.
            """
            contents.append(prompt_text)
            
            # 2. Thêm file nếu có
            if uploaded_file:
                if uploaded_file.type.startswith('image'):
                    img = PIL.Image.open(uploaded_file)
                    contents.append(img)
                else:
                    # Với video, Gemini cần được upload qua File API nếu file lớn, 
                    # ở đây ta xử lý đơn giản bằng bytes cho file nhỏ.
                    video_data = uploaded_file.read()
                    contents.append(types.Part.from_bytes(data=video_data, mime_type=uploaded_file.type))

            try:
                # Gọi Model (Dùng Gemini 2.0 Flash để có tốc độ và khả năng search tốt nhất)
                response = client.models.generate_content(
                    model='gemini-2.0-flash',
                    contents=contents,
                    config=types.GenerateContentConfig(
                        tools=[{"google_search": {}}]
                    )
                )

                # --- HIỂN THỊ KẾT QUẢ ---
                st.divider()
                st.balloons()
                
                # Trích xuất phần trăm (giả định AI trả về đúng định dạng)
                # Lưu ý: Trong thực tế bạn có thể dùng Regex để lấy số % ra vẽ biểu đồ
                
                st.subheader("📊 Kết quả phân tích")
                
                # Hiển thị nội dung từ AI
                st.markdown(response.text)
                
                st.success("Hệ thống đã hoàn tất đối chiếu dữ liệu.")

            except Exception as e:
                st.error(f"Lỗi kỹ thuật: {e}")

# --- FOOTER ---
st.divider()
st.caption("© 2026 TruthGuard AI - Dự án dự thi AI Young Guru - Đội ngũ: 3TLcoder")
