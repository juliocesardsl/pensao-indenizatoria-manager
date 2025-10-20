from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
import os


def draw_header(c: canvas.Canvas, width: float, height: float, logo_path: str = None, title_lines=None):
    """Desenha um cabeçalho padrão no topo da página.

    - c: objeto canvas do reportlab
    - width, height: dimensões da página (por exemplo, letter)
    - logo_path: caminho opcional para a imagem do brasão (será desenhada à esquerda)
    - title_lines: lista de strings para centralizar (cada item em uma linha)

    A função deixa o cursor vertical alguns centímetros abaixo do topo para o conteúdo.
    Retorna a y_offset (float) que indica a posição vertical logo abaixo do cabeçalho,
    útil para posicionar o restante do conteúdo.
    """
    if title_lines is None:
        title_lines = []

    top_margin = 1 * cm
    logo_max_height = 1.2 * cm
    logo_max_width = 3 * cm

    # Posições
    y_top = height - top_margin

    # Isolar estado gráfico para evitar que transformações ou cores
    # previamente definidas no canvas escondam o cabeçalho.
    c.saveState()
    try:
        # Forçar cor preta (preencher e traço) para garantir visibilidade
        try:
            c.setFillColorRGB(0, 0, 0)
        except Exception:
            # alguns objetos canvas podem usar setFillColor
            try:
                c.setFillColor((0, 0, 0))
            except Exception:
                pass
        try:
            c.setStrokeColorRGB(0, 0, 0)
        except Exception:
            try:
                c.setStrokeColor((0, 0, 0))
            except Exception:
                pass

        # Draw logo if provided and exists
        if logo_path and os.path.exists(logo_path):
            try:
                img = ImageReader(logo_path)
                iw, ih = img.getSize()
                aspect = ih / float(iw) if iw else 1.0
                draw_h = min(logo_max_height, ih)
                # compute width keeping aspect
                draw_w = min(logo_max_width, draw_h / aspect) if aspect != 0 else logo_max_width
                # draw at left (1cm from left edge). y_top is top reference; shift down by draw_h
                c.drawImage(img, 1*cm, y_top - draw_h, width=draw_w, height=draw_h, preserveAspectRatio=True, mask='auto')
            except Exception:
                # se falhar, continuamos sem o logo
                pass

        # Texto centralizado (cada linha abaixo da outra)
        current_y = y_top - 0.2*cm
        for i, line in enumerate(title_lines):
            # Diminuir fonte levemente para linhas adicionais
            if i == 0:
                c.setFont("Helvetica-Bold", 12)
            else:
                c.setFont("Helvetica-Bold", 10)
            # garantir que a string seja str (evitar None)
            if line is None:
                line = ''
            c.drawCentredString(width / 2.0, current_y, str(line))
            current_y -= 0.5*cm

        # Linha separadora abaixo do cabeçalho
        c.setLineWidth(0.5)
        c.line(1*cm, current_y + 0.2*cm, width - 1*cm, current_y + 0.2*cm)

        # Retorna posição vertical para começar o conteúdo (um espaço após a linha)
        return_y = current_y - 0.2*cm
    finally:
        c.restoreState()

    return return_y


def default_titles():
    return [
        "Governo do Distrito Federal",
        "Secretaria de Estado de Economia do Distrito Federal",
        "Gerência de Aposentadoria e Pensões Indenizatórias"
    ]
