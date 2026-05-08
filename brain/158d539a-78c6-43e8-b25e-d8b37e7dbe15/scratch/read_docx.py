import docx
import sys
import io

# Set stdout to handle utf-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

try:
    doc = docx.Document("d:/Ideal_trendzzz_visuals/ideal_visualizer_proj/Ai Powered Interior Design Copilot Humanized Document (1).docx")
    text = "\n".join([para.text for para in doc.paragraphs])
    print(text)
except Exception as e:
    print(f"Error: {e}")
