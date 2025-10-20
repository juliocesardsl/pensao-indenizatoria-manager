import sqlite3
from datetime import datetime
import os
import sys
import tkinter as tk
from tkinter import messagebox
import gerar_documentos # Módulo centralizado para gerar documentos
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from pdf_utils import draw_header, default_titles


# ================================================================================================= #
# FUNÇÃO AUXILIAR PARA CAMINHOS DE ARQUIVOS (PARA O EXECUTÁVEL)
# ================================================================================================= #
def resource_path(relative_path):
    """ Obtém o caminho absoluto para o recurso, funciona para dev e para PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# Helper function to get the correct index value for a given date
def get_indice_valor(cursor, tipo_indice, mes_referencia_dt):
    """
    Busca no banco de dados o valor do índice que estava vigente
    no mês de referência informado.
    """
    # Usamos o primeiro dia do mês de referência para a comparação
    data_limite_vigencia = mes_referencia_dt.strftime('%Y-%m-01')
    
    cursor.execute("""
        SELECT valor FROM indice 
        WHERE tipo_indice = ? AND data_vigencia <= ?
          AND status = 'ATIVO'
        ORDER BY data_vigencia DESC, data_atualizacao DESC
        LIMIT 1
    """, (tipo_indice, data_limite_vigencia))
    
    resultado = cursor.fetchone()
    return resultado[0] if resultado else None

def gerar_pagamentos(mes_referencia, beneficiario_id=None, data_de_pagamento=None):
    """
    Gera ou regera os pagamentos para um determinado mês de referência.
    Apaga os pagamentos existentes para o período e os recalcula com base
    nos parâmetros mais recentes.
    """
    try:
        mes_referencia_dt = datetime.strptime(mes_referencia, "%m/%Y")
        mes_referencia_db_format = mes_referencia_dt.strftime("%Y-%m")
    except ValueError:
        print(f"ERRO: Formato de data inválido: {mes_referencia}")
        return "ERROR"

    try:
        with sqlite3.connect(resource_path('banco.db'), timeout=10) as conn:
            cursor = conn.cursor()

            # 1. Define para quais beneficiários o pagamento será gerado
            if beneficiario_id:
                beneficiarios_a_processar = [(beneficiario_id,)]
            else:
                # Busca todos os beneficiários ativos
                cursor.execute("SELECT id FROM beneficiarios")
                beneficiarios_a_processar = cursor.fetchall()

            if not beneficiarios_a_processar:
                print("Nenhum beneficiário ativo encontrado para processar.")
                return "NO_DATA"

            # 2. Apaga os pagamentos antigos para o(s) beneficiário(s) no mês de referência
            if beneficiario_id:
                cursor.execute("DELETE FROM pagamento_gerados WHERE beneficiario_id = ? AND mes_referencia = ?", (beneficiario_id, mes_referencia))
            else:
                cursor.execute("DELETE FROM pagamento_gerados WHERE mes_referencia = ?", (mes_referencia,))
            
            print(f"Pagamentos antigos para {mes_referencia} foram limpos. Iniciando recálculo...")

            # 3. Loop principal para gerar novos pagamentos
            # Converte data_de_pagamento (DD/MM/YYYY) para formato de banco (YYYY-MM-DD) se fornecida
            data_de_pagamento_db = None
            if data_de_pagamento:
                try:
                    dt_pag = datetime.strptime(data_de_pagamento, "%d/%m/%Y")
                    data_de_pagamento_db = dt_pag.strftime("%d-%m-%Y")
                except Exception:
                    data_de_pagamento_db = None

            for b_id_tuple in beneficiarios_a_processar:
                b_id = b_id_tuple[0]
                
                # Busca nome e CPF para o registro
                cursor.execute("SELECT nome_completo, cpf FROM beneficiarios WHERE id = ?", (b_id,))
                info_beneficiario = cursor.fetchone()
                if not info_beneficiario:
                    continue 
                nome_beneficiario, cpf_beneficiario = info_beneficiario

                # 4. Busca o PARÂMETRO MAIS RECENTE válido para o mês
                cursor.execute("""
                    SELECT 
                        id, valor, percentual_concedido, salario_13, um_terco_ferias, 
                        indice_vinculado, data_inicial, observacoes
                    FROM pagamentos
                    WHERE beneficiario_id = ? 
                      AND (substr(data_inicial, 4, 4) || '-' || substr(data_inicial, 1, 2)) <= ?
                      AND (data_final IS NULL OR data_final = '' OR (substr(data_final, 4, 4) || '-' || substr(data_final, 1, 2)) >= ?)
                      AND status = 'ATIVO'
                    ORDER BY data_atualizacao DESC, id DESC
                    LIMIT 1
                """, (b_id, mes_referencia_db_format, mes_referencia_db_format))
                
                parametro_ativo = cursor.fetchone()

                if not parametro_ativo:
                    print(f"AVISO: Nenhum parâmetro de pagamento ativo encontrado para {nome_beneficiario} no mês {mes_referencia}.")
                    continue

                param_id, valor_fixo, percentual, salario_13, um_terco_ferias, indice_vinculado, data_inicial_param, observacoes = parametro_ativo

                valor_base_calculado = 0.0
                percentual_usado = None
                valor_indice_usado = None
                
                def safe_float(val):
                    try:
                        return float(val)
                    except (TypeError, ValueError):
                        return 0.0

                # 5. Lógica de cálculo do valor base
                if percentual not in (None, '', ' ') and safe_float(percentual) > 0 and indice_vinculado:
                    valor_indice_atual = get_indice_valor(cursor, indice_vinculado, mes_referencia_dt)
                    if valor_indice_atual is not None:
                        valor_base_calculado = (safe_float(percentual) / 100.0) * safe_float(valor_indice_atual)
                        percentual_usado = safe_float(percentual)
                        valor_indice_usado = safe_float(valor_indice_atual)
                    else:
                        print(f"AVISO: Índice '{indice_vinculado}' não encontrado para {mes_referencia}. Pagamento para {nome_beneficiario} não gerado.")
                        continue
                elif valor_fixo not in (None, '', ' ') and safe_float(valor_fixo) > 0:
                    valor_base_calculado = safe_float(valor_fixo)
                else:
                    print(f"AVISO: Parâmetro ID {param_id} para {nome_beneficiario} não possui valor fixo ou percentual válido. Pagamento não gerado.")
                    continue

                # 6. Lógica de cálculo de adicionais
                total_valor_13 = 0.0
                if salario_13 and mes_referencia.startswith("12/"):
                    try:
                        ano_ref = int(mes_referencia.split('/')[1])
                        mes_ini, ano_ini = map(int, data_inicial_param.split('/'))
                        meses_trabalhados = 12 - mes_ini + 1 if ano_ref == ano_ini else 12
                        total_valor_13 = (valor_base_calculado / 12.0) * meses_trabalhados
                    except Exception as e:
                        print(f"AVISO: Erro ao calcular 13º para {nome_beneficiario}: {e}")

                total_valor_ferias = 0.0
                if um_terco_ferias:
                    try:
                        data_ini_dt = datetime.strptime(data_inicial_param, "%m/%Y")
                        meses_desde_inicio = (mes_referencia_dt.year - data_ini_dt.year) * 12 + (mes_referencia_dt.month - data_ini_dt.month)
                        if meses_desde_inicio >= 11 and (meses_desde_inicio - 11) % 12 == 0:
                            total_valor_ferias = valor_base_calculado / 3.0
                    except Exception as e:
                        print(f"AVISO: Erro ao calcular 1/3 de férias para {nome_beneficiario}: {e}")

                # 7. Soma total e insere no banco
                valor_final_total = valor_base_calculado + total_valor_13 + total_valor_ferias

                cursor.execute("""
                    INSERT INTO pagamento_gerados (
                        beneficiario_id, nome_beneficiario, cpf_beneficiario, mes_referencia, 
                        valor, valor_13_salario, valor_um_terco_ferias, 
                        percentual_concedido, valor_indice, data_geracao, data_de_pagamento, observacoes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    b_id, nome_beneficiario, cpf_beneficiario, mes_referencia,
                    round(valor_final_total, 2), round(total_valor_13, 2), round(total_valor_ferias, 2),
                    percentual_usado, valor_indice_usado, datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    data_de_pagamento_db,
                    observacoes
                ))
        
        return "SUCCESS"

    except sqlite3.Error as e:
        print(f"Erro de banco de dados em gerar_pagamentos: {e}")
        return "ERROR"
    except Exception as e:
        print(f"Erro inesperado em gerar_pagamentos: {e}")
        return "ERROR"

