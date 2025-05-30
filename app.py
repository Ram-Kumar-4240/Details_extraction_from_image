import streamlit as st
import cloudinary
import cloudinary.uploader
from groq import Groq
import fitz  # PyMuPDF
from PIL import Image
from io import BytesIO
import uuid
import time



# Cloudinary Configuration
cloudinary.config(
    cloud_name="dgojt5udn",
    api_key="635178667269684",
    api_secret="kBvCa2ROf5mMS4bTFeV4DGaeOos"
)

# Initialize Groq client
client = Groq(api_key="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")

def resize_image(image, max_size=800):
    width, height = image.size
    if max(width, height) > max_size:
        scale = max_size / max(width, height)
        return image.resize((int(width * scale), int(height * scale)), Image.LANCZOS)
    return image

def upload_image_to_cloudinary(image):
    try:
        image = resize_image(image)
        img_buffer = BytesIO()
        image.save(img_buffer, format="PNG")
        img_buffer.seek(0)
        result = cloudinary.uploader.upload(img_buffer)
        return result['secure_url']
    except Exception as e:
        st.error(f"❌ Upload failed: {e}")
        return None

def extract_passport_details(image_url):
    prompt = (
        "Extract the following details from this passport image:\n"
        "- SURNAME\n- FIRST NAME\n- PASSPORT NUMBER\n- NATIONALITY (full name, not abbreviation)\n"
        "- DATE OF BIRTH\n- DATE OF ISSUE\n- DATE OF EXPIRY\n- PLACE OF ISSUE\n"
        "- GENDER\n- ADDRESS\n- NOMINEE\n\n"
        "Return 'NOT AVAILABLE' if any detail is missing.\n"
        "Output all text in UPPERCASE.\n"
        "Format:\nSURNAME: P\nFIRST NAME: RAM\nPASSPORT NUMBER: XXXXXXXX\n..."
    )

    response = client.chat.completions.create(
        model="meta-llama/llama-4-maverick-17b-128e-instruct",
        messages=[
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]}
        ],
        temperature=0.2,
        max_completion_tokens=1024,
        top_p=1
    )

    return response.choices[0].message.content.upper()


def convert_pdf_to_images(pdf_file):
    try:
        pdf = fitz.open(stream=pdf_file.read(), filetype="pdf")
        return [Image.frombytes("RGB", [p.get_pixmap(dpi=200).width, p.get_pixmap(dpi=200).height],
                                p.get_pixmap(dpi=200).samples) for p in pdf]
    except Exception as e:
        st.error(f"❌ PDF Conversion failed: {e}")
        return []


def render_copy_button(value, key_suffix):
    html_code = f"""
        <div style="margin-top: 25px;">
            <button onclick="copyText_{key_suffix}()" 
                    style="background-color: #ff4b4b; color: white; border: none; 
                           padding: 6px 12px; border-radius: 4px; cursor: pointer;
                           font-size: 12px; font-weight: bold;">📋</button>
            <span id="status_{key_suffix}" style="margin-left: 5px; color: green; font-size: 12px;"></span>
        </div>
        <script>
            function copyText_{key_suffix}() {{
                var textarea = document.createElement('textarea');
                textarea.value = '{value.replace("'", "\\'")}';
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand('copy');
                document.body.removeChild(textarea);
                document.getElementById('status_{key_suffix}').innerText = '✅';
                setTimeout(() => {{
                    document.getElementById('status_{key_suffix}').innerText = '';
                }}, 1500);
            }}
        </script>
    """
    st.components.v1.html(html_code, height=60)


def display_extracted_fields(text, prefix=""):
    for line in text.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            key, value = key.strip(), value.strip()
            col1, col2 = st.columns([4, 1])
            with col1:
                st.text_input(label=key, value=value, key=f"{prefix}_{key}_{uuid.uuid4()}")
            with col2:
                render_copy_button(value, f"{prefix}_{key}_{uuid.uuid4()}")


# ------------------------- MAIN APP -------------------------
def main():
    st.set_page_config(page_title="Passport Detail Extractor", layout="wide")
    st.title("📸 Passport Image/PDF Detail Extractor")
    st.markdown("Upload an image or PDF containing passport details. We'll extract key information using AI.")

    uploaded_file = st.file_uploader("Upload PNG, JPG, JPEG, or PDF", type=["png", "jpg", "jpeg", "pdf"])

    if uploaded_file:
        if uploaded_file.type == "application/pdf":
            st.info("📄 PDF detected! Extracting all pages...")
            images = convert_pdf_to_images(uploaded_file)
            if not images:
                return

            for i, image in enumerate(images):
                with st.status(f"🔄 Processing page {i + 1}...", expanded=False) as status:
                    image_url = upload_image_to_cloudinary(image)
                    if image_url:
                        col1, col2 = st.columns([1, 2])
                        with col1:
                            st.image(image, caption=f"📌 Page {i + 1}", use_container_width=True)
                        with col2:
                            st.subheader("🔍 Extracted Details")
                            extracted_text = extract_passport_details(image_url)
                            display_extracted_fields(extracted_text, f"page_{i}")
                        status.update(label="✅ Page Processed!", state="complete")

        else:
            image = Image.open(uploaded_file)
            with st.status("🔄 Processing image...", expanded=False) as status:
                image_url = upload_image_to_cloudinary(image)
                if image_url:
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.image(image, caption="📌 Uploaded Image", use_container_width=True)
                        st.caption("✅ Uploaded to Cloudinary")
                    with col2:
                        st.subheader("🔍 Extracted Details")
                        extracted_text = extract_passport_details(image_url)
                        display_extracted_fields(extracted_text, "image")
                    status.update(label="✅ Image Processed!", state="complete")


if __name__ == "__main__":
    main()
