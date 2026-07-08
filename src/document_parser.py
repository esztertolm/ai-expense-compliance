from pypdf import PdfReader
import io
import base64


def extract_text_from_pdf(uploaded_file):
    """Extracts raw text from a Streamlit uploaded PDF file."""
    try:
        # We use io.BytesIO to read the uploaded file from memory
        pdf_reader = PdfReader(io.BytesIO(uploaded_file.getvalue()))
        text = ""
        for page in pdf_reader.pages:
            # Extract text from each page and append it
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        return text
    except Exception as e:
        return f"Error reading PDF: {str(e)}"
    

def encode_image_to_base64(uploaded_file):
    """Converts a Streamlit uploaded image file into a Base64 string for the Vision API."""
    return base64.b64encode(uploaded_file.read()).decode("utf-8")