def _esconder_janela_raiz_tk():
    """Esconde a janela raiz do Tkinter que é criada desnecessariamente ao usar messagebox."""
    root = tk.Tk()
    root.withdraw()

def _gerar_relatorio_txt(periodo_str, pagamentos_gerados, totais, save_path="."):
    """
    Gera um arquivo de texto com o resumo dos pagamentos gerados (layout antigo).
    """
    nome_arquivo = f"Relatorio_Pagamentos_{periodo_str}.txt"
    caminho_completo = os.path.join(save_path, nome_arquivo)
    try:
        with open(caminho_completo, 'w', encoding='utf-8') as f:
            f.write("===================================================================================================\n")
            f.write(f"                                   RELATÓRIO DE PAGAMENTOS\n")
            f.write("===================================================================================================\n\n")
            f.write(f"Período: {periodo_str.replace('_', ' ').replace('-a-', ' a ')}\n")
            f.write(f"Data de Geração: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n")
            f.write(f"{'Beneficiário'.ljust(35)} {'Mês Ref.'.ljust(10)} {'Base (R$)'.rjust(12)} {'13º (R$)'.rjust(12)} {'Férias (R$)'.rjust(12)} {'Total (R$)'.rjust(12)}\n")
            f.write("-" * 100 + "\n")
            for nome, mes_ref, v_base, v_13, v_ferias, v_total in pagamentos_gerados:
                f.write(f"{nome.ljust(35)} {mes_ref.ljust(10)} {f'{v_base:12.2f}'} {f'{v_13:12.2f}'} {f'{v_ferias:12.2f}'} {f'{v_total:12.2f}'}\n")
            f.write("-" * 100 + "\n")
            f.write(f"{'Subtotal Base:'.ljust(88)} {totais['base']:12.2f}\n")
            f.write(f"{'Subtotal 13º Salário:'.ljust(88)} {totais['13']:12.2f}\n")
            f.write(f"{'Subtotal 1/3 Férias:'.ljust(88)} {totais['ferias']:12.2f}\n")
            f.write("-" * 100 + "\n")
            f.write(f"{'TOTAL GERAL'.ljust(88)} {totais['geral']:12.2f}\n\n")
        print(f"Relatório de resumo (TXT) salvo em: {caminho_completo}")
    except IOError as e:
        print(f"Erro ao gerar arquivo de relatório TXT: {e}")

