import streamlit as st
import cloudinary
import cloudinary.uploader
from groq import Groq
import fitz  # PyMuPDF
from PIL import Image
from io import BytesIO
import uuid


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
        scaling_factor = max_size / max(width, height)
        new_size = (int(width * scaling_factor), int(height * scaling_factor))
        return image.resize(new_size, Image.LANCZOS)
    return image

def upload_image(image):
    try:
        image = resize_image(image)
        img_bytes = BytesIO()
        image.save(img_bytes, format="PNG")
        img_bytes.seek(0)
        response = cloudinary.uploader.upload(img_bytes)
        return response['secure_url']
    except Exception as e:
        st.error(f"⚠️ Error uploading image: {e}")
        return None

def extract_text_from_image(image_url):
    prompt_text = (
        "Extract the following details from this passport image:\n"
        "- FULL NAME\n"
        "- PASSPORT NUMBER\n"
        "- NATIONALITY (provide full country name, not abbreviation - e.g., AUSTRALIA not AUS)\n"
        "- DATE OF BIRTH\n"
        "- DATE OF ISSUE\n"
        "- DATE OF EXPIRY\n"
        "- PLACE OF ISSUE\n"
        "- GENDER\n"
        "- ADDRESS\n\n"
        "If any of these details are missing, return 'NOT AVAILABLE'.\n"
        "Ensure all extracted text is in UPPERCASE.\n"
        "For NATIONALITY, always provide the full country name (AUSTRALIA, UNITED STATES, UNITED KINGDOM, etc.) not the 3-letter code.\n"
        "Return format:\nFULL NAME: LUTFONESSA\nPASSPORT NUMBER: XXXXXXXX\nNATIONALITY: AUSTRALIA\n..."
    )

    response = client.chat.completions.create(
        model="meta-llama/llama-4-maverick-17b-128e-instruct",
        messages=[
            {"role": "user", "content": [
                {"type": "text", "text": prompt_text},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]}
        ],
        temperature=0.2,
        max_completion_tokens=1024,
        top_p=1,
        stream=False
    )

    return response.choices[0].message.content.upper()

def convert_pdf_to_images(pdf_file):
    try:
        pdf_document = fitz.open(stream=pdf_file.read(), filetype="pdf")
        images = []
        for page in pdf_document:
            pix = page.get_pixmap(dpi=200)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            images.append(img)
        return images
    except Exception as e:
        st.error(f"⚠️ Error converting PDF: {e}")
        return []

def display_extracted_values(extracted_text, unique_prefix=""):
    lines = extracted_text.splitlines()
    for line in lines:
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if value:
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    unique_key = f"{unique_prefix}_{key}_{uuid.uuid4()}"
                    st.text_input(label=key, value=value, key=unique_key)
                
                with col2:
                    st.write("")  # Empty space to align with text input
                    copy_button_key = f"{unique_prefix}_copy_{key}_{uuid.uuid4()}"
                    
                    # Simpler HTML with better JavaScript
                    copy_html = f"""
                    <div style="margin-top: 25px;">
                        <button onclick="copyText()" 
                                style="background-color: #ff4b4b; color: white; border: none; 
                                       padding: 6px 12px; border-radius: 4px; cursor: pointer;
                                       font-size: 12px; font-weight: bold;">
                            📋
                        </button>
                        <span id="copyStatus" style="margin-left: 5px; color: green; font-size: 12px;"></span>
                    </div>
                    
                    <script>
                        function copyText() {{
                            // Create a temporary textarea element
                            var textarea = document.createElement('textarea');
                            textarea.value = '{value.replace("'", "\\'")}';
                            document.body.appendChild(textarea);
                            textarea.select();
                            textarea.setSelectionRange(0, 99999); // For mobile devices
                            
                            try {{
                                var successful = document.execCommand('copy');
                                if (successful) {{
                                    document.getElementById('copyStatus').innerHTML = '✅';
                                    setTimeout(function() {{
                                        document.getElementById('copyStatus').innerHTML = '';
                                    }}, 1500);
                                }}
                            }} catch (err) {{
                                console.error('Copy failed:', err);
                            }}
                            
                            document.body.removeChild(textarea);
                        }}
                    </script>
                    """
                    
                    st.components.v1.html(copy_html, height=60)

def main():
    st.set_page_config(layout="wide")
    st.title("📸 Image & PDF Detail Extractor")

    uploaded_file = st.file_uploader("Upload an image or PDF", type=["png", "jpg", "jpeg", "pdf"])

    if uploaded_file:
        if uploaded_file.type == "application/pdf":
            st.info("📄 PDF detected! Extracting all pages...")
            images = convert_pdf_to_images(uploaded_file)
            if not images:
                return

            for idx, image in enumerate(images):
                with st.status(f"Processing page {idx + 1}...", expanded=False) as status:
                    image_url = upload_image(image)
                    if image_url:
                        col1, col2 = st.columns([1, 2])

                        with col1:
                            st.image(image, caption=f"📌 Page {idx + 1}", use_container_width=True)

                        extracted_text = extract_text_from_image(image_url)

                        with col2:
                            st.subheader("🔍 Extracted Details")
                            display_extracted_values(extracted_text, f"page_{idx}")

                        status.update(label="✅ Done!", state="complete")

        else:
            image = Image.open(uploaded_file)

            with st.status("Processing image... Please wait.", expanded=False) as status:
                image_url = upload_image(image)
                if image_url:
                    col1, col2 = st.columns([1, 2])

                    with col1:
                        st.image(image, caption="📌 Uploaded Image", use_container_width=True)
                        st.caption("✅ Uploaded to Cloudinary")

                    extracted_text = extract_text_from_image(image_url)

                    with col2:
                        st.subheader("🔍 Extracted Details")
                        display_extracted_values(extracted_text, "single_image")

                    status.update(label="✅ Processing complete!", state="complete")

if __name__ == "__main__":
    main()