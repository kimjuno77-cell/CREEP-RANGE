import PyPDF2
import sys

def check_pdf(pdf_path):
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            num_pages = len(reader.pages)
            print(f"Total pages: {num_pages}")
            
            for i in range(min(3, num_pages)):
                page = reader.pages[i]
                text = page.extract_text()
                print(f"--- Page {i + 1} ---")
                print(text[:1000])
                print("\n" + "="*40 + "\n")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    pdf_path = "API 579-2_Example.pdf"
    check_pdf(pdf_path)
