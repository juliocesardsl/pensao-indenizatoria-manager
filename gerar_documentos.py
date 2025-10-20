import sqlite3
import os
import sys
import tkinter as tk
from tkinter import messagebox
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.lib import colors
from reportlab.lib.units import cm, inch
from reportlab.pdfgen import canvas
from pdf_utils import draw_header, default_titles
from datetime import datetime
import locale

# Configura o locale para português do Brasil para formatar a data
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil.1252')
    except locale.Error:
        print("Locale pt_BR não encontrado, usando o padrão do sistema.")

# ================================================================================================= #
# FUNÇÃO AUXILIAR PARA CAMINHOS DE ARQUIVOS (PARA O EXECUTÁVEL)
# ================================================================================================= #
def resource_path(relative_path):
    """ Obtém o caminho absoluto para o recurso, funciona para dev e para PyInstaller """
    try:
        # PyInstaller cria uma pasta temp e armazena o caminho em _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def gerar_documento_empenho(mes_inicial, mes_final, save_path):
    """
    Gera um documento PDF com o Resumo de Despesa Pessoal, seguindo o modelo fornecido.
    """
    conn = None
    try:
        ref_inicial_fmt = f"{mes_inicial[3:7]}/{mes_inicial[0:2]}"
        ref_final_fmt = f"{mes_final[3:7]}/{mes_final[0:2]}"

        conn = sqlite3.connect(resource_path('banco.db')) 
        cursor = conn.cursor()

        cursor.execute("""
            SELECT SUM(valor), SUM(valor_um_terco_ferias), SUM(valor_13_salario)
            FROM
                pagamento_gerados
            WHERE
                (SUBSTR(mes_referencia, 4, 4) || '/' || SUBSTR(mes_referencia, 1, 2)) BETWEEN ? AND ?
        """, (ref_inicial_fmt, ref_final_fmt))

        dados_agregados = cursor.fetchone()

        if not dados_agregados or dados_agregados[0] is None:
            messagebox.showinfo("Sem Dados", f"Nenhum pagamento encontrado no período de {mes_inicial} a {mes_final}.")
            return "NO_DATA"

        # Query 2: Buscar os dados detalhados para o anexo
        cursor.execute("""
            SELECT
                pg.nome_beneficiario, pg.valor, b.cpf, b.menor_ou_incapaz,
                b.agencia, b.numero_conta, b.numero_banco, b.tipo_conta,
                rl.nome_completo, rl.cpf, rl.agencia, rl.numero_conta, rl.numero_banco, rl.tipo_conta
            FROM pagamento_gerados pg
            JOIN beneficiarios b ON pg.beneficiario_id = b.id
            LEFT JOIN representantes_legais rl ON b.cpf = rl.cpf_beneficiario
            WHERE (SUBSTR(pg.mes_referencia, 4, 4) || '/' || SUBSTR(pg.mes_referencia, 1, 2)) BETWEEN ? AND ?
            ORDER BY pg.nome_beneficiario
        """, (ref_inicial_fmt, ref_final_fmt))
        pagamentos_detalhados = cursor.fetchall()

        total_bruto, total_ferias, total_13 = [val or 0.0 for val in dados_agregados]
        total_outros = total_bruto - (total_ferias + total_13)
        total_descontos = 0.0 # O sistema não calcula descontos atualmente
        total_liquido = total_bruto - total_descontos

        def format_value(value):
            return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        nome_arquivo = f"Documento_Empenho_{mes_inicial.replace('/', '-')}_a_{mes_final.replace('/', '-')}.pdf"
        caminho_completo = os.path.join(save_path, nome_arquivo)
        doc = SimpleDocTemplate(caminho_completo, pagesize=letter, topMargin=3*cm, bottomMargin=1*cm, leftMargin=1*cm, rightMargin=1*cm)
        
        styles = getSampleStyleSheet()
        style_center_bold = ParagraphStyle(name='CenterBold', parent=styles['Normal'], alignment=TA_CENTER, fontName='Helvetica-Bold')
        style_center = ParagraphStyle(name='Center', parent=styles['Normal'], alignment=TA_CENTER)
        style_left = ParagraphStyle(name='Left', parent=styles['Normal'], alignment=TA_LEFT)
        style_right = ParagraphStyle(name='Right', parent=styles['Normal'], alignment=TA_RIGHT)
        style_right_bold = ParagraphStyle(name='RightBold', parent=styles['Normal'], alignment=TA_RIGHT, fontName='Helvetica-Bold')

        story = []

        # Cabeçalho
        header_data = [
            [Paragraph("RESUMO DE DESPESA PESSOAL E ENCARGOS SOCIAIS", style_center_bold)]
        ]
        story.append(Table(header_data, colWidths=[19*cm]))
        story.append(Spacer(1, 0.5*cm))

        # Informações da Folha
        mes_competencia = mes_inicial if mes_inicial == mes_final else f"{mes_inicial} a {mes_final}"
        info_data = [
            [Paragraph("UNIDADE: SEEC", style_left), Paragraph(f"MÊS DE COMPETÊNCIA: {mes_competencia}", style_center),],
            [Paragraph("46 – PENSÃO INDENIZATORIA", style_left), Paragraph(f"MÊS DE APROPRIAÇÃO: {mes_competencia}", style_center),]
        ]
        story.append(Table(info_data, colWidths=[6.3*cm, 6.4*cm, 6.3*cm]))
        story.append(Spacer(1, 0.5*cm))

        # Valores Resumidos
        valores_resumo_data = [
            [Paragraph("VALOR BRUTO", style_left), Paragraph(f"R$ {format_value(total_bruto)}", style_right_bold)],
            [Paragraph("SALDO A EMPENHAR", style_left), Paragraph(f"R$ {format_value(total_liquido)}", style_right_bold)],
            [Paragraph("VALOR A LIBERAR", style_left), Paragraph(f"R$ {format_value(total_liquido)}", style_right_bold)]
        ]
        story.append(Table(valores_resumo_data, colWidths=[15*cm, 4*cm]))
        story.append(Spacer(1, 0.5*cm))

        # Título movido para cima, conforme solicitado
        story.append(Paragraph("DEMONSTRATIVO DE APROPRIAÇÃO DA DESPESA", style_center_bold))
        story.append(Spacer(1, 0.5*cm))

        # Tabelas de Elementos
        elementos_data = [
            [Paragraph("<b>ELEMENTO</b>", style_center), Paragraph("<b>VALOR</b>", style_center), Paragraph("<b>FTE</b>", style_center)],
            
            ["339014/93", format_value(total_liquido), "100"],
            ["339018/19/48", "0,00", "0"],
            ["339033/49",    "0,00", "0"],
            ["339036",       "0,00", "0"],
            ["339046/47",    "0,00", "0"],
            ["339091/92",    "0,00", "0"]
        ]
        # Largura da coluna FTE ajustada para 1.5cm para evitar quebra de linha
        tabela_elementos = Table(elementos_data, colWidths=[2.5*cm, 2*cm, 1.5*cm] * 3, hAlign='CENTER')
        tabela_elementos.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(tabela_elementos)
        story.append(Spacer(1, 1*cm))

        # Tabela unificada de Detalhamento, Totais e Responsável
        story.append(Paragraph("DETALHAMENTO DA FOLHA DE PAGAMENTO", style_center))
        story.append(Spacer(1, 0.5*cm))

        # --- Célula [0,0]: Detalhes da folha ---
        detalhes_content = [
            [Paragraph("VALOR DO PAGAMENTO", style_left), Paragraph(format_value(total_outros), style_right)],
            [Paragraph("FÉRIAS", style_left), Paragraph(format_value(total_ferias), style_right)],
            [Paragraph("DECIMO TERCEIRO", style_left), Paragraph(format_value(total_13), style_right)],
            # [Paragraph("PAGAMENTO ATRASADO", style_left), Paragraph("0,00", style_right)],
        ]
        detalhes_table = Table(detalhes_content, colWidths=[6.5*cm, 2.5*cm])

        # --- Célula [0,1]: Pagamento indevido ---
        # indevido_content = [[Paragraph("PAGAMENTO INDEVIDO", style_left), Paragraph("0,00", style_right)]]
        # indevido_table = Table(indevido_content, colWidths=[6.5*cm, 2.5*cm])

        # --- Célula [1,0]: Total Bruto ---
        bruto_table = Table([[Paragraph("<b>TOTAL BRUTO</b>", style_center)], [Paragraph(format_value(total_bruto), style_center)]], colWidths=[9*cm])

        # --- Célula [1,1]: Descontos e Líquido ---
        descontos_liquido_content = [
            [Paragraph("<b>TOTAL DE DESCONTOS</b>", style_center), Paragraph("<b>TOTAL LÍQUIDO</b>", style_center)],
            [Paragraph(format_value(total_descontos), style_center), Paragraph(format_value(total_liquido), style_center)]
        ]
        descontos_liquido_table = Table(descontos_liquido_content, colWidths=[4.5*cm, 4.5*cm])

        # --- Célula [2,0] (mesclada): Responsável e Telefone ---
        responsavel_table = Table([[Paragraph("RESPONSÁVEL:", style_left), Paragraph("TELEFONE:", style_right)]], colWidths=[9.5*cm, 9.5*cm])

        # --- Montagem da tabela principal ---
        tabela_principal_data = [
            [detalhes_table],
            [bruto_table, descontos_liquido_table],
            [responsavel_table, '']
        ]
        tabela_principal = Table(tabela_principal_data, colWidths=[9.5*cm, 9.5*cm], rowHeights=[3*cm, 2*cm, 1*cm])
        tabela_principal.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('SPAN', (0,2), (1,2)), # Mescla a última linha
            ('VALIGN', (0,2), (0,2), 'MIDDLE'),
        ]))
        story.append(tabela_principal)

        # --- ANEXO COM DETALHAMENTO ---
        if pagamentos_detalhados:
            story.append(PageBreak())

            # Estilos específicos para o anexo com fonte menor
            style_anexo_header = ParagraphStyle(name='AnexoHeader', parent=styles['Normal'], alignment=TA_CENTER, fontName='Helvetica-Bold', fontSize=7)
            style_anexo_left = ParagraphStyle(name='AnexoLeft', parent=styles['Normal'], alignment=TA_LEFT, fontSize=7)
            style_anexo_center = ParagraphStyle(name='AnexoCenter', parent=styles['Normal'], alignment=TA_CENTER, fontSize=7)
            style_anexo_right = ParagraphStyle(name='AnexoRight', parent=styles['Normal'], alignment=TA_RIGHT, fontSize=7)

            # Título do anexo
            story.append(Paragraph("ANEXO - DETALHAMENTO PARA CRÉDITO EM CONTA", style_center_bold))
            story.append(Spacer(1, 0.5*cm))

            # Montagem da tabela de detalhes
            dados_detalhes = []
            header_detalhes = [
                Paragraph("<b>Beneficiário da Pensão</b>", style_anexo_header),
                Paragraph("<b>CPF</b>", style_anexo_header),
                Paragraph("<b>Responsável Legal</b>", style_anexo_header),
                Paragraph("<b>Banco</b>", style_anexo_header),
                Paragraph("<b>Agência</b>", style_anexo_header),
                Paragraph("<b>Conta</b>", style_anexo_header),
                Paragraph("<b>Tipo Conta</b>", style_anexo_header),
                Paragraph("<b>Valor (R$)</b>", style_anexo_header)
            ]
            dados_detalhes.append(header_detalhes)

            for p in pagamentos_detalhados:
                (nome_beneficiario, valor, cpf_ben, menor, ag_ben, conta_ben, banco_ben, tipo_conta_ben,
                 nome_rep, cpf_rep, ag_rep, conta_rep, banco_rep, tipo_conta_rep) = p

                if menor and nome_rep:
                    favorecido, cpf_fav, banco, ag, conta, tipo_conta = nome_rep, cpf_rep, banco_rep, ag_rep, conta_rep, tipo_conta_rep
                else:
                    favorecido, cpf_fav, banco, ag, conta, tipo_conta = nome_beneficiario, cpf_ben, banco_ben, ag_ben, conta_ben, tipo_conta_ben

                dados_detalhes.append([
                    Paragraph(nome_beneficiario or '', style_anexo_left),
                    Paragraph(cpf_fav or 'N/A', style_anexo_center),
                    Paragraph(favorecido or '', style_anexo_left),
                    Paragraph(banco or 'N/A', style_anexo_center),
                    Paragraph(ag or 'N/A', style_anexo_center),
                    Paragraph(conta or 'N/A', style_anexo_center),
                    Paragraph(tipo_conta or 'N/A', style_anexo_center),
                    Paragraph(format_value(valor or 0.0), style_anexo_right)
                ])

            # Larguras ajustadas para que a tabela se ajuste à largura da página (A4 retrato)
            col_widths = [4*cm, 4*cm, 2.5*cm, 1.5*cm, 1.5*cm, 2.5*cm, 1.5*cm, 2.0*cm]
            tabela_detalhes = Table(dados_detalhes, colWidths=col_widths, hAlign='CENTER')
            tabela_detalhes.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 1, colors.black),
                ('BACKGROUND', (0,0), (-1,0), colors.grey),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('ALIGN', (0,1), (1,-1), 'LEFT'),
                ('ALIGN', (2,1), (-2,-1), 'CENTER'), # Alinha do CPF até a penúltima
                ('ALIGN', (-1,1), (-1,-1), 'RIGHT'), # Alinha a última (Valor)
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
            ]))
            story.append(tabela_detalhes)

        # Callback para desenhar cabeçalho nas páginas geradas pelo Platypus
        def _on_page(canvas_obj, doc_obj):
            # desenha o cabeçalho e retorna y para conteúdo (não usado aqui diretamente)
            draw_header(canvas_obj, doc_obj.pagesize[0], doc_obj.pagesize[1], logo_path=os.path.join(os.path.dirname(__file__), 'Brasão_do_Distrito_Federal_Brasil.png'), title_lines=default_titles())

        doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
        
        messagebox.showinfo("Sucesso", f"Documento de empenho gerado com sucesso em:\n{caminho_completo}")
        return "SUCCESS"
    except sqlite3.Error as e:
        messagebox.showerror("Erro de Banco de Dados", f"Ocorreu um erro ao acessar o banco de dados: {e}")
        return "ERROR"
    except Exception as e:
        messagebox.showerror("Erro Inesperado", f"Ocorreu um erro ao gerar o documento: {e}")
        return "ERROR"
    finally:
        if conn:
            conn.close()

