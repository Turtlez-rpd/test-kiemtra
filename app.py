import streamlit as st
import google.generativeai as genai
import anthropic # Thư viện Claude (Giả định bạn đã có API Key)
import os
from PIL import Image

# 1. Cấu hình các API Key bảo mật (Trong file .env)
# genai.configure(api_key=os.environ["GEMINI_API_KEY"])
# CLAUDE_API_KEY = os.environ["CLAUDE_API_KEY"]
# judge_client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

# --- GIẢ GIÁ ĐỂ CHẠY THỬ (DÁN KEY THẬT CỦA BẠN VÀO ĐÂY) ---
genai.configure(api_key="PASTE_YOUR_GEMINI_API_KEY_HERE")
# CLAUDE_API_KEY = "PASTE_YOUR_CLAUDE_API_KEY_HERE"
# judge_client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
# --- XÓA CỤC GIẢ GIÁ KHI ĐI THI ---

# 2. Định nghĩa các Tác nhân (Agents)

# Tác nhân 1: The Investigator (Gemini 3.1 Pro)
# Dùng cho các vụ án văn bản và suy luận sâu sau khi có search
investigator_model = genai.GenerativeModel(
    model_name='gemini-3.1-pro',
    tools='google_search_retrieval' # Bật tính năng search
)

# Tác nhân 2: The Judge (Claude - Năng lực phán xét)
def ask_judge_claude(investigation_dossier):
    # --- MOCK CLAUDE (Dùng khi chưa có key, dán code thật vào sau) ---
    print("\n--- Gọi API Claude ---")
    mock_claude_response = f"""
        (Claude giả lập) Phán quyết: THẬT.
        Giải thích: Dựa vào 'Hồ sơ chứng cứ' từ Gemini 3.1 Pro, tôi thấy các trang báo chính thống tại Việt Nam như vtv.vn, tuoitre.vn đều đồng loạt đưa tin về sự kiện này. Mốc thời gian và các chi tiết cốt lõi đều trùng khớp, không có dấu hiệu ngụy biện.
        """
    return mock_claude_response
    # --- END MOCK CLAUDE ---
    
    # --- Code thật để đi thi (Khi có key, hãy bỏ comment) ---
    # message = judge_client.messages.create(
    #     model="claude-3-opus-20240229",
    #        max_tokens=1000,
    #        temperature=0,
    #        messages=[
    #            {
    #                "role": "user",
    #                "content": [
    #                    {
    #                        "type": "text",
    #                        "text": f"Ngươi là một Thẩm phán AI tối cao. Hãy đọc kỹ 'Hồ sơ chứng cứ' sau đây và đưa ra phán quyết cuối cùng (THẬT, GIẢ, hoặc XUYÊN TẠC). Giải thích ngắn gọn nhưng đanh thép. {investigation_dossier}"
    #                    }
    #                ]
    #            }
    #        ]
    #    )
    # return message.content[0].text
    # --- END CODE THẬT ---

# 3. Giao diện Streamlit (Sửa lại layout cho đẹp)

st.set_page_config(layout="wide", page_title="TruthGuard AI - Trạm kiểm chứng")
st.title("🛡️ TruthGuard AI")
st.caption("Công nghệ Multi-Agent xác minh tin giả qua Văn bản và Hình ảnh.")

# Sidebar - Điều khiển
with st.sidebar:
    st.header("⚙️ Bảng Điều Khiển")
    text_input = st.text_area("1. Dán văn bản/link tin đồn vào đây:", height=150, placeholder="Ví dụ: Ăn chuối bất tử")
    image_file = st.file_uploader("2. Tải ảnh/Video lên (nếu có):", type=['png', 'jpg', 'jpeg', 'mp4'])
    
    verify_button = st.button("🔥 BẮT ĐẦU KIỂM CHỨNG", use_container_width=True)

# Main Content - Hiển thị kết quả
st.subheader("📋 Báo Cáo Kiểm Chứng")