def _gerar_relatorio_pdf_resumo(periodo_str, pagamentos_gerados, totais, save_path="."):
    """
    Gera um arquivo PDF com o resumo dos pagamentos gerados (layout antigo).
    """
    nome_arquivo = f"Relatorio_Pagamentos_{periodo_str}.pdf"
    caminho_completo = os.path.join(save_path, nome_arquivo)
    try:
        c = canvas.Canvas(caminho_completo, pagesize=letter)
        width, height = letter

        # Desenha cabeçalho padrão e obtém a posição inicial de conteúdo
        logo_path = os.path.join(os.path.dirname(__file__), 'Brasão_do_Distrito_Federal_Brasil.png')
        content_start_y = draw_header(c, width, height, logo_path=logo_path, title_lines=["Governo do Distrito Federal", "Secretaria de Estado de Economia", "Gerência de Aposentadoria e Pensões Indenizatórias"]) 
        c.setFont("Helvetica", 10)
        c.drawRightString(width - inch, content_start_y, f"Data de Geração: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

        def draw_table_header(canvas_obj, y_pos):
            canvas_obj.setFont("Helvetica-Bold", 9)
            canvas_obj.drawString(inch, y_pos, "Beneficiário")
            canvas_obj.drawRightString(width - 4.5 * inch, y_pos, "Mês Ref.")
            canvas_obj.drawRightString(width - 3.5 * inch, y_pos, "Base (R$)")
            canvas_obj.drawRightString(width - 2.5 * inch, y_pos, "13º (R$)")
            canvas_obj.drawRightString(width - 1.75 * inch, y_pos, "Férias (R$)")
            canvas_obj.drawRightString(width - inch, y_pos, "Total (R$)")
            y_pos -= 0.2 * inch
            canvas_obj.line(inch, y_pos, width - inch, y_pos)
            y_pos -= 0.25 * inch
            canvas_obj.setFont("Courier", 8)
            return y_pos

        def format_value(val):
            return f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        
        # Começamos a tabela logo abaixo do cabeçalho
        y_position = content_start_y - 0.4 * inch
        y_position = draw_table_header(c, y_position)

        for nome, mes_ref, v_base, v_13, v_ferias, v_total in pagamentos_gerados:
            # Se estiver próximo do rodapé, cria nova página e redesenha o cabeçalho
            if y_position < 1.5 * inch:
                c.showPage()
                content_start_y = draw_header(c, width, height, logo_path=logo_path, title_lines=["RELATÓRIO DE PAGAMENTOS", f"Período: {periodo_str.replace('_', ' ').replace('-a-', ' a ')}"]) 
                c.setFont("Helvetica", 10)
                c.drawRightString(width - inch, content_start_y, f"Data de Geração: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
                y_position = content_start_y - 0.4 * inch
                y_position = draw_table_header(c, y_position)

            c.drawString(inch, y_position, (nome or '')[:40])
            c.drawRightString(width - 4.5 * inch, y_position, f"{mes_ref}")
            c.drawRightString(width - 3.5 * inch, y_position, f"{v_base:9.2f}")
            c.drawRightString(width - 2.5 * inch, y_position, f"{v_13:9.2f}")
            c.drawRightString(width - 1.75 * inch, y_position, f"{v_ferias:9.2f}")
            c.drawRightString(width - inch, y_position, f"{v_total:9.2f}")
            y_position -= 0.25 * inch

        # Caso não caiba o resumo de totais na página atual, cria nova página e redesenha cabeçalho
        if y_position < 2.5 * inch:
            c.showPage()
            content_start_y = draw_header(c, width, height, logo_path=logo_path, title_lines=["RELATÓRIO DE PAGAMENTOS", f"Período: {periodo_str.replace('_', ' ').replace('-a-', ' a ')}"]) 
            c.setFont("Helvetica", 10)
            c.drawRightString(width - inch, content_start_y, f"Data de Geração: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
            y_position = content_start_y - 0.6 * inch

        y_position -= 0.1 * inch
        c.line(inch, y_position, width - inch, y_position)
        y_position -= 0.25 * inch
        
        

        c.setFont("Helvetica", 9)
        c.drawString(inch, y_position, "Subtotal Base:")
        c.drawRightString(width - inch, y_position, f"{format_value(totais['base']): >9}")
        y_position -= 0.2 * inch
        c.drawString(inch, y_position, "Subtotal 13º Salário:")
        c.drawRightString(width - inch, y_position, f"{format_value(totais['13']): >9}")
        y_position -= 0.2 * inch
        c.drawString(inch, y_position, "Subtotal 1/3 Férias:")
        c.drawRightString(width - inch, y_position, f"{format_value(totais['ferias']): >9}")
        y_position -= 0.2 * inch
        c.line(inch, y_position, width - inch, y_position)
        y_position -= 0.25 * inch
        c.setFont("Helvetica-Bold", 11)
        c.drawString(inch, y_position, "TOTAL GERAL")
        c.drawRightString(width - inch, y_position, f"{format_value(totais['geral']): >9}")

        c.save()
        print(f"Relatório PDF de resumo salvo em: {caminho_completo}")
        return True
    except PermissionError:
        _esconder_janela_raiz_tk()
        messagebox.showerror("Erro de Permissão", f"Não foi possível salvar o relatório '{caminho_completo}'.\n\nVerifique se o arquivo não está aberto e tente novamente.")
        return False
    except Exception as e:
        _esconder_janela_raiz_tk()
        messagebox.showerror("Erro ao Gerar PDF", f"Ocorreu um erro inesperado ao gerar o relatório PDF de resumo:\n{e}")
        return False

def gerar_relatorios_por_periodo(mes_inicial, mes_final, save_path, beneficiario_id=None):
    """
    Gera os relatórios (resumo em TXT e PDF, e anexo em PDF) com base nos pagamentos já gerados.
    """
    try:
        # Usando 'with' para garantir que a conexão seja fechada corretamente
        with sqlite3.connect(resource_path('banco.db')) as conn:
            cursor = conn.cursor()

            start_date = datetime.strptime(mes_inicial, "%m/%Y").strftime("%Y-%m")
            end_date = datetime.strptime(mes_final, "%m/%Y").strftime("%Y-%m")
            periodo_str = f"{mes_inicial.replace('/', '-')}_a_{mes_final.replace('/', '-')}"

            # --- 1. BUSCA DE DADOS PARA O RELATÓRIO DE RESUMO ---
            query_resumo = """
                SELECT 
                    nome_beneficiario,
                    mes_referencia,
                    (valor - ifnull(valor_13_salario, 0) - ifnull(valor_um_terco_ferias, 0)) as valor_base,
                    ifnull(valor_13_salario, 0),
                    ifnull(valor_um_terco_ferias, 0),
                    valor
                FROM pagamento_gerados
                WHERE strftime('%Y-%m', printf('%s-%s-01', substr(mes_referencia, 4, 4), substr(mes_referencia, 1, 2))) BETWEEN ? AND ?
            """
            params_resumo = [start_date, end_date]

            if beneficiario_id:
                query_resumo += " AND beneficiario_id = ?"
                params_resumo.append(beneficiario_id)
            
            query_resumo += " ORDER BY nome_beneficiario, strftime('%Y-%m', printf('%s-%s-01', substr(mes_referencia, 4, 4), substr(mes_referencia, 1, 2)))"
            
            cursor.execute(query_resumo, params_resumo)
            pagamentos_resumo = cursor.fetchall()

            if not pagamentos_resumo:
                return "NO_DATA"

            # --- 2. GERAÇÃO DOS RELATÓRIOS DE RESUMO (TXT E PDF) ---
            total_base = sum(p[2] for p in pagamentos_resumo)
            total_13 = sum(p[3] for p in pagamentos_resumo)
            total_ferias = sum(p[4] for p in pagamentos_resumo)
            total_geral = sum(p[5] for p in pagamentos_resumo)
            totais = {'base': total_base, '13': total_13, 'ferias': total_ferias, 'geral': total_geral}

            _gerar_relatorio_txt(periodo_str, pagamentos_resumo, totais, save_path)
            pdf_resumo_success = _gerar_relatorio_pdf_resumo(periodo_str, pagamentos_resumo, totais, save_path)

            # Retorna o status baseado apenas no sucesso da geração do PDF de resumo
            if pdf_resumo_success:
                return "SUCCESS"
            else:
                return "PARTIAL_SUCCESS"

    except sqlite3.Error as e:
        print(f"Erro de banco de dados em gerar_relatorios_por_periodo: {e}")
        return "ERROR"
    except Exception as e:
        print(f"Erro inesperado em gerar_relatorios_por_periodo: {e}")
        return "ERROR"
