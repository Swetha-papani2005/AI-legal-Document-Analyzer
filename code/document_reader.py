import os
from PyPDF2 import PdfReader
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import platform

# ✅ Set Windows Tesseract path only if running locally (not on Streamlit Cloud)
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

class DocumentReader:
    def __init__(self, input_folder, output_folder):
        self.input_folder = input_folder
        self.output_folder = output_folder

    def is_scanned_pdf(self, file_path):
        """Check if the PDF is scanned (no digital text)."""
        try:
            reader = PdfReader(file_path)
            for page in reader.pages:
                if page.extract_text():
                    return False  # text exists — not scanned
            return True
        except:
            return True  # If PDF can't be read, treat as scanned

    def extract_text(self, file_name):
        """Extract text from PDF — OCR if needed."""
        file_path = os.path.join(self.input_folder, file_name)
        output_path = os.path.join(self.output_folder, file_name.replace(".pdf", ".txt"))

        if self.is_scanned_pdf(file_path):
            print(f"🔍 Scanned PDF detected — using OCR on: {file_name}")
            text = self.extract_text_with_ocr(file_path)
        else:
            print(f"📄 Digital PDF detected — extracting directly: {file_name}")
            text = self.extract_text_from_pdf(file_path)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)

        print(f"✅ Extracted text saved to {output_path}\n")

    def extract_text_from_pdf(self, file_path):
        """Extract text from normal text PDF."""
        text = ""
        reader = PdfReader(file_path)
        for page in reader.pages:
            text += page.extract_text() or ""
        return text

    def extract_text_with_ocr(self, file_path):
        """OCR for scanned PDF using Tesseract."""
        text = ""
        try:
            images = convert_from_path(file_path, dpi=300)
            for i, img in enumerate(images):
                print(f"🖼 OCR processing page {i + 1}...")
                text += pytesseract.image_to_string(img, lang="eng")
        except Exception as e:
            print(f"❌ OCR failed: {e}")

        return text.strip()


if __name__ == "__main__":
    input_folder = "../data/raw documents"
    output_folder = "../data/extracted text"

    os.makedirs(output_folder, exist_ok=True)
    reader = DocumentReader(input_folder, output_folder)

    for file in os.listdir(input_folder):
        if file.endswith(".pdf"):
            reader.extract_text(file)

    print("🏁 OCR/Text Extraction Completed")