if verify_button and (text_input or image_file):
    with st.spinner("AI đang 'lùng sục' khắp Internet và suy luận..."):
        
        # --- PHASE 1: Thu thập & Phân tích (Dùng Gemini 3.1 Pro) ---
        dossier = ""
        
        # 1. Xử lý ảnh (Phân tích AI-gen, bóc text)
        if image_file and image_file.type.startswith('image/'):
            st.write("🔍 Đang phân tích hình ảnh...")
            img = Image.open(image_file)
            
            # Câu prompt yêu cầu Gemini thực hiện "Deep Thinking"
            image_prompt = """
            Ngươi là một chuyên gia điều tra kỹ thuật số. Hãy phân tích hình ảnh này.
            1. Tìm các dấu hiệu hình ảnh cho thấy đây có phải là ảnh do AI tạo (AI-generated) hay không (ví dụ: lỗi ngón tay, cấu trúc da, ánh sáng phi lý). Hãy giải thích chi tiết các bằng chứng tìm được.
            2. Trích xuất bất kỳ văn bản nào có trong hình ảnh này.
            """
            
            # Phân tích ảnh không cần search
            # image_analysis_model = genai.GenerativeModel('gemini-1.5-pro') # Dùng con pro cho ảnh, ko cần search
            # image_analysis_response = image_analysis_model.generate_content([image_prompt, img])
            
            # --- Tạm thời dùng Gemini 1.5 Pro cho ảnh để tiết kiệm quota của con 3.1 Pro mới ---
            temp_image_model = genai.GenerativeModel('gemini-1.5-pro')
            image_analysis_response = temp_image_model.generate_content([image_prompt, img])
            
            # Lấy text trong ảnh ra (bóc tách đơn giản cho demo)
            extracted_text = ""
            if "Trích xuất bất kỳ văn bản nào" in image_analysis_response.text:
                 extracted_text = image_analysis_response.text.split("Trích xuất bất kỳ văn bản nào có trong hình ảnh này.")[1].strip()

            dossier += f"--- Kết quả điều tra hình ảnh ---\n{image_analysis_response.text}\n"
            if extracted_text:
                dossier += f"Văn bản bóc được từ ảnh: '{extracted_text}'\n"
        
        # 2. Xử lý văn bản (Kiểm chứng sự kiện)
        if text_input or (image_file and image_file.type.startswith('image/') and extracted_text):
            st.write("🔍 Đang kiểm chứng văn bản qua Google Search...")
            text_to_check = text_input + " " + extracted_text # Kết hợp text input và text trong ảnh
            
            text_prompt = f"""
            Ngươi là một Điều tra viên cao cấp. Hãy xem xét [Hình ảnh/Video/Văn bản] này. Hãy trích xuất các tuyên bố đáng ngờ. Sau đó, tự động sử dụng Google Search để tìm kiếm các bằng chứng liên quan từ các trang web chính thống tại Việt Nam (như chính phủ, báo đài quốc gia, các nguồn quốc tế uy tín). Hãy xâu chuỗi thông tin, phân tích tính đúng sai của các tuyên bố dựa trên những gì tìm được, và lập thành một 'Hồ Sơ Chứng Cứ' khách quan, chi tiết nhất. Thông tin cần check: '{text_to_check}'
            """
            
            # Gọi API Gemini 3.1 Pro có search
            text_analysis_response = investigator_model.generate_content(text_prompt)
            dossier += f"--- Kết quả điều tra văn bản ---\n{text_analysis_response.text}\n"
            
        # --- PHASE 2: Phán quyết (Chuyển sang Claude) ---
        st.write("⚖️ 'Thẩm phán tối cao' Claude đang xem xét hồ sơ...")
        final_verdict = ask_judge_claude(dossier)
        
        # --- PHASE 3: Hiển thị (Display) ---
        st.write("✅ Đã có phán quyết!")
        
        st.divider()
        st.write(final_verdict)
        
        with st.expander("👁️ Xem chi tiết 'Hồ sơ chứng cứ' (Dữ liệu từ Gemini 3.1 Pro)"):
            st.text(dossier)

else:
    st.info("Hãy nhập tin đồn hoặc tải file lên ở bảng điều khiển bên trái để bắt đầu.")