def gerar_relatorio_pagamento(pagamentos_detalhados, save_path, mes_inicial, mes_final):
    """
    Gera o anexo do relatório de pagamentos em PDF, listando os detalhes bancários.
    """
    nome_arquivo = f"Anexo_Relatorio_Pagamentos_{mes_inicial.replace('/', '-')}_a_{mes_final.replace('/', '-')}.pdf"
    caminho_completo = os.path.join(save_path, nome_arquivo)
    
    try:
        c = canvas.Canvas(caminho_completo, pagesize=letter)
        width, height = letter

        # Desenha cabeçalho padrão
        content_start_y = draw_header(c, width, height, logo_path=os.path.join(os.path.dirname(__file__), 'Brasão_do_Distrito_Federal_Brasil.png'), title_lines=["Anexo - Detalhamento para Pagamento", f"Período de Referência: {mes_inicial} a {mes_final}"])
        c.setFont("Helvetica", 9)
        c.drawString(1*inch, content_start_y, f"Data de Geração: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

        # Posicionamento relativo ao cabeçalho
        y_position = content_start_y - 0.5 * inch

        for dados in pagamentos_detalhados:
            # Desempacota os dados do beneficiário e do representante
            (nome_ben, valor_total, cpf_ben, menor, ag_ben, conta_ben, banco_ben, tipo_conta_ben, 
             nome_rep, cpf_rep, ag_rep, conta_rep, banco_rep, tipo_conta_rep) = dados

            # Verifica se há espaço na página, se não, cria uma nova
            if y_position < 2.5 * inch:
                c.showPage()
                # redraw header on new page
                content_start_y = draw_header(c, width, height, logo_path=os.path.join(os.path.dirname(__file__), 'Brasão_do_Distrito_Federal_Brasil.png'), title_lines=["Anexo - Detalhamento para Pagamento (Continuação)"])
                c.setFont("Helvetica-Bold", 14)
                c.drawCentredString(width / 2.0, content_start_y, "Anexo - Detalhamento para Pagamento (Continuação)")
                y_position = content_start_y - 0.5 * inch

            # --- Bloco de Informações ---
            c.setFont("Helvetica-Bold", 11)
            c.drawString(inch, y_position, f"Beneficiário: {nome_ben or 'N/A'}")
            y_position -= 0.25 * inch
            
            c.setFont("Helvetica", 9)
            c.drawString(inch, y_position, f"CPF: {cpf_ben or 'N/A'}")
            c.drawRightString(width - inch, y_position, f"Valor Total do Período: R$ {valor_total or 0.0:.2f}")
            y_position -= 0.2 * inch

            # Dados bancários do beneficiário
            c.drawString(inch, y_position, f"Banco: {banco_ben or 'N/A'} | Agência: {ag_ben or 'N/A'} | Conta ({tipo_conta_ben or 'N/A'}): {conta_ben or 'N/A'}")
            y_position -= 0.3 * inch

            # Se for menor/incapaz, exibe os dados do representante
            if menor and nome_rep:
                c.setFont("Helvetica-Bold", 10)
                c.drawString(inch, y_position, f"Representante Legal: {nome_rep or 'N/A'}")
                y_position -= 0.2 * inch
                c.setFont("Helvetica", 9)
                c.drawString(inch, y_position, f"CPF do Rep.: {cpf_rep or 'N/A'}")
                y_position -= 0.2 * inch
                c.drawString(inch, y_position, f"Banco: {banco_rep or 'N/A'} | Agência: {ag_rep or 'N/A'} | Conta ({tipo_conta_rep or 'N/A'}): {conta_rep or 'N/A'}")
                y_position -= 0.3 * inch

            # Linha separadora
            c.line(inch, y_position, width - inch, y_position)
            y_position -= 0.3 * inch

        c.save()
        return "SUCCESS"
    except PermissionError:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Erro de Permissão",
            f"Não foi possível salvar o relatório '{caminho_completo}'.\n\n"
            "Verifique se o arquivo não está aberto em outro programa e tente novamente."
        )
        return "ERROR"
    except Exception as e:
        print(f"Erro ao gerar PDF do anexo: {e}")
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Erro ao Gerar PDF", f"Ocorreu um erro inesperado ao gerar o anexo PDF:\n{e}")
        return "ERROR"

