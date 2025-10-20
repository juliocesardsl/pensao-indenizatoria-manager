from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from pdf_utils import draw_header, default_titles
import os

out = os.path.join(os.path.dirname(__file__), 'test_header_output.pdf')

c = canvas.Canvas(out, pagesize=letter)
width, height = letter

# draw header
y = draw_header(c, width, height, logo_path=os.path.join(os.path.dirname(__file__), 'Brasão_do_Distrito_Federal_Brasil.png'), title_lines=default_titles())

# sample content
c.setFont('Helvetica', 10)
c.drawString(2*72, y, 'Linha de teste abaixo do cabeçalho')

c.save()
print('Generated', out)
