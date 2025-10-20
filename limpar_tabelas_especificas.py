# salvar como: limpar_tabelas_especificas.py
import sqlite3
import sys
import shutil
from datetime import datetime

def limpar_todas_as_tabelas_exceto_users():
    """
    Apaga todos os dados de todas as tabelas, exceto da tabela 'users'.
    Também reinicia os contadores de ID para as tabelas limpas.
    """
    # Lista de todas as tabelas que devem ser limpas
    tabelas_para_limpar = [
        'beneficiarios',
        'representantes_legais',
        'pagamentos',
        'pagamento_gerados',
        'indice',
        'folhas',
        'anexos',
        # 'status_ref_pagamento' # Tabela obsoleta, pode ser incluída se ainda existir
    ]

    try:
        # Pede confirmação explícita ao usuário para evitar acidentes
        confirmacao = input(
            "ATENÇÃO: Esta ação apagará TODOS os dados do sistema, exceto os de usuários (logins).\n"
            "Serão limpas as tabelas de beneficiários, pagamentos, índices, folhas, etc.\n"
            "Esta ação não pode ser desfeita.\n\n"
            "Digite 'CONFIRMAR' para continuar: "
        )
        if confirmacao != 'CONFIRMAR':
            print("\nOperação cancelada pelo usuário.")
            sys.exit()

        # Usa 'with' para garantir que a conexão seja fechada mesmo em caso de erro
        with sqlite3.connect('banco.db') as conn:
            cursor = conn.cursor()
            
            print("\nIniciando limpeza completa do banco de dados...")

            # Itera sobre a lista para apagar os dados de cada tabela
            for tabela in tabelas_para_limpar:
                try:
                    print(f"Limpando a tabela '{tabela}'...")
                    cursor.execute(f"DELETE FROM {tabela}")
                except sqlite3.OperationalError:
                    # Ignora o erro se a tabela não existir, tornando o script mais robusto
                    print(f"  - Aviso: Tabela '{tabela}' não encontrada. Pulando.")

            # Reinicia os contadores de ID (autoincremento) para todas as tabelas limpas
            print("Reiniciando contadores de ID...")
            # Cria uma string de placeholders para a consulta SQL
            placeholders = ', '.join(['?'] * len(tabelas_para_limpar))
            cursor.execute(f"DELETE FROM sqlite_sequence WHERE name IN ({placeholders})", tabelas_para_limpar)
            
            conn.commit()
            print("\nLimpeza concluída com sucesso!")

    except sqlite3.Error as e:
        print(f"\nERRO: Ocorreu um erro no banco de dados: {e}")
        sys.exit("Operação abortada.")
    except Exception as e:
        print(f"\nERRO: Ocorreu um erro inesperado: {e}")
        sys.exit("Operação abortada.")

if __name__ == "__main__":
    # Faz um backup antes de executar a limpeza
    try:
        data_hora = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"banco.db.backup_{data_hora}"
        shutil.copy2('banco.db', backup_path)
        print(f"Backup do banco de dados criado em: {backup_path}")
    except Exception as e:
        print(f"Aviso: Não foi possível criar um backup automático do banco de dados. Erro: {e}")

    limpar_todas_as_tabelas_exceto_users()
