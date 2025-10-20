# salvar como: importar_dados.py
import sqlite3
import pandas as pd
from datetime import datetime
import sys

def limpar_tabelas():
    """Apaga todos os dados das tabelas de beneficiários, representantes e parâmetros."""
    conn = sqlite3.connect('banco.db')
    cursor = conn.cursor()

    print("Limpando tabelas existentes...")

    try:
        # Apaga os dados das tabelas relacionadas ao cadastro
        cursor.execute("DELETE FROM pagamentos")
        cursor.execute("DELETE FROM representantes_legais")
        cursor.execute("DELETE FROM beneficiarios")
        
        # Reinicia os contadores de ID para essas tabelas
        cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('pagamentos', 'representantes_legais', 'beneficiarios')")
        
        conn.commit()
        print("Tabelas 'pagamentos', 'representantes_legais' e 'beneficiarios' foram limpas com sucesso.")
    except sqlite3.Error as e:
        print(f"ERRO ao limpar as tabelas: {e}")
        conn.rollback()
        sys.exit("Importação abortada devido a erro na limpeza do banco.")
    finally:
        conn.close()

def formatar_data_para_mes_ano(data_str):
    """Tenta converter uma string de data (em vários formatos) para MM/AAAA."""
    if not data_str or pd.isna(data_str):
        return ''
    
    # Se já for um objeto datetime (pandas pode converter automaticamente)
    if isinstance(data_str, datetime):
        return data_str.strftime('%m/%Y')

    # Se for uma string, tenta analisar
    try:
        # Tenta analisar formatos comuns como '2025-01-01 00:00:00', '01/01/2025', etc.
        data_dt = pd.to_datetime(data_str, errors='coerce')
        if pd.notna(data_dt):
            return data_dt.strftime('%m/%Y')
    except Exception:
        # Se falhar, retorna a string original (pode já estar no formato MM/AAAA)
        pass
    return str(data_str).strip()

def formatar_cpf(cpf):
    """Garante que o CPF tenha apenas dígitos."""
    if isinstance(cpf, str):
        cpf_str = ''.join(filter(str.isdigit, cpf))
    else:
        cpf_str = str(cpf)
    
    # Se o CPF ficou com 10 dígitos, provavelmente perdeu o zero à esquerda
    if len(cpf_str) == 10:
        return '0' + cpf_str
    return cpf_str

