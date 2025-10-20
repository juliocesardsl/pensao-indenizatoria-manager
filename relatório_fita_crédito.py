import pandas as pd

def formatar_cpf(cpf):
    cpf = cpf.zfill(11)
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:11]}"

def parse_cabecalho(arquivo_txt):
    with open(arquivo_txt, "r", encoding="utf-8") as f:
        try:
            linha = f.readline().rstrip("\n")
            if len(linha) < 95: return pd.DataFrame()

            valor_str = linha[43:57].strip()
            valor_total = f"R$ {int(valor_str) / 100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if valor_str.isdigit() else ""
            cabecalho = {
                "Código do Órgão": linha[0:5],
                "Código da Folha": linha[5:8],
                "Tipo de Registro": linha[8:9],
                "Mês de Referência": linha[9:11],
                "Ano de Referência": linha[11:15],
                "Tipo de Pagamento": linha[15:17],
                "Descrição do Pagamento": linha[17:37].strip(),
                "Quantidade de Registros": linha[37:43].strip(),
                "Valor Total": valor_total,
            }
            return pd.DataFrame([cabecalho])
        except (IOError, IndexError):
            return pd.DataFrame()

def parse_final(arquivo_txt):
    with open(arquivo_txt, "r", encoding="utf-8") as f:
        try:
            linhas = f.readlines()
            if len(linhas) < 2: return pd.DataFrame()
            
            linha = linhas[-1].rstrip("\n")
            if len(linha) < 95 or linha[8:9] != '3': return pd.DataFrame()

            valor_str = linha[15:29].strip()
            valor_total = f"R$ {int(valor_str) / 100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if valor_str.isdigit() else ""
            final = {
                "Código do Órgão": linha[0:5],
                "Código da Folha": linha[5:8],
                "Tipo de Registro": linha[8:9],
                "Quantidade de Registros": linha[9:15].strip(),
                "Valor Total": valor_total,
            }
            return pd.DataFrame([final])
        except (IOError, IndexError):
            return pd.DataFrame()

def parse_fita_credito(arquivo_txt):
    registros = []
    with open(arquivo_txt, "r", encoding="utf-8") as f:
        # Pula o cabeçalho (primeira linha) e o trailer (última linha)
        linhas = f.readlines()[1:-1]
        for linha in linhas:
            linha = linha.rstrip("\n")
            if len(linha) < 95:
                continue
            tipo_movimento = linha[8:9]
            if tipo_movimento == "2":
                cpf = linha[84:95].strip()
                valor_str = linha[54:64].strip()
                valor = int(valor_str) / 100 if valor_str.isdigit() else 0.0
                
                tipo_conta_code = linha[74:75]
                tipo_conta_map = {'0': 'Corrente', '1': 'Poupança'} # Ajustado conforme layout
                tipo_conta_str = tipo_conta_map.get(tipo_conta_code, 'Desconhecido')

                registro = {
                    "Código do Órgão": linha[0:5],
                    "Código da Folha": linha[5:8],
                    "Tipo de Registro": linha[8:9],
                    "Tipo de Movimento": tipo_movimento,
                    "Matrícula do servidor": linha[9:17].strip(),
                    "Nome do servidor": linha[17:54].strip(),
                    "Valor do pagamento": f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                    "Número da conta": linha[64:73].strip(),
                    "Dígito Conta": linha[73:74].strip(),
                    "Tipo Conta": tipo_conta_str,
                    "Banco": linha[75:78].strip(),
                    "Agência Pagamento": linha[78:82].strip(),
                    "UF": linha[82:84].strip(),
                    "CPF do servidor": formatar_cpf(cpf) if cpf.isdigit() and len(cpf) == 11 else cpf,
                }
                registros.append(registro)
    return pd.DataFrame(registros)

def gerar_relatorio_fita_credito(arquivo_txt, arquivo_excel):
    df_cabecalho = parse_cabecalho(arquivo_txt)
    df_detalhes = parse_fita_credito(arquivo_txt)
    df_final = parse_final(arquivo_txt)

    with pd.ExcelWriter(arquivo_excel, engine='openpyxl') as writer:
        if not df_cabecalho.empty:
            df_cabecalho.to_excel(writer, sheet_name="Cabeçalho", index=False)
        if not df_detalhes.empty:
            df_detalhes.to_excel(writer, sheet_name="Detalhes", index=False)
        if not df_final.empty:
            df_final.to_excel(writer, sheet_name="Final", index=False)