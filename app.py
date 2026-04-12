import streamlit as st
from google import genai
from google.genai import types
import PIL.Image
import io

# --- CẤU HÌNH GIAO DIỆN ---
st.set_page_config(
    page_title="TruthGuard AI - Fact Checker",
    page_icon="🛡️",
    layout="wide"
)

# --- CSS FIX LỖI HIỂN THỊ (ÉP MÀU CHỮ ĐẬM) ---
st.markdown("""
    <style>
    /* Nền chính của App */
    .stApp {
        background-color: #ffffff;
    }
    
    /* Ép màu tất cả các loại chữ tiêu đề và văn bản */
    h1, h2, h3, p, span, label {
        color: #1e293b !important; /* Màu xanh đen đậm, cực kỳ dễ đọc */
    }

    /* Tùy chỉnh tiêu đề chính */
    .main-title {
        color: #1e40af !important;
        font-size: 3.5rem !important;
        font-weight: 800 !important;
        text-align: center;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        padding-bottom: 20px;
    }

    /* Tùy chỉnh các khối Input */
    .stTextArea textarea {
        background-color: #f1f5f9 !important;
        color: #000000 !important;
        border: 1px solid #cbd5e1 !important;
    }
    
    /* Nút bấm */
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        background-color: #1e40af !important;
        color: white !important;
        font-size: 1.2rem !important;
        height: 3.5rem;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #1d4ed8 !important;
        transform: translateY(-2px);
    }
    </style>
    """, unsafe_allow_html=True)

# --- GIỮ NGUYÊN PHẦN KHỞI TẠO AI VÀ LOGIC BÊN DƯỚI ---

# --- KHỞI TẠO AI ---
# Sử dụng API Key từ Secrets của Streamlit
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=API_KEY)
except Exception:
    st.error("⚠️ Không tìm thấy API Key. Hãy cấu hình trong Secrets hoặc file .env")

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛠️ Điều khiển")
    st.info("Hệ thống kiểm chứng tin tức đa phương tiện của đội 3TLcoder.")
    st.divider()
    st.markdown("### 📊 Quota Status")
    st.caption("Model: Gemini 2.5 Flash (Active)")
    st.progress(0.4) # Demo thanh tiến trình

# --- GIAO DIỆN CHÍNH ---
st.markdown("<h1 class='main-title'>🛡️ TruthGuard AI</h1>", unsafe_allow_html=True)
st.write("<p style='text-align: center;'>Công nghệ AI xác minh tin giả qua Văn bản, Hình ảnh và Video</p>", unsafe_allow_html=True)

# Chia bố cục Input
col_text, col_media = st.columns([1.2, 1])

with col_text:
    st.markdown("### 📝 Nội dung xác minh")
    tin_tuc_nghi_ngo = st.text_area(
        "Dán văn bản bài báo, đoạn tin đồn hoặc Link tại đây:", 
        height=200, 
        placeholder="Ví dụ: Link báo giả mạo, tin nhắn lừa đảo chuyển tiền..."
    )

with col_media:
    st.markdown("### 📸 Bằng chứng Media")
    uploaded_file = st.file_uploader("Tải lên Ảnh chụp màn hình hoặc Video:", type=["jpg", "jpeg", "png", "mp4", "mov"])
    if uploaded_file:
        if uploaded_file.type.startswith('image'):
            st.image(uploaded_file, caption="Ảnh bằng chứng", use_container_width=True)
        else:
            st.video(uploaded_file)

# --- XỬ LÝ DỮ LIỆU ---
if st.button("🚀 BẮT ĐẦU KIỂM CHỨNG"):
    if not tin_tuc_nghi_ngo and not uploaded_file:
        st.warning("Vui lòng nhập ít nhất một loại dữ liệu (Văn bản hoặc File)!")
    else:
        with st.spinner("🔍 Hệ thống đang đối soát dữ liệu thực tế..."):
            
            # Chuẩn bị dữ liệu cho AI
            contents = []
            
            # Prompt tối ưu để AI trả về % và lời khuyên
            prompt_instruction = """
            Bạn là chuyên gia phân tích tin giả của TruthGuard. Hãy sử dụng Google Search để kiểm tra.
            Hãy phân tích kỹ các yếu tố: nguồn tin, tính xác thực của hình ảnh/video, và sự kiện liên quan.
            
            Yêu cầu cấu trúc phản hồi:
            1. [PERCENTAGE]: Đưa ra con số % tin cậy cụ thể (Ví dụ: 20% Thật - 80% Giả).
            2. [ANALYSIS]: Phân tích các bằng chứng tìm được từ các nguồn báo chí chính thống.
            3. [WARNINGS]: Chỉ ra các dấu hiệu lừa đảo hoặc cắt ghép (nếu có).
            4. [ADVICE]: Lời khuyên cụ thể cho người dùng (Ví dụ: Không nhấn link, báo cáo bài viết).
            
            Trình bày bằng Markdown, sử dụng bảng hoặc bullet points cho dễ đọc.
            """
            contents.append(prompt_instruction)
            
            if tin_tuc_nghi_ngo:
                contents.append(f"Nội dung cần kiểm tra: {tin_tuc_nghi_ngo}")
            
            if uploaded_file:
                if uploaded_file.type.startswith('image'):
                    img = PIL.Image.open(uploaded_file)
                    contents.append(img)
                else:
                    video_data = uploaded_file.read()
                    contents.append(types.Part.from_bytes(data=video_data, mime_type=uploaded_file.type))

            try:
                # Đổi model sang Gemini 2.5 Flash như yêu cầu
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=contents,
                    config=types.GenerateContentConfig(
                        tools=[{"google_search": {}}]
                    )
                )

                # --- HIỂN THỊ KẾT QUẢ ---
                st.divider()
                st.balloons()
                
                st.markdown("## 📋 Báo Cáo Kiểm Chứng")
                
                # Hiển thị nội dung phản hồi từ AI
                st.markdown(response.text)

            except Exception as e:
                st.error(f"❌ Lỗi: {str(e)}")

# --- FOOTER ---
st.divider()
st.markdown("<p style='text-align: center; color: gray;'>Dự án TruthGuard AI - National Final top 30 Hanoi</p>", unsafe_allow_html=True)