def importar_beneficiarios(df_beneficiarios):
    """Importa os dados dos beneficiários para o banco."""
    conn = sqlite3.connect('banco.db')
    cursor = conn.cursor()

    sucesso = 0
    falha = 0

    for index, row in df_beneficiarios.iterrows():
        cpf_limpo = formatar_cpf(row.get('cpf', ''))

        # Pula se o CPF for inválido
        if not cpf_limpo or len(cpf_limpo) != 11:
            print(f"CPF inválido ou ausente na linha {index + 2}. Pulando.")
            falha += 1
            continue

        # Formata o número do banco para ter 3 dígitos com zeros à esquerda
        numero_banco_raw = row.get('numero_banco', '')
        numero_banco_fmt = ''
        if numero_banco_raw:
            numero_banco_fmt = str(numero_banco_raw).split('.')[0].zfill(3)

        try:
            cursor.execute("""
                INSERT INTO beneficiarios (
                    nome_completo, cpf, data_nascimento, naturalidade, identidade, orgao_emissor, email, 
                    endereco, cep, telefone, numero_processo_judicial, numero_processo_sei, 
                    origem_decisao, numero_vara, data_decisao, data_oficioPGDF, 
                    numero_banco, descricao_banco, agencia, numero_conta, digitoconta, tipo_conta, codigouf,
                    menor_ou_incapaz, observacoes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row.get('nome_completo'), cpf_limpo, row.get('data_nascimento'), row.get('naturalidade'),
                row.get('identidade'), row.get('orgao_emissor'), row.get('email'), row.get('endereco'),
                row.get('cep'), row.get('telefone'), row.get('numero_processo_judicial'),
                row.get('numero_processo_sei'), row.get('origem_decisao'), row.get('numero_vara'),
                row.get('data_decisao'), row.get('data_oficioPGDF'), numero_banco_fmt,
                row.get('descricao_banco'), row.get('agencia'), row.get('numero_conta'),
                row.get('digitoconta'), row.get('tipo_conta'), row.get('codigouf'), int(row.get('menor_ou_incapaz', 0)),
                row.get('observacoes')
            ))
            sucesso += 1
        except sqlite3.IntegrityError:
            print(f"Beneficiário com CPF {cpf_limpo} já existe. Pulando.")
            falha += 1
        except Exception as e:
            print(f"Erro ao inserir beneficiário com CPF {cpf_limpo}: {e}")
            falha += 1

    conn.commit()
    conn.close()
    print(f"\n--- Beneficiários ---\n{sucesso} inseridos com sucesso.\n{falha} falharam ou já existiam.")

def importar_parametros(df_parametros):
    """Importa os parâmetros de pagamento para o banco."""
    conn = sqlite3.connect('banco.db')
    cursor = conn.cursor()

    sucesso = 0
    falha = 0

    for index, row in df_parametros.iterrows():
        cpf_limpo = formatar_cpf(row.get('cpf_beneficiario', ''))

        if not cpf_limpo or len(cpf_limpo) != 11:
            print(f"CPF inválido ou ausente na linha {index + 2} da aba de parâmetros. Pulando.")
            falha += 1
            continue

        try:
            # Busca o ID do beneficiário pelo CPF
            cursor.execute("SELECT id FROM beneficiarios WHERE cpf = ?", (cpf_limpo,))
            result = cursor.fetchone()
            if not result:
                print(f"Beneficiário com CPF {cpf_limpo} não encontrado. Parâmetro não inserido.")
                falha += 1
                continue

            beneficiario_id = result[0]
            data_atualizacao = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            data_inicial_fmt = formatar_data_para_mes_ano(row.get('data_inicial'))
            data_final_fmt = formatar_data_para_mes_ano(row.get('data_final'))

            cursor.execute("""
                INSERT INTO pagamentos (
                    beneficiario_id, cpf_beneficiario, data_inicial, data_final, valor, 
                    percentual_concedido, indice_vinculado, salario_13, um_terco_ferias, 
                    observacoes, status, data_atualizacao, usuario_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                beneficiario_id, cpf_limpo, data_inicial_fmt, data_final_fmt,
                row.get('valor_fixo'), row.get('percentual_concedido'), row.get('indice_vinculado'),
                int(row.get('salario_13', 0)), int(row.get('um_terco_ferias', 0)),
                row.get('observacoes'), row.get('status', 'ATIVO'), data_atualizacao, 1 # ID do usuário admin
            ))
            sucesso += 1
        except Exception as e:
            print(f"Erro ao inserir parâmetro para o CPF {cpf_limpo}: {e}")
            falha += 1

    conn.commit()
    conn.close()
    print(f"\n--- Parâmetros de Pagamento ---\n{sucesso} inseridos com sucesso.\n{falha} falharam ou beneficiário não encontrado.")

def main():
    try:
        df_beneficiarios = pd.read_excel('dados_importacao.xlsx', sheet_name='Beneficiarios', dtype=str).fillna('')
        df_parametros = pd.read_excel('dados_importacao.xlsx', sheet_name='Parametros', dtype=str).fillna('')
    except FileNotFoundError:
        print("Erro: Arquivo 'dados_importacao.xlsx' não encontrado.")
        print("Verifique se o nome do arquivo está correto e se ele está na mesma pasta do script.")
        return
    except Exception as e:
        print(f"Erro ao ler a planilha: {e}")
        return

    print("Iniciando importação de dados...")
    limpar_tabelas()

    print("\nIniciando importação de beneficiários...")
    importar_beneficiarios(df_beneficiarios)
    
    print("\nIniciando importação de parâmetros de pagamento...")
    importar_parametros(df_parametros)
    
    print("\nImportação concluída!")

if __name__ == "__main__":
    main()
