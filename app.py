import streamlit as st
import google.generativeai as genai
import anthropic
import os
from PIL import Image
import streamlit as st
# ... (các import khác giữ nguyên)

# ==========================================
# 1. CẤU HÌNH API KEY (LẤY TỪ SECRETS KÍN)
# ==========================================

# Gọi key của Gemini
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# Khi nào bạn có key Claude thật, hãy mở comment 2 dòng dưới này:
# CLAUDE_API_KEY = st.secrets["CLAUDE_API_KEY"]
# judge_client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
# 2. ĐỊNH NGHĨA CÁC TÁC NHÂN (AGENTS)
# ==========================================

# Tác nhân 1: Gemini 3.1 Pro (Điều tra viên + Tự động Search)
investigator_model = genai.GenerativeModel(
    model_name='gemini-3.1-pro',
    tools='google_search_retrieval' 
)

# Tác nhân 2: Claude (Thẩm phán tối cao)
def ask_judge_claude(investigation_dossier):
    # --- MOCK CLAUDE (Chạy tạm khi chưa có API Key Claude thật) ---
    return f"""
    **Phán quyết (Giả lập): CẦN XÁC MINH THÊM**
    
    *Giải thích:* Dựa vào 'Hồ sơ chứng cứ' từ Gemini 3.1 Pro, tôi đã đọc qua các bằng chứng. (Vui lòng điền API Key thật của Claude vào mã nguồn để nhận phán quyết thực tế thay vì văn bản giả lập này).
    """
    
    # --- CODE THẬT (Bỏ comment khi đi thi) ---
    # message = judge_client.messages.create(
    #     model="claude-3-opus-20240229",
    #     max_tokens=1000,
    #     temperature=0,
    #     messages=[
    #         {
    #             "role": "user",
    #             "content": f"Ngươi là một Thẩm phán AI tối cao. Hãy đọc kỹ 'Hồ sơ chứng cứ' sau đây và đưa ra phán quyết cuối cùng (THẬT, GIẢ, hoặc XUYÊN TẠC). Giải thích ngắn gọn nhưng đanh thép. Hồ sơ: {investigation_dossier}"
    #         }
    #     ]
    # )
    # return message.content[0].text


# ==========================================
# 3. GIAO DIỆN STREAMLIT (UI)
# ==========================================
st.set_page_config(layout="wide", page_title="TruthGuard AI - Trạm kiểm chứng")
st.title("🛡️ TruthGuard AI")
st.caption("Công nghệ Multi-Agent xác minh tin giả qua Văn bản và Hình ảnh.")

# Sidebar - Bảng điều khiển nhập liệu
with st.sidebar:
    st.header("⚙️ Bảng Điều Khiển")
    text_input = st.text_area("1. Dán văn bản/link tin đồn vào đây:", height=150, placeholder="Ví dụ: Ăn chuối bất tử")
    image_file = st.file_uploader("2. Tải ảnh/Video lên (nếu có):", type=['png', 'jpg', 'jpeg', 'mp4'])
    
    verify_button = st.button("🔥 BẮT ĐẦU KIỂM CHỨNG", use_container_width=True)

# Main Content - Vùng hiển thị kết quả
st.subheader("📋 Báo Cáo Kiểm Chứng")

if verify_button and (text_input or image_file):
    with st.spinner("AI đang 'lùng sục' khắp Internet và suy luận..."):
        
        # ĐÂY LÀ ĐOẠN ĐÃ FIX LỖI (Khai báo biến trước)
        dossier = ""
        extracted_text = "" 
        
        # --- BƯỚC 1: XỬ LÝ HÌNH ẢNH (NẾU CÓ UP ẢNH) ---
        if image_file and image_file.type.startswith('image/'):
            st.write("🔍 Đang phân tích hình ảnh...")
            img = Image.open(image_file)
            
            image_prompt = """
            Ngươi là một chuyên gia điều tra kỹ thuật số. Hãy phân tích hình ảnh này.
            1. Tìm các dấu hiệu cho thấy đây có phải là ảnh do AI tạo (AI-generated) hay không.
            2. Trích xuất bất kỳ văn bản nào có trong hình ảnh này.
            """
            
            # Dùng Gemini 1.5 Pro cho ảnh để chạy nhanh và rẻ
            temp_image_model = genai.GenerativeModel('gemini-1.5-pro')
            image_analysis_response = temp_image_model.generate_content([image_prompt, img])
            
            # Trích xuất text từ ảnh (bắt lỗi nếu AI không bóc được text)
            if "Trích xuất" in image_analysis_response.text:
                try:
                    extracted_text = image_analysis_response.text.split("Trích xuất")[1].strip()
                except IndexError:
                    pass

            dossier += f"--- KẾT QUẢ ĐIỀU TRA HÌNH ẢNH ---\n{image_analysis_response.text}\n\n"
        
        # --- BƯỚC 2: XỬ LÝ VĂN BẢN VÀ LÊN MẠNG SEARCH ---
        if text_input or extracted_text:
            st.write("🔍 Đang kiểm chứng dữ liệu qua mạng lưới báo chí...")
            
            # Gộp cả text người dùng gõ và text bóc được từ ảnh
            text_to_check = f"{text_input} {extracted_text}".strip()
            
            text_prompt = f"""
            Ngươi là một Điều tra viên cao cấp. Hãy xem xét thông tin sau: '{text_to_check}'.
            1. Sử dụng Google Search để đối chiếu thông tin này với các báo đài, nguồn chính thống tại Việt Nam.
            2. Xâu chuỗi thông tin, phân tích tính đúng/sai.
            3. Lập thành một 'Hồ Sơ Chứng Cứ' khách quan và chi tiết.
            """
            
            # Gọi Gemini 3.1 Pro (có kết nối Google Search)
            text_analysis_response = investigator_model.generate_content(text_prompt)
            dossier += f"--- KẾT QUẢ ĐIỀU TRA VÀ TÌM KIẾM MẠNG ---\n{text_analysis_response.text}\n"
            
        # --- BƯỚC 3: CLAUDE PHÁN QUYẾT ---
        st.write("⚖️ 'Thẩm phán tối cao' Claude đang xem xét hồ sơ...")
        final_verdict = ask_judge_claude(dossier)
        
        # ==========================================
        # 4. HIỂN THỊ KẾT QUẢ RA MÀN HÌNH
        # ==========================================
        st.success("✅ Đã hoàn tất quá trình kiểm chứng!")
        st.divider()
        
        # Hiển thị kết luận của Claude
        st.markdown("### 📜 PHÁN QUYẾT CUỐI CÙNG")
        st.info(final_verdict)
        
        # Cho phép Giám khảo xem chi tiết "não" của Gemini hoạt động thế nào
        with st.expander("👁️ Mở xem 'Hồ sơ chứng cứ' chi tiết từ Gemini 3.1 Pro"):
            st.markdown(dossier)

else:
    st.info("Hãy nhập tin đồn hoặc tải file lên ở bảng điều khiển bên trái để bắt đầu.")
