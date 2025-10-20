# import sqlite3
# from datetime import datetime
#ESSSA FUNCOONALIDADE NÃO É MAIS NECESSÁRIA
# def inserir_indice(valor, data_atualizacao=None):
#     if data_atualizacao is None:
#         data_atualizacao = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#     try:
#         conn = sqlite3.connect('banco.db')
#         cursor = conn.cursor()
#         cursor.execute(
#             "INSERT INTO indice (valor, data_atualizacao) VALUES (?, ?)",
#             (valor, data_atualizacao)
#         )
#         conn.commit()
#         conn.close()
#         print("Índice inserido com sucesso!")
#     except Exception as e:
#         print(f"Erro ao inserir índice: {e}")

# if __name__ == "__main__":
#     try:
#         valor = float(input("Digite o valor do índice: ").replace(",", "."))
#         data = input("Digite a data de atualização (YYYY-MM-DD HH:MM:SS) ou deixe em branco para agora: ").strip()
#         if not data:
#             inserir_indice(valor)
#         else:
#             inserir_indice(valor, data)
#     except Exception as e:
#         print(f"Entrada inválida: {e}")