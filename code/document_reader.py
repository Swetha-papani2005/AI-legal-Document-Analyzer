import os
from PyPDF2 import PdfReader
import pytesseract
import pypdfium2

# ✅ Set Tesseract path
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

class DocumentReader:
    def __init__(self, input_folder, output_folder):
        self.input_folder = input_folder
        self.output_folder = output_folder

    # ✅ Detect if PDF already has text (not scanned)
    def is_scanned_pdf(self, file_path):
        try:
            reader = PdfReader(file_path)
            for page in reader.pages:
                if page.extract_text():
                    return False
            return True
        except:
            return True

    # ✅ Extract text (digital or scanned)
    def extract_text(self, file_name):
        file_path = os.path.join(self.input_folder, file_name)
        output_path = os.path.join(self.output_folder, file_name.replace(".pdf", ".txt"))

        if self.is_scanned_pdf(file_path):
            print(f"🔍 Scanned PDF detected: {file_name} — Running OCR...")
            text = self.extract_text_with_ocr(file_path)
        else:
            print(f"📄 Digital PDF detected: {file_name} — Extracting text...")
            text = self.extract_text_from_pdf(file_path)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)

        print(f"✅ Extracted text saved to {output_path}\n")

    # ✅ Extract text from digital PDF
    def extract_text_from_pdf(self, file_path):
        text = ""
        reader = PdfReader(file_path)
        for page in reader.pages:
            text += page.extract_text() or ""
        return text

    # ✅ OCR for scanned PDFs (NO POPPLER)
    def extract_text_with_ocr(self, file_path):
        text = ""
        try:
            pdf = pypdfium2.PdfDocument(file_path)
            for i in range(len(pdf)):
                page = pdf.get_page(i)
                img = page.render(scale=3).to_pil()  # high resolution for accuracy
                text += pytesseract.image_to_string(img, lang="eng")
                page.close()
            pdf.close()
        except Exception as e:
            print(f"❌ OCR failed: {e}")
        return text.strip()


# ✅ Script run mode
if __name__ == "__main__":
    input_folder = "../data/raw documents"
    output_folder = "../data/extracted text"

    os.makedirs(output_folder, exist_ok=True)
    reader = DocumentReader(input_folder, output_folder)

    for file in os.listdir(input_folder):
        if file.lower().endswith(".pdf"):
            reader.extract_text(file)

    print("🏁 Completed OCR/Text Extraction!")