def gerar_comprovante_rendimentos_pdf(beneficiario_id, ano_calendario, id_usuario_logado, parent_window):
    """Gera o arquivo PDF do comprovante de rendimentos."""
    try:
        with sqlite3.connect(resource_path('banco.db')) as conn:
            cursor = conn.cursor()
            # 1. Buscar informações do beneficiário
            cursor.execute("SELECT nome_completo, cpf FROM beneficiarios WHERE id = ?", (beneficiario_id,))
            beneficiario = cursor.fetchone()
            if not beneficiario:
                messagebox.showerror("Erro", "Beneficiário não encontrado.", parent=parent_window)
                return

            # 2. Calcular os rendimentos do ano
            cursor.execute("""
                SELECT SUM(valor), SUM(valor_13_salario)
                FROM pagamento_gerados
                WHERE beneficiario_id = ? AND substr(mes_referencia, 4, 4) = ?
            """, (beneficiario_id, ano_calendario))
            rendimentos = cursor.fetchone()

            # 3. Buscar informações do responsável
            cursor.execute("SELECT nome_completo FROM users WHERE id_usuario = ?", (id_usuario_logado,))
            responsavel = cursor.fetchone()

        nome_beneficiario, cpf_beneficiario = beneficiario
        total_bruto, total_13 = rendimentos if rendimentos else (0, 0)
        total_bruto = total_bruto or 0
        total_13 = total_13 or 0

        # O total de rendimentos é o valor bruto menos o 13º, que é declarado em campo separado.
        total_rendimentos_sem_13 = total_bruto - total_13

        nome_responsavel = responsavel[0] if responsavel else "Usuário do Sistema"

        # 4. Pedir ao usuário onde salvar o arquivo
        save_path = tk.filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            title="Salvar Comprovante de Rendimentos",
            initialfile=f"Comprovante_Rendimentos_{nome_beneficiario.replace(' ', '_')}_{ano_calendario}.pdf",
            parent=parent_window
        )
        if not save_path:
            return

        # 5. Gerar o PDF
        c = canvas.Canvas(save_path, pagesize=letter)
        width, height = letter

        # Desenha cabeçalho padrão
        content_start_y = draw_header(c, width, height, logo_path=os.path.join(os.path.dirname(__file__), 'Brasão_do_Distrito_Federal_Brasil.png'), title_lines=["Governo do Distrito Federal", "Secretaria de Estado de Economia do Distrito Federal", "Gerência de Aposentadoria e Pensões Indenizatórias"]) 

        story = []
        # Título (mantemos espaçamento relativo ao content_start_y original)
        header_data = [
            [Paragraph("RESUMO DE DESPESA PESSOAL E ENCARGOS SOCIAIS", style=ParagraphStyle(name='CenterBold', alignment=TA_CENTER, fontName='Helvetica-Bold'))]
        ]
        story.append(Table(header_data, colWidths=[19*cm]))
        story.append(Spacer(1, 0.5*cm))

        # Seções
        # Reposiciona todo o bloco relativo ao início do conteúdo após o cabeçalho
        y = content_start_y - 0.9*cm

        c.setFont("Helvetica-Bold", 10)
        c.drawString(2*cm, y, "1-FONTE PAGADORA PESSOA JURÍDICA"); c.drawString(13*cm, y, "2-NÚMERO DO CNPJ")
        c.setFont("Helvetica", 9)
        y -= 0.5*cm
        c.drawString(2*cm, y, "Razão Social/Nome")
        c.setFont("Helvetica-Bold", 9)
        y -= 0.5*cm
        c.drawString(2*cm, y, "SECRETARIA DE ESTADO DE ECONOMIA DO DISTRITO FEDERAL")
        c.setFont("Helvetica", 9)

        # --- AJUSTE DO CNPJ ---
        # Desenha o retângulo (borda) e o texto do CNPJ mais à direita
        c.rect(13*cm, y - 0.1*cm, 4.5*cm, 0.7*cm, stroke=1, fill=0)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(13.2*cm, y + 0.2*cm, "00.394.684/0001-53")
        c.setFont("Helvetica", 9)
        y -= 0.7*cm
        c.drawString(2*cm, y, "Endereço")
        c.setFont("Helvetica-Bold", 9)
        y -= 0.5*cm
        c.drawString(2*cm, y, "ED.PARQUE CIDADE CORPORATE QD 09 LT C BL B ASA SUL")
        c.setFont("Helvetica", 9)
        y -= 0.5*cm
        c.drawString(2*cm, y, "Cidade") 
        c.drawString(13*cm, y, "UF")
        c.setFont("Helvetica-Bold", 9)
        y -= 0.5*cm
        c.drawString(2*cm, y, "BRASILIA") 
        c.drawString(13*cm, y, "DF")

        c.setFont("Helvetica-Bold", 10)
        y -= 1.0*cm
        c.drawString(2*cm, y, "3-PESSOA FÍSICA BENEFICIÁRIA DE PENSÃO INDENIZATÓRIA")
        c.setFont("Helvetica", 9)
        y -= 0.5*cm
        c.drawString(2*cm, y, "Ano Base"); c.drawString(5*cm, y, "CPF"); c.drawString(9*cm, y, "Nome Completo")
        c.setFont("Helvetica-Bold", 9)
        y -= 0.5*cm
        c.drawString(2*cm, y, str(ano_calendario))
        c.drawString(5*cm, y, str(cpf_beneficiario))
        c.drawString(9*cm, y, str(nome_beneficiario))
        c.setFont("Helvetica", 9)
        y -= 1.0*cm
        c.drawString(2*cm, y, "Natureza do Rendimento")
        c.setFont("Helvetica-Bold", 9)
        y -= 0.5*cm
        c.drawString(2*cm, y, "INDENIZAÇÃO")

        c.setFont("Helvetica-Bold", 10)
        y -= 1.0*cm
        c.drawString(2*cm, y, "4-RENDIMENTOS ISENTOS E NÃO TRIBUTÁVEIS"); c.drawString(16*cm, y, "Em R$")
        c.setFont("Helvetica", 9)
        y -= 0.5*cm
        c.drawString(2*cm, y, "01 - TOTAL DOS RENDIMENTOS (inclusive férias)")
        c.setFont("Helvetica-Bold", 9)
        c.drawRightString(18*cm, y, f"{total_rendimentos_sem_13:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        c.setFont("Helvetica", 9)
        y -= 0.5*cm
        c.drawString(2*cm, y, "02 - DÉCIMO TERCEIRO SALÁRIO")
        c.setFont("Helvetica-Bold", 9)
        c.drawRightString(18*cm, y, f"{total_13:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        c.setFont("Helvetica", 9)
        y -= 0.5*cm
        c.drawString(2*cm, y, "03 - OUTROS")
        c.setFont("Helvetica-Bold", 9)
        c.drawRightString(18*cm, y, "0,00")

        c.setFont("Helvetica-Bold", 10)
        y -= 1.0*cm
        c.drawString(2*cm, y, "5-RESPONSÁVEL PELAS INFORMAÇÕES")
        c.setFont("Helvetica", 9)
        y -= 0.5*cm
        c.drawString(2*cm, y, "NOME"); c.drawString(12*cm, y, "DATA")
        c.setFont("Helvetica-Bold", 9)
        y -= 0.5*cm
        c.drawString(2*cm, y, str(nome_responsavel)); c.drawString(12*cm, y, datetime.now().strftime("%d/%m/%Y"))

        # Salva o PDF e informa sucesso
        c.save()
        messagebox.showinfo("Sucesso", f"Comprovante de rendimentos salvo em:\n{save_path}", parent=parent_window)
        parent_window.destroy()
        return "SUCCESS"
    except sqlite3.Error as e:
        messagebox.showerror("Erro de Banco de Dados", f"Ocorreu um erro ao acessar o banco de dados: {e}", parent=parent_window)
        return "ERROR"
    except Exception as e:
        messagebox.showerror("Erro Inesperado", f"Ocorreu um erro ao gerar o comprovante: {e}", parent=parent_window)
        return "ERROR"