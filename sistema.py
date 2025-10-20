import bcrypt
import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
from customtkinter import CTkImage
from tkinter import messagebox
from datetime import datetime
from tkinter.ttk import *
from tkinter import *
from tkcalendar import Calendar
import sqlite3
import subprocess
import os
import sys
from tkinter import filedialog  
from gerar_pagamento import gerar_pagamentos, gerar_relatorios_por_periodo
from relatório_fita_crédito import parse_fita_credito, formatar_cpf, parse_cabecalho, gerar_relatorio_fita_credito, parse_final
from gerar_fita_credito import gerar_fita_credito_txt
import exportar_excel
import gerar_documentos
import re

# ================================================================================================= #
# DICIONÁRIO GLOBAL DE BANCOS
# Para adicionar ou remover um banco, edite apenas este dicionário.
# ================================================================================================= #
BANCOS = {
    "001": "Banco do Brasil",
    "033": "Santander",
    "070": "Banco de Brasília",
    "077": "Banco Inter",
    "104": "Caixa Econômica Federal",
    "237": "Bradesco",
    "260": "Nu Pagamentos S.A. (Nubank)",
    "336": "Banco C6 S.A. (C6 Bank)",
    "341": "Itaú Unibanco",
    "380": "PicPay",
    "756": "Sicoob (Bancoob)",
}

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

#=================================================================================================#



#=================================================================================================#

def atualizar_combos():
    global combo_beneficiarios, combo_beneficiarios_ativos, mapa_beneficiarios
    
    try:
        conn = sqlite3.connect(resource_path('banco.db'))
        cursor = conn.cursor()
        
        # Obtém os beneficiários do banco de dados
        cursor.execute("SELECT id, nome_completo FROM beneficiarios")
        beneficiarios = cursor.fetchall()
        mapa_beneficiarios = {beneficiario: id for id, beneficiario in beneficiarios}
        combo_beneficiarios_ativos = list(mapa_beneficiarios.keys())
    except sqlite3.Error as e:
        messagebox.showerror("Erro", f"Erro ao acessar o banco de dados: {e}")
        return
    finally:
        if conn:
            conn.close()

#============================Cadastro de Usuários=================================================#
def atualizarListaUsuarios(frame):
    for widget in frame.winfo_children():
        widget.destroy()

    conn = sqlite3.connect(resource_path('banco.db'))
    cursor = conn.cursor()
    # Busca usuários e o nome do responsável vinculado (se houver)
    cursor.execute("""
        SELECT 
            u.id_usuario, 
            u.nome_usuario, 
            u.status
        FROM users u
        """)
    usuarios = cursor.fetchall()
    conn.close()

    # Botão para cadastrar novo usuário
    botao_cadastro = tk.Button(frame, text="Cadastrar Novo Usuário", command=lambda: abrirCadastroUsuario(frame))
    botao_cadastro.grid(row=0, column=0, columnspan=4, pady=10)

    for idx, (id_usuario, nome_usuario, status) in enumerate(usuarios, start=1):
        label = tk.Label(
            frame,
            text=f"{nome_usuario} - {status}",
            anchor="w",
            font=("Calibri", 10, "bold")
        )
        label.grid(row=idx, column=0, padx=10, pady=5, sticky="w")


        botao_status = tk.Button(
            frame, text="Desativar" if status == "ATIVO" else "Ativar",
            command=lambda id_usuario=id_usuario, status=status: alterarStatusUsuario(id_usuario, frame, status)
        )
        botao_status.grid(row=idx, column=1, padx=10, pady=5)

        botao_editar = tk.Button(
            frame, text="Editar",
            command=lambda id_usuario=id_usuario, nome_atual=nome_usuario: editarUsuario(id_usuario, nome_atual, frame)
        )
        botao_editar.grid(row=idx, column=2, padx=10, pady=5)

def alterarStatusUsuario(id_usuario, frame, status_atual):
    novo_status = "DESATIVADO" if status_atual == "ATIVO" else "ATIVO"
    conn = sqlite3.connect(resource_path('banco.db'))
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET status = ? WHERE id_usuario = ?", (novo_status, id_usuario))
    conn.commit()
    conn.close()
    atualizarListaUsuarios(frame)

def hash_senha(senha):
    """Gera um hash seguro para a senha."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(senha.encode('utf-8'), salt).decode('utf-8')

def cadastrarUsuario(nome_usuario, senha, nome_completo, num_matr, perfil, janela, frame):
    if not (nome_usuario.strip() and senha.strip() and nome_completo.strip() and num_matr.strip() and perfil.strip()):
        messagebox.showerror("Erro", "Todos os campos são obrigatórios!")
        return
    
    senha_hash = hash_senha(senha)  # Criptografa a senha antes de salvar

    conn = sqlite3.connect(resource_path('banco.db'))
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO users (nome_usuario, senha, status, nome_completo, num_matr, perfil) 
                      VALUES (?, ?, 'ATIVO', ?, ?, ?)''', 
                   (nome_usuario, senha_hash, nome_completo, num_matr, perfil))

    conn.commit()
    conn.close()
    messagebox.showinfo("Sucesso", "Usuário cadastrado com sucesso!")
    janela.destroy()
    atualizarListaUsuarios(frame)

def editarUsuario(id_usuario, nome_atual, frame):
    # Buscar os dados atuais do usuário
    conn = sqlite3.connect(resource_path('banco.db'))
    cursor = conn.cursor()
    cursor.execute("SELECT nome_usuario, senha, nome_completo, num_matr, perfil, status FROM users WHERE id_usuario = ?", (id_usuario,))
    usuario = cursor.fetchone()
    conn.close()

    if not usuario:
        messagebox.showerror("Erro", "Usuário não encontrado!")
        return

    nome_atual, senha_atual, nome_completo_atual, num_matr_atual, perfil_atual, status_atual = usuario

    # Criar janela de edição
    janela_editar = tk.Toplevel()
    janela_editar.title("Editar Usuário")
    janela_editar.geometry('350x450')

    # Campos de edição
    tk.Label(janela_editar, text="Nome de usuário:").pack(pady=5)
    entrada_nome = tk.Entry(janela_editar, width=30)
    entrada_nome.insert(0, nome_atual)
    entrada_nome.pack(pady=5)

    tk.Label(janela_editar, text="Senha:").pack(pady=5)
    entrada_senha = tk.Entry(janela_editar, width=30, show="*")
    entrada_senha.pack(pady=5)

    tk.Label(janela_editar, text="Nome Completo:").pack(pady=5)
    entrada_nome_completo = tk.Entry(janela_editar, width=30)
    entrada_nome_completo.insert(0, nome_completo_atual)
    entrada_nome_completo.pack(pady=5)

    tk.Label(janela_editar, text="Número de Matrícula:").pack(pady=5)
    entrada_matr = tk.Entry(janela_editar, width=30)
    entrada_matr.insert(0, num_matr_atual)
    entrada_matr.pack(pady=5)

    # Combobox para Perfil
    tk.Label(janela_editar, text="Perfil:").pack(pady=5)
    entrada_perfil = ttk.Combobox(janela_editar, values=["1 - Administrador", "2 - Usuário Padrão"], state="readonly", width=27)
    entrada_perfil.pack(pady=5)
    
    # Selecionar o perfil atual do usuário
    if perfil_atual == "1":
        entrada_perfil.current(0)  # Administrador
    elif perfil_atual == "2":
        entrada_perfil.current(1)  # Usuário Padrão

    # Combobox para Status
    tk.Label(janela_editar, text="Status:").pack(pady=5)
    status_combo = ttk.Combobox(janela_editar, values=["ATIVO", "DESATIVADO"], state="readonly")
    status_combo.set(status_atual)
    status_combo.pack(pady=5)

    def salvar_edicao():
        novo_nome = entrada_nome.get().strip()
        nova_senha = entrada_senha.get().strip()
        novo_nome_completo = entrada_nome_completo.get().strip()
        novo_matr = entrada_matr.get().strip()
        novo_perfil = entrada_perfil.get().split(" - ")[0]  # Pegando apenas o número do perfil
        novo_status = status_combo.get()

        if not (novo_nome and novo_nome_completo and novo_matr and novo_perfil):
            messagebox.showerror("Erro", "Todos os campos são obrigatórios!")
            return

        senha_hash = hash_senha(nova_senha) if nova_senha else senha_atual  # Só altera a senha se o campo não estiver vazio

        conn = sqlite3.connect(resource_path('banco.db'))
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users 
            SET nome_usuario = ?, senha = ?, nome_completo = ?, num_matr = ?, perfil = ?, status = ?
            WHERE id_usuario = ?
        """, (novo_nome, senha_hash, novo_nome_completo, novo_matr, novo_perfil, novo_status, id_usuario))
        conn.commit()
        conn.close()

        messagebox.showinfo("Sucesso", "Usuário atualizado com sucesso!")
        janela_editar.destroy()
        atualizarListaUsuarios(frame)

    # Botões
    tk.Button(janela_editar, text="Salvar Alterações", command=salvar_edicao).pack(pady=10)
    tk.Button(janela_editar, text="Cancelar", command=janela_editar.destroy).pack(pady=5)

def abrirCadastroUsuario(frame):
    janela_cadastro = tk.Toplevel()
    janela_cadastro.title("Cadastrar Novo Usuário")
    janela_cadastro.geometry("300x400")

    tk.Label(janela_cadastro, text="Nome de usuário:").pack(pady=5)
    entrada_nome = tk.Entry(janela_cadastro, width=30)
    entrada_nome.pack(pady=5)

    tk.Label(janela_cadastro, text="Senha:").pack(pady=5)
    entrada_senha = tk.Entry(janela_cadastro, width=30, show="*")
    entrada_senha.pack(pady=5)

    tk.Label(janela_cadastro, text="Nome Completo:").pack(pady=5)
    entrada_nome_completo = tk.Entry(janela_cadastro, width=30)
    entrada_nome_completo.pack(pady=5)

    tk.Label(janela_cadastro, text="Número de Matrícula:").pack(pady=5)
    entrada_matr = tk.Entry(janela_cadastro, width=30)
    entrada_matr.pack(pady=5)

    tk.Label(janela_cadastro, text="Perfil:").pack(pady=5)
    entrada_perfil = ttk.Combobox(janela_cadastro, values=["1 - Administrador", "2 - Usuário Padrão"], state="readonly", width=27)
    entrada_perfil.pack(pady=5)
    entrada_perfil.current(1)  # Define a opção padrão como "Usuário Padrão"

    botao_cadastrar = tk.Button(janela_cadastro, text="Cadastrar", 
                                command=lambda: cadastrarUsuario(
                                    entrada_nome.get(), entrada_senha.get(), 
                                    entrada_nome_completo.get(), entrada_matr.get(), 
                                    entrada_perfil.get().split(" - ")[0],  # Pegando apenas o número do perfil
                                    janela_cadastro, frame))
    botao_cadastrar.pack(pady=10)

    tk.Button(janela_cadastro, text="Cancelar", command=janela_cadastro.destroy).pack(pady=5)

from customtkinter import CTkScrollableFrame

def abrirTelaUsuarios():
    janela_usuarios = tk.Toplevel()
    janela_usuarios.title("Usuários do Sistema")
    janela_usuarios.geometry("500x400")
    janela_usuarios.resizable(False, False)

    frame_usuarios = CTkScrollableFrame(janela_usuarios, width=480, height=340, corner_radius=10)
    frame_usuarios.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    atualizarListaUsuarios(frame_usuarios)
    
#==============================================================================================#

def configurar_estilo_treeview():
    """Configura um estilo global para todos os Treeviews da aplicação."""
    style = ttk.Style()
    # Usar um tema que permita customização (clam, alt, default)
    style.theme_use("default")
    
    # Configuração do estilo principal do Treeview
    style.configure("Treeview",
                    background="#ffffff",
                    foreground="black",
                    rowheight=25,
                    fieldbackground="#ffffff")
    
    # Cor de seleção
    style.map('Treeview', background=[('selected', '#a1970c')])

    # Configuração do cabeçalho
    style.configure("Treeview.Heading", font=('Calibri', 10, 'bold'))

#==============================================================================================#

def exibir_janela_principal():
    janelaPrincipal = ctk.CTk()  # Troque CTkToplevel() por CTk()
    janelaPrincipal.title("Sistema Pensão Indenizatória")
    janelaPrincipal.geometry("720x550")
    ctk.set_default_color_theme("blue")
    configurar_estilo_treeview()

    menuBarra = Menu(janelaPrincipal)
    
    menuCadastro = Menu(menuBarra, tearoff=0)
    menuFerramentas = Menu(menuBarra, tearoff=0)
    
    # Cria o novo submenu para exportação
    menuExportar = Menu(menuFerramentas, tearoff=0)
    menuExportar.add_command(label="Lista de Beneficiários", command=exportar_excel.exportar_beneficiarios_excel)
    menuExportar.add_command(label="Lista de Parâmetros de Pagamento", command=exportar_excel.exportar_parametros_excel)
    menuExportar.add_command(label="Lista de Pagamentos Gerados", command=exportar_excel.exportar_pagamentos_gerados_excel)
    menuExportar.add_command(label="Lista de Representantes Legais", command=exportar_excel.exportar_representantes_excel)
    

    menuCadastro.add_command(label="Cadastrar Usuário", command=abrirTelaUsuarios)
    menuFerramentas.add_command(label="Novo Índice", command=novo_indice)
    menuFerramentas.add_command(label="Gerar Pagamento Automático", command=abrir_gerar_pagamento)
    menuFerramentas.add_command(label="Gerar Relatório de Pagamentos", command=abrir_gerar_relatorio)
    # Adiciona o submenu "Exportar para Excel" ao menu "Ferramentas"
    menuFerramentas.add_command(label="Gerar Documento de Empenho", command=abrir_gerar_doc_empenho)
    menuFerramentas.add_command(label="Gerar Comprovante de Rendimentos", command=abrir_gerar_comprovante_rendimentos)
    menuFerramentas.add_command(label="Gerar Fita de Crédito", command=janela_gerar_txt_fita_credito)
    if str(perfil_usuario_logado) == "1":
        menuFerramentas.add_command(label="Folha de Pagamento (Fechar/Reabrir)", command=lambda: fechar_abrir_folha_pagamento("FECHAR"), state="normal")
    else:
        menuFerramentas.add_command(label="Folha de Pagamento (Fechar/Reabrir)", command=lambda: fechar_abrir_folha_pagamento("FECHAR"), state="disabled")
    menuFerramentas.add_cascade(label="Exportar para Excel", menu=menuExportar)

    
    if str(perfil_usuario_logado) == "1":
        menuCadastro.entryconfig("Cadastrar Usuário", state="normal")
        print("passou pelo if")
    else:
        menuCadastro.entryconfig("Cadastrar Usuário", state="disabled")
        print("passou pelo else", perfil_usuario_logado)
        
    menuBarra.add_cascade(label="Cadastro", menu=menuCadastro)
    menuBarra.add_cascade(label="Ferramentas", menu=menuFerramentas)
    
    janelaPrincipal.config(menu=menuBarra)
    
    frame_central = ctk.CTkFrame(janelaPrincipal, fg_color="#f0f4f8")
    frame_central.pack(expand=True, fill="both", padx=1, pady=1)

    # Título centralizado
    lb_titulo = ctk.CTkLabel(
        frame_central,
        text="Sistema de Gestão das Pensões Indenizatórias",
        font=('Calibri', 22, 'bold'),
        text_color="#d37b08"
    )
    lb_titulo.pack(pady=(50, 10))

    # # Usuário logado
    lb_usuario = ctk.CTkLabel(
        frame_central,
        text=f"Usuário logado: 👤 {usuario_logado}",
        font=('Calibri', 14, 'bold'),
        text_color="#000000"
    )
    lb_usuario.pack(pady=(0, 20))

    
    def fechar_app():
        if messagebox.askokcancel("Sair", "Você tem certeza que deseja sair?"):
            janelaPrincipal.destroy()
            sys.exit()
            
    def trocar_usuario():
        if messagebox.askokcancel("Trocar de Usuário", "Você deseja trocar de usuário?"):
            janelaPrincipal.destroy()
            login()
            
    frame_adicionar = ctk.CTkFrame(frame_central, fg_color="transparent")
    frame_adicionar.pack(pady=10)
    
    frame_adicionar2 = ctk.CTkFrame(frame_central, fg_color="transparent")
    frame_adicionar2.pack(pady=10)
    
    frame_sair = ctk.CTkFrame(frame_central, fg_color="transparent")
    frame_sair.pack(pady=50)
    
    btn_beneficiarios = ctk.CTkButton(frame_adicionar, text="➕ Cadastro Beneficiário", width=110, command=cadastro_beneficiarios, fg_color="#a1970c", hover_color="#d37b08", text_color="#fff", corner_radius=18)
    btn_beneficiarios.grid(row=0, column=0, padx=10, pady=5)
    
    btn_pagamentos = ctk.CTkButton(frame_adicionar, text="➕ Cadastro Pagamento", width=110, command=cadastro_pagamentos, fg_color="#a1970c", hover_color="#d37b08", text_color="#fff", corner_radius=18)
    btn_pagamentos.grid(row=1, column=0, padx=10, pady=5)
    
    # btn_anexos = ctk.CTkButton(frame_adicionar, text="➕ Anexar Documento", width=90, command=lambda: messagebox.showinfo("Info", "Funcionalidade em desenvolvimento!"), fg_color="#a1970c", hover_color="#d37b08", text_color="#fff", corner_radius=18)
    # btn_anexos.grid(row=2, column=0, padx=10, pady=5)
    
    btn_listar_beneficiarios = ctk.CTkButton(frame_adicionar, text="📝 Relação de Beneficiário", width=110, command=listar_beneficiarios, fg_color="#a1970c", hover_color="#d37b08", text_color="#fff", corner_radius=18)
    btn_listar_beneficiarios.grid(row=0, column=1, padx=10, pady=5)
    
    btn_listar_pagamentos = ctk.CTkButton(frame_adicionar, text="📝 Relação de Parâmetros", width=110, command=listar_pagamentos, fg_color="#a1970c", hover_color="#d37b08", text_color="#fff", corner_radius=18)
    btn_listar_pagamentos.grid(row=1, column=1, padx=10, pady=5)
    
    btn_listar_representantes = ctk.CTkButton(frame_adicionar2, text="📝 Relação de Responsáveis", width=150, command=listar_representantes_legais, fg_color="#a1970c", hover_color="#d37b08", text_color="#fff", corner_radius=18)
    btn_listar_representantes.grid(row=0, column=1, padx=10, pady=5)
    
    btn_pagamentos_gerados = ctk.CTkButton(frame_adicionar2, text="💲 Pagamentos Gerados", width=150, command=listar_pagamentos_gerados, fg_color="#a1970c", hover_color="#d37b08", text_color="#fff", corner_radius=18)
    btn_pagamentos_gerados.grid(row=0, column=0, padx=10, pady=5)
    
    btn_auditoria_indices = ctk.CTkButton(frame_adicionar2, text="📝 Relação de Índices", width=150, command=listar_auditoria_indices, fg_color="#6c757d", hover_color="#5a6268", text_color="#fff", corner_radius=18)
    btn_auditoria_indices.grid(row=1, column=0, columnspan=2, padx=10, pady=5)
    
    btn_status_folha = ctk.CTkButton(frame_adicionar2, text="📄 Relação da Folha", width=150, command=listar_folhas_pagamento, fg_color="#6c757d", hover_color="#5a6268", text_color="#fff", corner_radius=18)
    btn_status_folha.grid(row=2, column=0, columnspan=2, padx=10, pady=5)
    
    btn_trocar_usuario = ctk.CTkButton(frame_sair, text="Trocar de Usuário", width=30, command=trocar_usuario, fg_color="#a1970c", hover_color="#d37b08", text_color="#fff", corner_radius=18)
    btn_trocar_usuario.grid(row=0, column=0, padx=10, pady=5)
    
    
    lb_rodape = ctk.CTkLabel(
        frame_central, text="© 2025 julio.slima - SEEC", font=('Calibri', 10, 'italic'), text_color="#c0a50a"
    )
    lb_rodape.pack(side="bottom", pady=(10, 0))
    
    janelaPrincipal.protocol("WM_DELETE_WINDOW", fechar_app)
    janelaPrincipal.mainloop()
    
#==============================================================================================#


def cadastro_beneficiarios():
    def salvar_beneficiario():
        nome = entry_nome.get().strip()
        cpf = entry_cpf.get().strip()
        endereco = entry_endereco.get().strip()
        cep = entry_cep.get().strip()
        telefone = entry_telefone.get().strip()
        processo = entry_processo.get().strip()
        numero_processo_sei = entry_processo_sei.get().strip()
        origem_decisao = entry_origem_decisao.get().strip()
        numero_vara = entry_numero_vara.get().strip()
        agencia = entry_agencia.get().strip()
        numero_conta = entry_numero_conta.get().strip()
        numero_banco = entry_numero_banco.get().strip()
        tipo_conta = combo_tipo_conta.get().strip()
        menor_ou_incapaz = var_menor_incapaz.get()
        # prazo_pagamento_tipo = combo_prazo_tipo.get()
        # prazo_pagamento_valor = entry_prazo_valor.get().strip()
        data_decisao = entry_data_decisao.get().strip()
        data_oficio = entry_data_oficio.get().strip()
        identidade = entry_identidade.get().strip()
        orgao_emissor_id = entry_orgao_emissor.get().strip()
        observacoes = entry_observacoes.get("1.0", tk.END).strip()
        descricao_do_banco = entry_descricao_banco.get().strip()
        codigo_orgao = entry_código_orgao.get().strip()
        codigo_folha = entry_código_folha.get().strip()
        codigo_uf = entry_uf.get().strip()
        digito_conta = entry_digito_conta.get().strip() 
        email = entry_email.get().strip()
        data_nascimento = entry_data_nascimento.get().strip()
        naturalidade = entry_naturalidade.get().strip()
        

        if not (nome and cpf and processo):
            messagebox.showerror("Erro", "Nome, CPF e Processo Judicial são obrigatórios!")
            return

        conn = sqlite3.connect(resource_path('banco.db'))
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO beneficiarios (
                    nome_completo, cpf, email, endereco, cep, telefone, numero_processo_judicial, numero_processo_sei,
                    origem_decisao, numero_vara, agencia, numero_conta, numero_banco, tipo_conta, menor_ou_incapaz,
                    data_decisao, data_oficioPGDF, observacoes, descricao_banco, codigoorgao, codigofolha, codigouf, agenciaconta, digitoconta, identidade, orgao_emissor, data_nascimento, naturalidade
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                nome, cpf, email, endereco, cep, telefone, processo, numero_processo_sei,
                origem_decisao, numero_vara, agencia, numero_conta, numero_banco, tipo_conta, menor_ou_incapaz,
                data_decisao, data_oficio, observacoes, descricao_do_banco, codigo_orgao, codigo_folha, codigo_uf, agencia, digito_conta, identidade, orgao_emissor_id, data_nascimento, naturalidade
            ))
            conn.commit()
            janelaBeneficiarios.destroy()
        except sqlite3.IntegrityError as e:
            messagebox.showerror("Erro", f"CPF ou Processo já cadastrado!\n{e}")
        finally:
            conn.close()
        
    janelaBeneficiarios = ctk.CTkToplevel()
    janelaBeneficiarios.title("Cadastro Beneficiário")
    janelaBeneficiarios.geometry("450x750")
    janelaBeneficiarios.wm_attributes("-topmost", True)
    ctk.set_default_color_theme("blue")

    # Frame com rolagem
    scroll_frame = ctk.CTkScrollableFrame(janelaBeneficiarios, width=420, height=650)
    scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    ctk.CTkLabel(scroll_frame, text="*Nome Completo:").pack(pady=3)
    entry_nome = ctk.CTkEntry(scroll_frame, width=200)
    entry_nome.pack(pady=2)

    ctk.CTkLabel(scroll_frame, text="*CPF:").pack(pady=3)
    entry_cpf = ctk.CTkEntry(scroll_frame, width=200)
    entry_cpf.pack(pady=2)

    ctk.CTkLabel(scroll_frame, text="Identidade:").pack(pady=3)
    entry_identidade = ctk.CTkEntry(scroll_frame, width=200)
    entry_identidade.pack(pady=2)
    
    ctk.CTkLabel(scroll_frame, text="Data de Nascimento (DD-MM-AAAA):").pack(pady=3)
    entry_data_nascimento = ctk.CTkEntry(scroll_frame, width=200)
    entry_data_nascimento.pack(pady=2)
    
    ctk.CTkLabel(scroll_frame, text="Naturalidade:").pack(pady=3)
    entry_naturalidade = ctk.CTkEntry(scroll_frame, width=200)
    entry_naturalidade.pack(pady=2)

    ctk.CTkLabel(scroll_frame, text="Órgão Emissor:").pack(pady=3)
    entry_orgao_emissor = ctk.CTkEntry(scroll_frame, width=200)
    entry_orgao_emissor.pack(pady=2)
    
    ctk.CTkLabel(scroll_frame, text="Email:").pack(pady=3)
    entry_email = ctk.CTkEntry(scroll_frame, width=200)
    entry_email.pack(pady=2)

    ctk.CTkLabel(scroll_frame, text="Endereço:").pack(pady=3)
    entry_endereco = ctk.CTkEntry(scroll_frame, width=200)
    entry_endereco.pack(pady=2)

    ctk.CTkLabel(scroll_frame, text="CEP:").pack(pady=3)
    entry_cep = ctk.CTkEntry(scroll_frame, width=200)
    entry_cep.pack(pady=2)

    ctk.CTkLabel(scroll_frame, text="Telefone:").pack(pady=3)
    entry_telefone = ctk.CTkEntry(scroll_frame, width=200)
    entry_telefone.pack(pady=2)
    
    ctk.CTkLabel(scroll_frame, text="Código do Órgão:").pack(pady=3)
    entry_código_orgao = ctk.CTkEntry(scroll_frame, width=200)
    entry_código_orgao.pack(pady=2)
    entry_código_orgao.insert(0, "32007")
    
    ctk.CTkLabel(scroll_frame, text="Código da Folha").pack(pady=3)
    entry_código_folha = ctk.CTkEntry(scroll_frame, width=200)
    entry_código_folha.pack(pady=2)
    entry_código_folha.insert(0, "001")
    
    ctk.CTkLabel(scroll_frame, text="Número do Banco:").pack(pady=3)
    entry_numero_banco = ctk.CTkEntry(scroll_frame, width=200)
    entry_numero_banco.pack(pady=2)
    
    def preencher_agencia(event=None):
        numero_banco = entry_numero_banco.get().strip()
        nome_banco = BANCOS.get(numero_banco, "")
        entry_descricao_banco.delete(0, tk.END)
        entry_descricao_banco.insert(0, nome_banco)
        
    ctk.CTkLabel(scroll_frame, text="Descrição do banco:").pack(pady=3)
    entry_descricao_banco = ctk.CTkEntry(scroll_frame, width=200)
    entry_descricao_banco.pack(pady=2)
    
    ctk.CTkLabel(scroll_frame, text="Agência:").pack(pady=3)
    entry_agencia = ctk.CTkEntry(scroll_frame, width=200)
    entry_agencia.pack(pady=2)
    
    ctk.CTkLabel(scroll_frame, text="UF:").pack(pady=3)
    entry_uf = ctk.CTkEntry(scroll_frame, width=200)
    entry_uf.pack(pady=2)
    
    ctk.CTkLabel(scroll_frame, text="Tipo de Conta:").pack(pady=3)
    combo_tipo_conta = ctk.CTkComboBox(scroll_frame, width=200, values=["Corrente", "Poupança", "Judicial"])
    combo_tipo_conta.pack(pady=2)
    combo_tipo_conta.set("Corrente")
        
    ctk.CTkLabel(scroll_frame, text="Número da Conta:").pack(pady=3)
    entry_numero_conta = ctk.CTkEntry(scroll_frame, width=200)
    entry_numero_conta.pack(pady=2)
    
    ctk.CTkLabel(scroll_frame, text="Dígito da Conta:").pack(pady=3)
    entry_digito_conta = ctk.CTkEntry(scroll_frame, width=200)
    entry_digito_conta.pack(pady=2)
    
    var_menor_incapaz = tk.IntVar()
    def abrir_popup_representante():
        def salvar_representante():
            nome_rep = entry_nome_rep.get().strip()
            identidade = entry_identidade_rep.get().strip()
            cpf_rep = entry_cpf_rep.get().strip()
            orgao_emissor = entry_orgao_emissor.get().strip()
            endereco_rep = entry_endereco_rep.get().strip()
            telefone_rep = entry_telefone_rep.get().strip()
            agencia_rep = entry_agencia_rep.get().strip()
            numero_conta_rep = entry_numero_conta_rep.get().strip()
            tipo_conta_rep = combo_tipo_conta_rep.get().strip()
            email_rep = entry_email_rep.get().strip()
            digito_conta_rep = entry_digito_conta_rep.get().strip()
            numero_banco_rep = entry_numero_banco_rep.get().strip()
            descricao_banco_rep = entry_descricao_banco_rep.get().strip()

            if not (nome_rep and cpf_rep and identidade):
                messagebox.showerror("Erro", "Nome, CPF e Identidade do representante são obrigatórios!")
                return

            conn = sqlite3.connect(resource_path('banco.db'))
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO representantes_legais (
                        nome_completo, identidade, cpf, orgao_emissor, endereco, telefone, agencia, numero_conta, tipo_conta, numero_banco, cpf_beneficiario, descricao_banco, email, digitoconta
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    nome_rep, identidade, cpf_rep, orgao_emissor, endereco_rep, telefone_rep,
                    agencia_rep, numero_conta_rep, tipo_conta_rep, numero_banco_rep, entry_cpf.get().strip(), descricao_banco_rep, email_rep, digito_conta_rep
                ))
                conn.commit()
                popup.destroy()
            except sqlite3.IntegrityError as e:
                messagebox.showerror("Erro", f"CPF ou Identidade do representante já cadastrado!\n{e}")
            finally:
                conn.close()
        
        
        popup = ctk.CTkToplevel()
        popup.title("Cadastrar Representante Legal")
        popup.geometry("400x500")
        popup.transient(janelaBeneficiarios)  # Torna o popup modal
        popup.wm_attributes("-topmost", True)
        ctk.set_default_color_theme("blue")

        # Frame com rolagem
        scroll_frame_popup = ctk.CTkScrollableFrame(popup, width=420, height=650)
        scroll_frame_popup.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(scroll_frame_popup, text="Nome Completo:").pack(pady=3)
        entry_nome_rep = ctk.CTkEntry(scroll_frame_popup, width=200)
        entry_nome_rep.pack(pady=2)
        
        ctk.CTkLabel(scroll_frame_popup, text="CPF:").pack(pady=3)
        entry_cpf_rep = ctk.CTkEntry(scroll_frame_popup, width=200)
        entry_cpf_rep.pack(pady=2)
        
        ctk.CTkLabel(scroll_frame_popup, text="Identidade:").pack(pady=3)
        entry_identidade_rep = ctk.CTkEntry(scroll_frame_popup, width=200)
        entry_identidade_rep.pack(pady=2)

        ctk.CTkLabel(scroll_frame_popup, text="Órgão Emissor:").pack(pady=3)
        entry_orgao_emissor = ctk.CTkEntry(scroll_frame_popup, width=200)
        entry_orgao_emissor.pack(pady=2)
        
        ctk.CTkLabel(scroll_frame_popup, text="Email:").pack(pady=3)
        entry_email_rep = ctk.CTkEntry(scroll_frame_popup, width=200)
        entry_email_rep.pack(pady=2)
        
        ctk.CTkLabel(scroll_frame_popup, text="Endereço:").pack(pady=3)
        entry_endereco_rep = ctk.CTkEntry(scroll_frame_popup, width=200)
        entry_endereco_rep.pack(pady=2)
        
        ctk.CTkLabel(scroll_frame_popup, text="Telefone:").pack(pady=3)
        entry_telefone_rep = ctk.CTkEntry(scroll_frame_popup, width=200)
        entry_telefone_rep.pack(pady=2)
        
        
        ctk.CTkLabel(scroll_frame_popup, text="Número do Banco:").pack(pady=3)
        entry_numero_banco_rep = ctk.CTkEntry(scroll_frame_popup, width=200)
        entry_numero_banco_rep.pack(pady=2)
        
        def preencher_agencia_rep(event=None):
            numero_banco = entry_numero_banco_rep.get().strip()
            nome_banco = BANCOS.get(numero_banco, "")
            entry_descricao_banco_rep.delete(0, tk.END)
            entry_descricao_banco_rep.insert(0, nome_banco)
            
        ctk.CTkLabel(scroll_frame_popup, text="Descrição do banco:").pack(pady=3)
        entry_descricao_banco_rep = ctk.CTkEntry(scroll_frame_popup, width=200)
        entry_descricao_banco_rep.pack(pady=2)
        
        ctk.CTkLabel(scroll_frame_popup, text="Agência:").pack(pady=3)
        entry_agencia_rep = ctk.CTkEntry(scroll_frame_popup, width=200)
        entry_agencia_rep.pack(pady=2)
        
        ctk.CTkLabel(scroll_frame_popup, text="Tipo de Conta:").pack(pady=3)
        combo_tipo_conta_rep = ctk.CTkComboBox(scroll_frame_popup, width=200, values=["Corrente", "Poupança", "Judicial"])
        combo_tipo_conta_rep.pack(pady=2)
        combo_tipo_conta_rep.set("Corrente")
        
        ctk.CTkLabel(scroll_frame_popup, text="Número da Conta:").pack(pady=3)
        entry_numero_conta_rep = ctk.CTkEntry(scroll_frame_popup, width=200)
        entry_numero_conta_rep.pack(pady=2)
        
        ctk.CTkLabel(scroll_frame_popup, text="Dígito da Conta:").pack(pady=3)
        entry_digito_conta_rep = ctk.CTkEntry(scroll_frame_popup, width=200)
        entry_digito_conta_rep.pack(pady=2)
        

        ctk.CTkButton(scroll_frame_popup, text="Salvar", command=salvar_representante, fg_color="#a1970c", hover_color="#d37b08", text_color="#fff", corner_radius=18).pack(pady=10)
        ctk.CTkButton(scroll_frame_popup, text="Cancelar", command=popup.destroy, fg_color="#a1970c", hover_color="#d37b08", text_color="#fff", corner_radius=18).pack(pady=5)

        #===============================================================================================#
        
        def aplicar_mascara_cpf(event):
            valor = entry_cpf_rep.get().replace(".", "").replace("-", "")[:11]
            novo = ""
            if len(valor) > 0:
                novo += valor[:3]
            if len(valor) > 3:
                novo += "." + valor[3:6]
            if len(valor) > 6:
                novo += "." + valor[6:9]
            if len(valor) > 9:
                novo += "-" + valor[9:11]
            entry_cpf_rep.delete(0, tk.END)
            entry_cpf_rep.insert(0, novo)
            
        def aplicar_mascara_telefone(event):
            valor = entry_telefone_rep.get().replace("(", "").replace(")", "").replace("-", "").replace(" ", "")[:11]
            novo = ""
            if len(valor) > 0:
                novo += "(" + valor[:2] + ") "
            if len(valor) > 2 and len(valor) <= 7:
                novo += valor[2:6] + "-" + valor[6:10]
            elif len(valor) > 7:
                novo += valor[2:7] + "-" + valor[7:11]
            entry_telefone_rep.delete(0, tk.END)
            entry_telefone_rep.insert(0, novo)
            
        def aplicar_mascara_numero_banco(event):
            valor = entry_numero_banco_rep.get().replace("-", "")[:3]
            novo = ""
            if len(valor) > 0:
                novo += valor[:3]
            entry_numero_banco_rep.delete(0, tk.END)
            entry_numero_banco_rep.insert(0, novo)
            
        entry_cpf_rep.bind("<KeyRelease>", aplicar_mascara_cpf)
        entry_telefone_rep.bind("<KeyRelease>", aplicar_mascara_telefone)
        entry_numero_banco_rep.bind("<KeyRelease>", aplicar_mascara_numero_banco)
        entry_numero_banco_rep.bind("<KeyRelease>", preencher_agencia_rep)
        
        
    def on_menor_incapaz_change():
        if var_menor_incapaz.get():
            abrir_popup_representante()
            
    ctk.CTkCheckBox(scroll_frame, text="É menor ou incapaz?", variable=var_menor_incapaz, command=on_menor_incapaz_change).pack(pady=5)
    
    ctk.CTkLabel(scroll_frame, text="Nº Processo SEI:").pack(pady=3)
    entry_processo_sei = ctk.CTkEntry(scroll_frame, width=200)
    entry_processo_sei.pack(pady=2)
    
    ctk.CTkLabel(scroll_frame, text="*Nº Processo Judicial:").pack(pady=3)
    entry_processo = ctk.CTkEntry(scroll_frame, width=200)
    entry_processo.pack(pady=2)

    ctk.CTkLabel(scroll_frame, text="Origem da Decisão:").pack(pady=3)
    entry_origem_decisao = ctk.CTkEntry(scroll_frame, width=200)
    entry_origem_decisao.pack(pady=2)
    
    ctk.CTkLabel(scroll_frame, text="Número da Vara:").pack(pady=3)
    entry_numero_vara = ctk.CTkEntry(scroll_frame, width=200)
    entry_numero_vara.pack(pady=2)
    
    ctk.CTkLabel(scroll_frame, text="Data Decisão (DD-MM-AAAA):").pack(pady=3)
    entry_data_decisao = ctk.CTkEntry(scroll_frame, width=200)
    entry_data_decisao.pack(pady=2)
    
    ctk.CTkLabel(scroll_frame, text="Data do Ofício PGDF (DD-MM-AAAA):").pack(pady=3)
    entry_data_oficio = ctk.CTkEntry(scroll_frame, width=200)
    entry_data_oficio.pack(pady=2)
    
    entry_numero_banco.bind("<KeyRelease>", preencher_agencia)
    
    




    



    # ctk.CTkLabel(scroll_frame, text="Prazo de Pagamento:").pack(pady=3)
    # combo_prazo_tipo = ctk.CTkComboBox(scroll_frame, width=200, values=["Parcelado", "Vitalício"])
    # combo_prazo_tipo.pack(pady=2)
    # combo_prazo_tipo.set("Parcelado")
    
    # ctk.CTkLabel(scroll_frame, text="Nº de Parcelas (ou deixe em branco para vitalício):").pack(pady=3)
    # entry_prazo_valor = ctk.CTkEntry(scroll_frame, width=200)
    # entry_prazo_valor.pack(pady=2)

    ctk.CTkLabel(scroll_frame, text="Ementa da decisão:").pack(pady=3)
    entry_observacoes = tk.Text(scroll_frame, width=38, height=4)
    entry_observacoes.pack(pady=2)


    ctk.CTkButton(scroll_frame, text="Salvar", command=salvar_beneficiario, fg_color="#a1970c", hover_color="#d37b08", text_color="#fff", corner_radius=18).pack(pady=10)
    ctk.CTkButton(scroll_frame, text="Cancelar", command=janelaBeneficiarios.destroy, fg_color="#a1970c", hover_color="#d37b08", text_color="#fff", corner_radius=18).pack(pady=5)

#==============================================================================================#

    def aplicar_mascara_cpf(event):
        valor = entry_cpf.get().replace(".", "").replace("-", "")[:11]
        novo = ""
        if len(valor) > 0:
            novo += valor[:3]
        if len(valor) > 3:
            novo += "." + valor[3:6]
        if len(valor) > 6:
            novo += "." + valor[6:9]
        if len(valor) > 9:
            novo += "-" + valor[9:11]
        entry_cpf.delete(0, tk.END)
        entry_cpf.insert(0, novo)

    def aplicar_mascara_cep(event):
        valor = entry_cep.get().replace("-", "")[:8]
        novo = ""
        if len(valor) > 0:
            novo += valor[:5]
        if len(valor) > 5:
            novo += "-" + valor[5:8]
        entry_cep.delete(0, tk.END)
        entry_cep.insert(0, novo)

    def aplicar_mascara_telefone(event):
        valor = entry_telefone.get().replace("(", "").replace(")", "").replace("-", "").replace(" ", "")[:11]
        novo = ""
        if len(valor) > 0:
            novo += "(" + valor[:2] + ") "
        if len(valor) > 2 and len(valor) <= 7:
            novo += valor[2:6] + "-" + valor[6:10]
        elif len(valor) > 7:
            novo += valor[2:7] + "-" + valor[7:11]
        entry_telefone.delete(0, tk.END)
        entry_telefone.insert(0, novo)

    def aplicar_mascara_data(event):
        valor = entry_data_decisao.get().replace("-", "")[:8]
        novo = ""
        if len(valor) > 0:
            novo += valor[:2]
        if len(valor) > 2:
            novo += "-" + valor[2:4]
        if len(valor) > 4:
            novo += "-" + valor[4:8]
        entry_data_decisao.delete(0, tk.END)
        entry_data_decisao.insert(0, novo)
        
    def aplicar_mascara_data_oficio(event):
        valor = entry_data_oficio.get().replace("-", "")[:8]
        novo = ""
        if len(valor) > 0:
            novo += valor[:2]
        if len(valor) > 2:
            novo += "-" + valor[2:4]
        if len(valor) > 4:
            novo += "-" + valor[4:8]
        entry_data_oficio.delete(0, tk.END)
        entry_data_oficio.insert(0, novo)
        
    def aplicar_mascara_data_nascimento(event):
        valor = entry_data_nascimento.get().replace("-", "")[:8]
        novo = ""
        if len(valor) > 0:
            novo += valor[:2]
        if len(valor) > 2:
            novo += "-" + valor[2:4]
        if len(valor) > 4:
            novo += "-" + valor[4:8]
        entry_data_nascimento.delete(0, tk.END)
        entry_data_nascimento.insert(0, novo)
        
    def aplicar_mascara_numero_banco(event):
        valor = entry_numero_banco.get().replace("-", "")[:3]
        novo = ""
        if len(valor) > 0:
            novo += valor[:3]
        entry_numero_banco.delete(0, tk.END)
        entry_numero_banco.insert(0, novo)


    # Após criar os campos:
    entry_cpf.bind("<KeyRelease>", aplicar_mascara_cpf)
    entry_cep.bind("<KeyRelease>", aplicar_mascara_cep)
    entry_telefone.bind("<KeyRelease>", aplicar_mascara_telefone)
    entry_data_decisao.bind("<KeyRelease>", aplicar_mascara_data)
    entry_data_oficio.bind("<KeyRelease>", aplicar_mascara_data_oficio)
    entry_numero_banco.bind("<KeyRelease>", aplicar_mascara_numero_banco)
    entry_data_nascimento.bind("<KeyRelease>", aplicar_mascara_data_nascimento)


#==============================================================================================#

def listar_beneficiarios():
    conn = sqlite3.connect(resource_path('banco.db'))
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            b.id, b.nome_completo, b.menor_ou_incapaz, b.cpf, b.identidade, b.data_nascimento, b.naturalidade, b.orgao_emissor, b.email, r.nome_completo, b.endereco, b.cep, b.telefone, 
            b.numero_processo_judicial, b.numero_processo_sei, b.origem_decisao, b.numero_vara,
            b.agencia, b.numero_conta, b.digitoconta, b.numero_banco, b.descricao_banco, b.tipo_conta,
            b.data_decisao, b.data_oficioPGDF, b.observacoes
        FROM beneficiarios b
        LEFT JOIN representantes_legais r ON b.cpf = r.cpf_beneficiario
    """)
    beneficiarios = cursor.fetchall()
    conn.close()

    if not beneficiarios:
        messagebox.showinfo("Info", "Nenhum beneficiário cadastrado.")
        return

    janelaListarBeneficiarios = ctk.CTkToplevel()
    janelaListarBeneficiarios.title("Lista de Beneficiários")
    janelaListarBeneficiarios.geometry("1100x550")
    # Do not force this window to be always-on-top; that made it stay above everything.
    # If you want it transient to the main/root window, use: janelaListarBeneficiarios.transient(root)
    # janelaListarBeneficiarios.wm_attributes("-topmost", True)
    ctk.set_default_color_theme("blue")
    
    # Frame principal que ocupa toda a janela
    main_frame = ctk.CTkFrame(janelaListarBeneficiarios)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)
    main_frame.grid_rowconfigure(0, weight=1)
    main_frame.grid_columnconfigure(0, weight=1)
    
    # Frame para a tabela e as barras de rolagem
    tree_frame = ctk.CTkFrame(main_frame)
    tree_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
    tree_frame.grid_rowconfigure(0, weight=1)
    tree_frame.grid_columnconfigure(0, weight=1)
    
    # Estilo já é configurado globalmente, não precisa repetir aqui
    style = ttk.Style() 
    style.theme_use("default") 
    style.configure("Treeview", background="#ffffff", foreground="black", rowheight=25, fieldbackground="#ffffff")
    
    # Cor de seleção
    style.map('Treeview', background=[('selected', '#a1970c')])

    # Configuração do cabeçalho (a opção show='headings' já cria as linhas divisórias)
    style.configure("Treeview.Heading", font=('Calibri', 10, 'bold'))

    colunas = (
        "ID", "Nome", "Menor/Incapaz", "CPF", "Identidade", "Data de Nascimento", "Naturalidade", "Órgão Emissor", "Email", "Responsável Legal", "Endereço", "CEP", "Telefone",
        "Proc. Judicial", "Proc. SEI", "Origem Decisão", "Nº Vara",
        "Agência", "Conta", "Dígito", "Nº Banco", "Descrição do Banco", "Tipo Conta",
        "Data Decisão", "Data PGDF", "Ementa da Decisão"
    )
    tree = ttk.Treeview(tree_frame, columns=colunas, show='headings')
    
    for col in colunas:
        tree.heading(col, text=col, command=lambda c=col: sort_by_column(tree, c, False))
        tree.column(col, width=120, anchor='center')
    
    scrollbar_vertical = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    scrollbar_horizontal = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=scrollbar_vertical.set, xscrollcommand=scrollbar_horizontal.set)
    tree.grid(row=0, column=0, sticky='nsew')
    scrollbar_vertical.grid(row=0, column=1, sticky='ns')
    scrollbar_horizontal.grid(row=1, column=0, sticky='ew')

    # Tags para cores de linha alternadas (efeito "zebra")
    tree.tag_configure('oddrow', background='#F0F0F0') # Cinza claro
    tree.tag_configure('evenrow', background='white')

    for i, beneficiario in enumerate(beneficiarios):
        beneficiario = ["" if valor is None else valor for valor in beneficiario]
        beneficiario[2] = "Sim" if beneficiario[2] else "Não"  # menor_ou_incapaz
        tree.insert("", tk.END, values=beneficiario, tags=('evenrow' if i % 2 == 0 else 'oddrow',))
        
    def carregar_processos():
        for item in tree.get_children():
            tree.delete(item)
            
        try:
            conn = sqlite3.connect(resource_path('banco.db'), timeout=10)
            cursor = conn.cursor()
            
            query = """
                SELECT
                    b.id, b.nome_completo, b.menor_ou_incapaz, b.cpf, b.identidade, b.data_nascimento, b.naturalidade, b.orgao_emissor, b.email, r.nome_completo, b.endereco, b.cep, b.telefone,
                    b.numero_processo_judicial, b.numero_processo_sei, b.origem_decisao, 
                    b.numero_vara, b.agencia, b.numero_conta, b.digitoconta, b.numero_banco, b.descricao_banco, b.tipo_conta, 
                    b.data_decisao, b.data_oficioPGDF, b.observacoes
                FROM beneficiarios b
                LEFT JOIN representantes_legais r ON b.cpf = r.cpf_beneficiario
            """
            cursor.execute(query)
            processos = cursor.fetchall()
            
            for i, processo in enumerate(processos):
                processo_tratado = tuple("" if valor is None else valor for valor in processo)
                tag = 'evenrow' if i % 2 == 0 else 'oddrow'
                tree.insert("", "end", values=processo_tratado, tags=(tag,))
                
        except sqlite3.OperationalError as e:
            messagebox.showerror("Erro", f"Erro ao carregar os processos: {e}")
        finally:
            if conn:
                conn.close()
    
    # Frame para os controles (filtro e botão)
    controls_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    controls_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=(5,0))
    
    ctk.CTkLabel(controls_frame, text="Filtrar:", font=('Calibri', 14, 'italic'), text_color="black").pack(side="left", padx=(0, 5))
    entry_filtro = ctk.CTkEntry(controls_frame, width=200)
    entry_filtro.pack(side="left", fill="x")
    
    
    btn_atualizar = ctk.CTkButton(controls_frame, text="Atualizar", width=100, command=carregar_processos, fg_color="#a1970c", hover_color="#d37b08", text_color="#fff", corner_radius=18)
    btn_atualizar.pack(side="right", padx=(10, 0))

    def filtrar_beneficiarios(event=None):
        filtro = entry_filtro.get().strip().lower()
        for item in tree.get_children():
            tree.delete(item)
        for i, beneficiario in enumerate(beneficiarios):
            beneficiario_str = [str("" if valor is None else valor).lower() for valor in beneficiario]
            if any(filtro in campo for campo in beneficiario_str):
                beneficiario_exibido = ["" if valor is None else valor for valor in beneficiario]
                beneficiario_exibido[2] = "Sim" if beneficiario_exibido[2] else "Não"  # menor_ou_incapaz
                tag = 'evenrow' if i % 2 == 0 else 'oddrow'
                tree.insert("", tk.END, values=beneficiario_exibido, tags=(tag,))

    entry_filtro.bind("<KeyRelease>", filtrar_beneficiarios)
    
    def sort_by_column(tree, col, descending):
        data = [(tree.set(child, col), child) for child in tree.get_children('')]

        try:
            data.sort(key=lambda t: float(t[0]) if t[0].replace('.', '', 1).isdigit() else t[0], reverse=descending)
        except ValueError:
            data.sort(key=lambda t: t[0], reverse=descending)

        for index, (val, child) in enumerate(data):
            tree.move(child, '', index)

        tree.heading(col, command=lambda: sort_by_column(tree, col, not descending))

    def on_double_click(event):
        item = tree.selection()
        if item:
            id_beneficiario = tree.item(item, "values")[0]
            editar_beneficiario(id_beneficiario)
        
    tree.bind("<Double-1>", on_double_click)
    
#==============================================================================================#

    def editar_beneficiario(id_beneficiario):
        conn = sqlite3.connect(resource_path('banco.db'))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT nome_completo, cpf, identidade, orgao_emissor, email, endereco, cep, telefone, numero_processo_judicial,
                    numero_processo_sei, origem_decisao, numero_vara, agencia, numero_conta,
                    numero_banco, tipo_conta, menor_ou_incapaz,
                    data_decisao, data_oficioPGDF, observacoes, descricao_banco, codigoorgao, codigofolha, codigouf, digitoconta, data_nascimento, naturalidade
            FROM beneficiarios WHERE id = ?
        """, (id_beneficiario,))
        dados = cursor.fetchone()
        conn.close()

        if not dados:
            messagebox.showerror("Erro", "Beneficiário não encontrado!")
            return
        
        nome, cpf, identidade, orgao_emissor, email, endereco, cep, telefone, processo_judicial, numero_processo_sei, origem_decisao, numero_vara, agencia, numero_conta, numero_banco, tipo_conta, menor_ou_incapaz, data_decisao, data_oficio, observacoes, descricao_do_banco, codigo_orgao, codigo_folha, codigo_uf, digito_conta, data_de_nascimento, naturalidade  = dados
        
        def salvar_edicoes():
            novo_nome = entry_nome.get().strip()
            novo_cpf = entry_cpf.get().strip()
            novo_endereco = entry_endereco.get().strip()
            novo_cep = entry_cep.get().strip()
            novo_telefone = entry_telefone.get().strip()
            novo_processo = entry_processo.get().strip()
            novo_numero_processo_sei = entry_processo_sei.get().strip()
            nova_origem_decisao = entry_origem_decisao.get().strip()
            novo_numero_vara = entry_numero_vara.get().strip()
            nova_agencia = entry_agencia.get().strip()
            novo_numero_conta = entry_numero_conta.get().strip()
            novo_numero_banco = entry_numero_banco.get().strip()
            novo_tipo_conta = combo_tipo_conta.get().strip()
            novo_menor_incapaz = var_menor_incapaz.get()
            # novo_prazo_tipo = combo_prazo_tipo.get()
            # novo_prazo_valor = entry_prazo_valor.get().strip()
            nova_data_decisao = entry_data_decisao.get().strip()
            nova_data_oficio = entry_data_oficio.get().strip()
            nova_identidade = entry_identidade.get().strip()
            novo_orgao_emissor = entry_orgao_emissor.get().strip()
            novas_observacoes = entry_observacoes.get("1.0", tk.END).strip()
            nova_descricao_banco = entry_descricao_banco.get().strip()
            nova_codigo_orgao = entry_codigo_orgao.get().strip()
            nova_codigo_folha = entry_codigo_folha.get().strip()
            nova_codigo_uf = entry_codigo_uf.get().strip()
            nova_agencia_conta = nova_agencia # Usa o mesmo valor da agência de pagamento
            nova_digito_conta = entry_digito_conta.get().strip()
            novo_email = entry_email.get().strip()
            nova_data_de_nascimento = entry_data_nascimento.get().strip()
            nova_naturalidade = entry_naturalidade.get().strip()
            
            

            if not (novo_nome and novo_cpf and novo_processo):
                messagebox.showerror("Erro", "Nome, CPF e Processo Judicial são obrigatórios!")
                return
            
            conn = sqlite3.connect(resource_path('banco.db'))
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    UPDATE beneficiarios SET
                        nome_completo = ?, cpf = ?, identidade = ?, orgao_emissor = ?, email = ?, endereco = ?, cep = ?, telefone = ?, 
                        numero_processo_judicial = ?, numero_processo_sei = ?, origem_decisao = ?,
                        numero_vara = ?, agencia = ?, numero_conta = ?, numero_banco = ?, tipo_conta = ?, 
                        menor_ou_incapaz = ?, 
                        data_decisao = ?, data_oficioPGDF = ?, observacoes = ?, descricao_banco = ?, codigoorgao = ?, codigofolha = ?, codigouf = ?, agenciaconta = ?, digitoconta = ?,
                        data_nascimento = ?, naturalidade = ?
                    WHERE id = ?
                """, (
                    novo_nome, novo_cpf, nova_identidade, novo_orgao_emissor, novo_email, novo_endereco, novo_cep, novo_telefone, 
                    novo_processo, novo_numero_processo_sei, nova_origem_decisao,
                    novo_numero_vara, nova_agencia, novo_numero_conta, novo_numero_banco,
                    novo_tipo_conta, novo_menor_incapaz, nova_data_decisao, nova_data_oficio, novas_observacoes,
                    nova_descricao_banco, nova_codigo_orgao, nova_codigo_folha, nova_codigo_uf, nova_agencia, nova_digito_conta, nova_data_de_nascimento, nova_naturalidade,
                    id_beneficiario 
                ))
            
                conn.commit()
                janelaEditarBeneficiario.destroy()
                carregar_processos()
            except sqlite3.IntegrityError as e:
                messagebox.showerror("Erro", f"CPF ou Processo já cadastrado!\n{e}")
            finally:
                conn.close()
                
        janelaEditarBeneficiario = ctk.CTkToplevel(janelaListarBeneficiarios)
        janelaEditarBeneficiario.title("Editar Beneficiário")
        janelaEditarBeneficiario.geometry("450x750")
        janelaEditarBeneficiario.grab_set()
        ctk.set_default_color_theme("blue")

        # Frame para os botões, posicionado primeiro na parte inferior
        # frame_botoes = ctk.CTkFrame(janelaEditarBeneficiario, fg_color="transparent")
        # frame_botoes.pack(side="bottom", pady=10, fill="x")

        # Área de rolagem, posicionado depois para ocupar o espaço restante
        scroll_frame_edit = ctk.CTkScrollableFrame(janelaEditarBeneficiario)
        scroll_frame_edit.pack(fill="both", expand=True, padx=10, pady=5)

        # Botões são adicionados ao frame_botoes
        
        
        ctk.CTkLabel(scroll_frame_edit, text="Nome Completo:").pack(pady=3)
        entry_nome = ctk.CTkEntry(scroll_frame_edit, width=200)
        entry_nome.insert(0, str(nome) if nome is not None else "")
        entry_nome.pack(pady=2)
        
        ctk.CTkLabel(scroll_frame_edit, text="CPF:").pack(pady=3)
        entry_cpf = ctk.CTkEntry(scroll_frame_edit, width=200) 
        entry_cpf.insert(0, str(cpf) if cpf is not None else "")
        entry_cpf.pack(pady=2)

        ctk.CTkLabel(scroll_frame_edit, text="Identidade:").pack(pady=3)
        entry_identidade = ctk.CTkEntry(scroll_frame_edit, width=200)
        entry_identidade.insert(0, str(identidade) if identidade is not None else "")
        entry_identidade.pack(pady=2)
        
        ctk.CTkLabel(scroll_frame_edit, text="Data de Nascimento (DD-MM-AAAA):").pack(pady=3)
        entry_data_nascimento = ctk.CTkEntry(scroll_frame_edit, width=200)
        entry_data_nascimento.insert(0, str(data_de_nascimento) if data_de_nascimento is not None else "")
        entry_data_nascimento.pack(pady=2)
        
        ctk.CTkLabel(scroll_frame_edit, text="Naturalidade:").pack(pady=3)
        entry_naturalidade = ctk.CTkEntry(scroll_frame_edit, width=200)
        entry_naturalidade.insert(0, str(naturalidade) if naturalidade is not None else "")
        entry_naturalidade.pack(pady=2)

        ctk.CTkLabel(scroll_frame_edit, text="Órgão Emissor:").pack(pady=3)
        entry_orgao_emissor = ctk.CTkEntry(scroll_frame_edit, width=200)
        entry_orgao_emissor.insert(0, str(orgao_emissor) if orgao_emissor is not None else "")
        entry_orgao_emissor.pack(pady=2)
        
        ctk.CTkLabel(scroll_frame_edit, text="Email:").pack(pady=3)
        entry_email = ctk.CTkEntry(scroll_frame_edit, width=200)
        entry_email.insert(0, str(email) if email is not None else "")
        entry_email.pack(pady=2)
        
        ctk.CTkLabel(scroll_frame_edit, text="Endereço:").pack(pady=3)
        entry_endereco = ctk.CTkEntry(scroll_frame_edit, width=200)
        entry_endereco.insert(0, str(endereco) if endereco is not None else "")
        entry_endereco.pack(pady=2)
        
        ctk.CTkLabel(scroll_frame_edit, text="CEP:").pack(pady=3)
        entry_cep = ctk.CTkEntry(scroll_frame_edit, width=200)
        entry_cep.insert(0, str(cep) if cep is not None else "")
        entry_cep.pack(pady=2)
        
        ctk.CTkLabel(scroll_frame_edit, text="Telefone:").pack(pady=3)
        entry_telefone = ctk.CTkEntry(scroll_frame_edit, width=200)
        entry_telefone.insert(0, str(telefone) if telefone is not None else "")
        entry_telefone.pack(pady=2)
        
        ctk.CTkLabel(scroll_frame_edit, text="Código do Órgão:").pack(pady=3)
        entry_codigo_orgao = ctk.CTkEntry(scroll_frame_edit, width=200)
        entry_codigo_orgao.insert(0, str(codigo_orgao) if codigo_orgao is not None else "")
        entry_codigo_orgao.pack(pady=2)
        
        ctk.CTkLabel(scroll_frame_edit, text="Código da Folha:").pack(pady=3)
        entry_codigo_folha = ctk.CTkEntry(scroll_frame_edit, width=200)
        entry_codigo_folha.insert(0, str(codigo_folha) if codigo_folha is not None else "")
        entry_codigo_folha.pack(pady=2)
        
        ctk.CTkLabel(scroll_frame_edit, text="Número do Banco:").pack(pady=3)
        entry_numero_banco = ctk.CTkEntry(scroll_frame_edit, width=200)
        entry_numero_banco.insert(0, str(numero_banco) if numero_banco is not None else "")
        entry_numero_banco.pack(pady=2)
        
        def preencher_agencia_edit(event):
            banco = entry_numero_banco.get().strip()
            banco_nome = BANCOS.get(banco, "")
            if banco_nome:
                entry_descricao_banco.delete(0, tk.END)
                entry_descricao_banco.insert(0, banco_nome)
            else:
                entry_descricao_banco.delete(0, tk.END)
                
        ctk.CTkLabel(scroll_frame_edit, text="Descrição do banco:").pack(pady=3)
        entry_descricao_banco = ctk.CTkEntry(scroll_frame_edit, width=200)
        entry_descricao_banco.insert(0, str(descricao_do_banco) if descricao_do_banco is not None else "")
        entry_descricao_banco.pack(pady=2)
        
        ctk.CTkLabel(scroll_frame_edit, text="Agência:").pack(pady=3)
        entry_agencia = ctk.CTkEntry(scroll_frame_edit, width=200)
        entry_agencia.insert(0, str(agencia) if agencia is not None else "")
        entry_agencia.pack(pady=2)
        
        ctk.CTkLabel(scroll_frame_edit, text="UF:").pack(pady=3)
        entry_codigo_uf = ctk.CTkEntry(scroll_frame_edit, width=200)
        entry_codigo_uf.insert(0, str(codigo_uf) if codigo_uf is not None else "")
        entry_codigo_uf.pack(pady=2)
        
        ctk.CTkLabel(scroll_frame_edit, text="Tipo de Conta:").pack(pady=3)
        combo_tipo_conta = ctk.CTkComboBox(scroll_frame_edit, width=200, values=["Corrente", "Poupança", "Judicial"])
        combo_tipo_conta.pack(pady=2)
        if tipo_conta in ["Corrente", "Poupança", "Judicial"]:
            combo_tipo_conta.set(tipo_conta)
        else:
            combo_tipo_conta.set("Corrente")
        
        ctk.CTkLabel(scroll_frame_edit, text="Número da Conta:").pack(pady=3)
        entry_numero_conta = ctk.CTkEntry(scroll_frame_edit, width=200)
        entry_numero_conta.insert(0, str(numero_conta) if numero_conta is not None else "")
        entry_numero_conta.pack(pady=2)

        ctk.CTkLabel(scroll_frame_edit, text="Dígito da Conta:").pack(pady=3)
        entry_digito_conta = ctk.CTkEntry(scroll_frame_edit, width=200)
        entry_digito_conta.insert(0, str(digito_conta) if digito_conta is not None else "")
        entry_digito_conta.pack(pady=2)
        
        
        var_menor_incapaz = tk.IntVar()
        var_menor_incapaz.set(menor_ou_incapaz)
        def abrir_popup_representante():
            def salvar_representante():
                nome_rep = entry_nome_rep.get().strip()
                identidade = entry_identidade_rep.get().strip()
                cpf_rep = entry_cpf_rep.get().strip()
                orgao_emissor = entry_orgao_emissor.get().strip()
                endereco_rep = entry_endereco_rep.get().strip()
                telefone_rep = entry_telefone_rep.get().strip()
                agencia_rep = entry_agencia_rep.get().strip()
                numero_conta_rep = entry_numero_conta_rep.get().strip()
                tipo_conta_rep = combo_tipo_conta_rep.get().strip()
                email_rep = entry_email_rep.get().strip()
                digito_conta_rep = entry_digito_conta_rep.get().strip()
                numero_banco_rep = entry_numero_banco_rep.get().strip()
                descricao_dobanco = entry_descricao_banco_rep.get().strip()
                

                if not (nome_rep and cpf_rep):
                    messagebox.showerror("Erro", "Nome, CPF e Identidade do representante são obrigatórios!")
                    return

                conn = sqlite3.connect(resource_path('banco.db'))
                cursor = conn.cursor()
                try:
                    cursor.execute("""
                        INSERT INTO representantes_legais ( 
                            nome_completo, identidade, cpf, orgao_emissor, endereco, telefone, agencia, numero_conta, tipo_conta, numero_banco, cpf_beneficiario, descricao_banco, email, digitoconta
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        nome_rep, identidade, cpf_rep, orgao_emissor, endereco_rep, telefone_rep, 
                        agencia_rep, numero_conta_rep, tipo_conta_rep, numero_banco_rep, entry_cpf.get().strip(), descricao_dobanco, email_rep, digito_conta_rep
                    ))
                    conn.commit()
                    popup.destroy()
                except sqlite3.IntegrityError as e:
                    messagebox.showerror("Erro", f"CPF ou Identidade do representante já cadastrado!\n{e}")
                finally:
                    conn.close()
            
            
            popup = ctk.CTkToplevel()
            popup.title("Cadastrar Representante Legal")
            popup.geometry("400x500")
            popup.transient(janelaEditarBeneficiario)  # Torna o popup modal
            popup.wm_attributes("-topmost", True)
            ctk.set_default_color_theme("blue")

            # Frame com rolagem
            scroll_frame_popup = ctk.CTkScrollableFrame(popup, width=420, height=650)
            scroll_frame_popup.pack(fill="both", expand=True, padx=10, pady=10)
            
            ctk.CTkLabel(scroll_frame_popup, text="Nome Completo:").pack(pady=3)
            entry_nome_rep = ctk.CTkEntry(scroll_frame_popup, width=200)
            entry_nome_rep.pack(pady=2)
            
            ctk.CTkLabel(scroll_frame_popup, text="CPF:").pack(pady=3)
            entry_cpf_rep = ctk.CTkEntry(scroll_frame_popup, width=200)
            entry_cpf_rep.pack(pady=2)
            
            ctk.CTkLabel(scroll_frame_popup, text="Identidade:").pack(pady=3)
            entry_identidade_rep = ctk.CTkEntry(scroll_frame_popup, width=200)
            entry_identidade_rep.pack(pady=2)

            ctk.CTkLabel(scroll_frame_popup, text="Órgão Emissor:").pack(pady=3)
            entry_orgao_emissor = ctk.CTkEntry(scroll_frame_popup, width=200)
            entry_orgao_emissor.pack(pady=2)
            
            ctk.CTkLabel(scroll_frame_popup, text="Email:").pack(pady=3)
            entry_email_rep = ctk.CTkEntry(scroll_frame_popup, width=200)
            entry_email_rep.pack(pady=2)
            
            ctk.CTkLabel(scroll_frame_popup, text="Endereço:").pack(pady=3)
            entry_endereco_rep = ctk.CTkEntry(scroll_frame_popup, width=200)
            entry_endereco_rep.pack(pady=2)

            ctk.CTkLabel(scroll_frame_popup, text="Telefone:").pack(pady=3)
            entry_telefone_rep = ctk.CTkEntry(scroll_frame_popup, width=200)
            entry_telefone_rep.pack(pady=2)
            
            ctk.CTkLabel(scroll_frame_popup, text="Número do Banco:").pack(pady=3)
            entry_numero_banco_rep = ctk.CTkEntry(scroll_frame_popup, width=200)
            entry_numero_banco_rep.pack(pady=2)
            
            def preencher_agencia_rep_edit(event):
                banco_1 = entry_numero_banco_rep.get().strip()
                banco_nome = BANCOS.get(banco_1, "")
                if banco_nome:
                    entry_descricao_banco_rep.delete(0, tk.END)
                    entry_descricao_banco_rep.insert(0, banco_nome)
                else:
                    entry_descricao_banco_rep.delete(0, tk.END)
                    
            ctk.CTkLabel(scroll_frame_popup, text="Descrição do banco:").pack(pady=3)
            entry_descricao_banco_rep = ctk.CTkEntry(scroll_frame_popup, width=200)
            entry_descricao_banco_rep.pack(pady=2)
            
            ctk.CTkLabel(scroll_frame_popup, text="Agência:").pack(pady=3)
            entry_agencia_rep = ctk.CTkEntry(scroll_frame_popup, width=200)
            entry_agencia_rep.pack(pady=2)
            
            entry_numero_banco_rep.bind("<KeyRelease>", preencher_agencia_rep_edit)
            
            ctk.CTkLabel(scroll_frame_popup, text="Tipo de Conta:").pack(pady=3)
            combo_tipo_conta_rep = ctk.CTkComboBox(scroll_frame_popup, width=200, values=["Corrente", "Poupança", "Judicial"])
            combo_tipo_conta_rep.pack(pady=2)
            combo_tipo_conta_rep.set("Corrente")
            
            ctk.CTkLabel(scroll_frame_popup, text="Número da Conta:").pack(pady=3)
            entry_numero_conta_rep = ctk.CTkEntry(scroll_frame_popup, width=200)
            entry_numero_conta_rep.pack(pady=2)
            
            ctk.CTkLabel(scroll_frame_popup, text="Dígito da Conta:").pack(pady=3)
            entry_digito_conta_rep = ctk.CTkEntry(scroll_frame_popup, width=200)
            entry_digito_conta_rep.pack(pady=2)
            

            ctk.CTkButton(scroll_frame_popup, text="Salvar", command=salvar_representante, fg_color="#a1970c", hover_color="#d37b08", text_color="#fff", corner_radius=18).pack(pady=10)
            ctk.CTkButton(scroll_frame_popup, text="Cancelar", command=popup.destroy, fg_color="#a1970c", hover_color="#d37b08", text_color="#fff", corner_radius=18).pack(pady=5)

            #===============================================================================================#
            
            def aplicar_mascara_cpf(event):
                valor = entry_cpf_rep.get().replace(".", "").replace("-", "")[:11]
                novo = ""
                if len(valor) > 0:
                    novo += valor[:3]
                if len(valor) > 3:
                    novo += "." + valor[3:6]
                if len(valor) > 6:
                    novo += "." + valor[6:9]
                if len(valor) > 9:
                    novo += "-" + valor[9:11]
                entry_cpf_rep.delete(0, tk.END)
                entry_cpf_rep.insert(0, novo)
                
            def aplicar_mascara_telefone(event):
                valor = entry_telefone_rep.get().replace("(", "").replace(")", "").replace("-", "").replace(" ", "")[:11]
                novo = ""
                if len(valor) > 0:
                    novo += "(" + valor[:2] + ") "
                if len(valor) > 2 and len(valor) <= 7:
                    novo += valor[2:6] + "-" + valor[6:10]
                elif len(valor) > 7:
                    novo += valor[2:7] + "-" + valor[7:11]
                entry_telefone_rep.delete(0, tk.END)
                entry_telefone_rep.insert(0, novo)
                
            def aplicar_mascara_numero_banco(event):
                valor = entry_numero_banco_rep.get().replace("-", "")[:3]
                novo = ""
                if len(valor) > 0:
                    novo += valor[:3]
                entry_numero_banco_rep.delete(0, tk.END)
                entry_numero_banco_rep.insert(0, novo)
                
            entry_cpf_rep.bind("<KeyRelease>", aplicar_mascara_cpf)
            entry_telefone_rep.bind("<KeyRelease>", aplicar_mascara_telefone)
            entry_numero_banco_rep.bind("<KeyRelease>", aplicar_mascara_numero_banco)
                
            
            
        def on_menor_incapaz_change():
            if var_menor_incapaz.get():
                abrir_popup_representante()
                
        ctk.CTkCheckBox(scroll_frame_edit, text="É menor ou incapaz?", variable=var_menor_incapaz, command=on_menor_incapaz_change).pack(pady=5)
        
        
        def editar_representante():
            conn = sqlite3.connect(resource_path('banco.db'))
            cursor = conn.cursor()
            cursor.execute("""
                SELECT nome_completo, identidade, cpf, orgao_emissor, endereco, telefone, email,
                       agencia, numero_conta, tipo_conta, numero_banco, digitoconta
                FROM representantes_legais WHERE cpf_beneficiario = ?
            """, (cpf,))
            representante = cursor.fetchone()
            conn.close()

            if not representante:
                messagebox.showerror("Erro", "Nenhum representante legal encontrado!", parent=janelaEditarBeneficiario)
                return
            
            nome_rep, identidade, cpf_rep, orgao_emissor, endereco_rep, telefone_rep, email_rep, agencia_rep, numero_conta_rep, tipo_conta_rep, numero_banco_rep, digito_conta_rep = representante
            
            def salvar_representante():
                novo_nome_rep = entry_nome_rep.get().strip()
                nova_identidade = entry_identidade.get().strip()
                novo_cpf_rep = entry_cpf_rep.get().strip()
                novo_orgao_emissor = entry_orgao_emissor.get().strip()
                novo_endereco_rep = entry_endereco_rep.get().strip()
                novo_telefone_rep = entry_telefone_rep.get().strip()
                nova_agencia_rep = entry_agencia_rep.get().strip()
                novo_numero_conta_rep = entry_numero_conta_rep.get().strip()
                novo_tipo_conta_rep = combo_tipo_conta_rep.get().strip()
                novo_email_rep = entry_email_rep.get().strip()
                novo_digito_conta_rep = entry_digito_conta_rep.get().strip()
                novo_numero_banco_rep = entry_numero_banco_rep.get().strip()

                if not (novo_nome_rep and novo_cpf_rep and nova_identidade):
                    messagebox.showerror("Erro", "Nome, CPF e Identidade do representante são obrigatórios!")
                    return

                conn = sqlite3.connect(resource_path('banco.db'))
                cursor = conn.cursor()
                try:
                    cursor.execute("""
                        UPDATE representantes_legais SET
                            nome_completo = ?, identidade = ?, cpf = ?, orgao_emissor = ?, email = ?,
                            endereco = ?, telefone = ?, agencia = ?, numero_conta = ?,
                            tipo_conta = ?, numero_banco = ?, digitoconta = ?
                        WHERE cpf_beneficiario = ?
                    """, (
                        novo_nome_rep, nova_identidade, novo_cpf_rep, novo_orgao_emissor, novo_email_rep,
                        novo_endereco_rep, novo_telefone_rep, nova_agencia_rep, 
                        novo_numero_conta_rep, novo_tipo_conta_rep, novo_numero_banco_rep, novo_digito_conta_rep,
                        cpf
                    ))
                    conn.commit()
                    janelaEditarRepresentante.destroy()
                except sqlite3.IntegrityError as e:
                    messagebox.showerror("Erro", f"CPF ou Identidade do representante já cadastrado!\n{e}")
                finally:
                    conn.close()
                    
            janelaEditarRepresentante = ctk.CTkToplevel()
            janelaEditarRepresentante.title("Representante Legal")
            janelaEditarRepresentante.geometry("400x500")
            janelaEditarRepresentante.transient(janelaEditarBeneficiario)  # Torna o popup modal
            janelaEditarRepresentante.wm_attributes("-topmost", True)
            ctk.set_default_color_theme("blue")
            
            scroll_frame_edit_rep = ctk.CTkScrollableFrame(janelaEditarRepresentante, width=420, height=650)
            scroll_frame_edit_rep.pack(fill="both", expand=True, padx=10, pady=10)
            
            ctk.CTkLabel(scroll_frame_edit_rep, text="Número do Banco:").pack(pady=3)
            entry_numero_banco_rep = ctk.CTkEntry(scroll_frame_edit_rep, width=200)
            entry_numero_banco_rep.insert(0, str(numero_banco_rep) if numero_banco_rep is not None else "")
            entry_numero_banco_rep.pack(pady=2)
            
            def preencher_agencia_edit_rep(event):
                banco = entry_numero_banco_rep.get().strip()
                agencia_nome = BANCOS.get(banco, "")
                if agencia_nome:
                    entry_agencia_rep.delete(0, tk.END)
                    entry_agencia_rep.insert(0, agencia_nome)
                else:
                    entry_agencia_rep.delete(0, tk.END)
            
            ctk.CTkLabel(scroll_frame_edit_rep, text="Agência:").pack(pady=3)
            entry_agencia_rep = ctk.CTkEntry(scroll_frame_edit_rep, width=200)
            entry_agencia_rep.insert(0, str(agencia_rep) if agencia_rep is not None else "")
            entry_agencia_rep.pack(pady=2)
            
            
            ctk.CTkLabel(scroll_frame_edit_rep, text="Tipo de Conta:").pack(pady=3)
            combo_tipo_conta_rep = ctk.CTkComboBox(scroll_frame_edit_rep, width=200, values=["Corrente", "Poupança", "Judicial"])
            combo_tipo_conta_rep.pack(pady=2)
            if tipo_conta_rep in ["Corrente", "Poupança", "Judicial"]:
                combo_tipo_conta_rep.set(tipo_conta_rep)
            else:
                combo_tipo_conta_rep.set("Corrente")
                
            ctk.CTkLabel(scroll_frame_edit_rep, text="Número da Conta:").pack(pady=3)
            entry_numero_conta_rep = ctk.CTkEntry(scroll_frame_edit_rep, width=200)
            entry_numero_conta_rep.insert(0, str(numero_conta_rep) if numero_conta_rep is not None else "")
            entry_numero_conta_rep.pack(pady=2)
            
            ctk.CTkLabel(scroll_frame_edit_rep, text="Dígito da Conta:").pack(pady=3)
            entry_digito_conta_rep = ctk.CTkEntry(scroll_frame_edit_rep, width=200)
            entry_digito_conta_rep.insert(0, str(digito_conta_rep) if digito_conta_rep is not None else "")
            entry_digito_conta_rep.pack(pady=2)
            
            ctk.CTkLabel(scroll_frame_edit_rep, text="Nome Completo:").pack(pady=3)
            entry_nome_rep = ctk.CTkEntry(scroll_frame_edit_rep, width=200)
            entry_nome_rep.insert(0, str(nome_rep) if nome_rep is not None else "")
            entry_nome_rep.pack(pady=2)
            
            ctk.CTkLabel(scroll_frame_edit_rep, text="Identidade:").pack(pady=3)
            entry_identidade = ctk.CTkEntry(scroll_frame_edit_rep, width=200)
            entry_identidade.insert(0, str(identidade) if identidade is not None else "")
            entry_identidade.pack(pady=2)
            
            ctk.CTkLabel(scroll_frame_edit_rep, text="CPF:").pack(pady=3)
            entry_cpf_rep = ctk.CTkEntry(scroll_frame_edit_rep, width=200)
            entry_cpf_rep.insert(0, str(cpf_rep) if cpf_rep is not None else "")
            entry_cpf_rep.pack(pady=2)
            
            ctk.CTkLabel(scroll_frame_edit_rep, text="Identidade:").pack(pady=3)
            entry_identidade = ctk.CTkEntry(scroll_frame_edit_rep, width=200)
            entry_identidade.insert(0, str(identidade) if identidade is not None else "")
            entry_identidade.pack(pady=2)
            
            ctk.CTkLabel(scroll_frame_edit_rep, text="Órgão Emissor:").pack(pady=3)
            entry_orgao_emissor = ctk.CTkEntry(scroll_frame_edit_rep, width=200)
            entry_orgao_emissor.insert(0, str(orgao_emissor) if orgao_emissor is not None else "")
            entry_orgao_emissor.pack(pady=2)
            
            ctk.CTkLabel(scroll_frame_edit_rep, text="Email:").pack(pady=3)
            entry_email_rep = ctk.CTkEntry(scroll_frame_edit_rep, width=200)
            entry_email_rep.insert(0, str(email_rep) if email_rep is not None else "")
            entry_email_rep.pack(pady=2)
            
            ctk.CTkLabel(scroll_frame_edit_rep, text="Órgão Emissor:").pack(pady=3)
            entry_orgao_emissor = ctk.CTkEntry(scroll_frame_edit_rep, width=200)
            entry_orgao_emissor.insert(0, str(orgao_emissor) if orgao_emissor is not None else "")
            entry_orgao_emissor.pack(pady=2)
            
            ctk.CTkLabel(scroll_frame_edit_rep, text="Endereço:").pack(pady=3)
            entry_endereco_rep = ctk.CTkEntry(scroll_frame_edit_rep, width=200)
            entry_endereco_rep.insert(0, str(endereco_rep) if endereco_rep is not None else "")
            entry_endereco_rep.pack(pady=2)
            
            ctk.CTkLabel(scroll_frame_edit_rep, text="Telefone:").pack(pady=3)
            entry_telefone_rep = ctk.CTkEntry(scroll_frame_edit_rep, width=200)
            entry_telefone_rep.insert(0, str(telefone_rep) if telefone_rep is not None else "")
            entry_telefone_rep.pack(pady=2)
                
            ctk.CTkButton(scroll_frame_edit_rep, text="Salvar", command=salvar_representante, fg_color="#a1970c", hover_color="#d37b08", text_color="#fff", corner_radius=18).pack(pady=10)
            ctk.CTkButton(scroll_frame_edit_rep, text="Cancelar", command=janelaEditarRepresentante.destroy, fg_color="#a1970c", hover_color="#d37b08", text_color="#fff", corner_radius=18).pack(pady=5)
            
            entry_numero_banco_rep.bind("<KeyRelease>", preencher_agencia_edit_rep)
            
            
        ctk.CTkButton(scroll_frame_edit, text="Ver/Editar Representante Legal", command=editar_representante, fg_color="#a1970c", hover_color="#d37b08", text_color="#fff", corner_radius=18).pack(pady=5)
        
        
        ctk.CTkLabel(scroll_frame_edit, text="Nº Processo SEI:").pack(pady=3)
        entry_processo_sei = ctk.CTkEntry(scroll_frame_edit, width=200)
        entry_processo_sei.insert(0, str(numero_processo_sei) if numero_processo_sei is not None else "")
        entry_processo_sei.pack(pady=2)
        
        ctk.CTkLabel(scroll_frame_edit, text="Nº Processo Judicial:").pack(pady=3)
        entry_processo = ctk.CTkEntry(scroll_frame_edit, width=200)
        entry_processo.insert(0, str(processo_judicial) if processo_judicial is not None else "")
        entry_processo.pack(pady=2)

        ctk.CTkLabel(scroll_frame_edit, text="Origem da Decisão:").pack(pady=3)
        entry_origem_decisao = ctk.CTkEntry(scroll_frame_edit, width=200)
        entry_origem_decisao.insert(0, str(origem_decisao) if origem_decisao is not None else "")
        entry_origem_decisao.pack(pady=2)

        ctk.CTkLabel(scroll_frame_edit, text="Número da Vara:").pack(pady=3)
        entry_numero_vara = ctk.CTkEntry(scroll_frame_edit, width=200)
        entry_numero_vara.insert(0, str(numero_vara) if numero_vara is not None else "")
        entry_numero_vara.pack(pady=2)

        ctk.CTkLabel(scroll_frame_edit, text="Data Decisão (DD-MM-AAAA):").pack(pady=3)
        entry_data_decisao = ctk.CTkEntry(scroll_frame_edit, width=200)
        entry_data_decisao.insert(0, str(data_decisao) if data_decisao is not None else "")
        entry_data_decisao.pack(pady=2)
        
        ctk.CTkLabel(scroll_frame_edit, text="Data do Ofício PGDF (DD-MM-AAAA):").pack(pady=3)
        entry_data_oficio = ctk.CTkEntry(scroll_frame_edit, width=200)
        entry_data_oficio.insert(0, str(data_oficio) if data_oficio is not None else "")
        entry_data_oficio.pack(pady=2)


        # ctk.CTkLabel(scroll_frame_edit, text="Prazo de Pagamento:").pack(pady=3)
        # combo_prazo_tipo = ctk.CTkComboBox(scroll_frame_edit, width=200, values=["Parcelado", "Vitalício"])
        # combo_prazo_tipo.pack(pady=2)
        # if prazo_pagamento_tipo in ["Parcelado", "Vitalício"]:
        #     combo_prazo_tipo.set(prazo_pagamento_tipo)
        # else:
        #     combo_prazo_tipo.set("Parcelado")
        
        # ctk.CTkLabel(scroll_frame_edit, text="Nº de Parcelas (ou deixe em branco para vitalício):").pack(pady=3)
        # entry_prazo_valor = ctk.CTkEntry(scroll_frame_edit, width=200)
        # entry_prazo_valor.insert(0, str(prazo_pagamento_valor) if prazo_pagamento_valor is not None else "")  # Preenche com o valor atual
        # entry_prazo_valor.pack(pady=2)

        ctk.CTkLabel(scroll_frame_edit, text="Ementa da decisão:").pack(pady=3)
        entry_observacoes = tk.Text(scroll_frame_edit, width=38, height=4)
        # Ensure we always insert a single string argument. Some DB values may be None or
        # accidentally a tuple/list; coerce to string and clear the widget before inserting.
        try:
            texto_obs = "" if observacoes is None else str(observacoes)
        except Exception:
            texto_obs = ""
        entry_observacoes.delete("1.0", tk.END)
        entry_observacoes.insert("1.0", texto_obs)
        entry_observacoes.pack(pady=2)
        
        ctk.CTkButton(scroll_frame_edit, text="Salvar", command=salvar_edicoes, fg_color="#a1970c", hover_color="#d37b08", text_color="#fff", corner_radius=18).pack(padx=20, pady=5, expand=True)
        ctk.CTkButton(scroll_frame_edit, text="Cancelar", command=janelaEditarBeneficiario.destroy, fg_color="#6c757d", hover_color="#5a6268", text_color="#fff", corner_radius=18).pack(padx=20, pady=5, expand=True)
        

        def aplicar_mascara_cpf(event):
            valor = entry_cpf.get().replace(".", "").replace("-", "")[:11]
            novo = ""
            if len(valor) > 0:
                novo += valor[:3]
            if len(valor) > 3:
                novo += "." + valor[3:6]
            if len(valor) > 6:
                novo += "." + valor[6:9]
            if len(valor) > 9:
                novo += "-" + valor[9:11]
            entry_cpf.delete(0, tk.END)
            entry_cpf.insert(0, novo)

        def aplicar_mascara_cep(event):
            valor = entry_cep.get().replace("-", "")[:8]
            novo = ""
            if len(valor) > 0:
                novo += valor[:5]
            if len(valor) > 5:
                novo += "-" + valor[5:8]
            entry_cep.delete(0, tk.END)
            entry_cep.insert(0, novo)

        def aplicar_mascara_telefone(event):
            valor = entry_telefone.get().replace("(", "").replace(")", "").replace("-", "").replace(" ", "")[:11]
            novo = ""
            if len(valor) > 0:
                novo += "(" + valor[:2] + ") "
            if len(valor) > 2 and len(valor) <= 7:
                novo += valor[2:6] + "-" + valor[6:10]
            elif len(valor) > 7:
                novo += valor[2:7] + "-" + valor[7:11]
            entry_telefone.delete(0, tk.END)
            entry_telefone.insert(0, novo)

        def aplicar_mascara_data(event):
            valor = entry_data_decisao.get().replace("-", "")[:8]
            novo = ""
            if len(valor) > 0:
                novo += valor[:2]
            if len(valor) > 2:
                novo += "-" + valor[2:4]
            if len(valor) > 4:
                novo += "-" + valor[4:8]
            entry_data_decisao.delete(0, tk.END)
            entry_data_decisao.insert(0, novo)
            
        def aplicar_mascara_data_oficio(event):
            valor = entry_data_oficio.get().replace("-", "")[:8]
            novo = ""
            if len(valor) > 0:
                novo += valor[:2]
            if len(valor) > 2:
                novo += "-" + valor[2:4]
            if len(valor) > 4:
                novo += "-" + valor[4:8]
            entry_data_oficio.delete(0, tk.END)
            entry_data_oficio.insert(0, novo)
            
            
        def mascara_data_de_nascimento(event):
            valor = entry_data_nascimento.get().replace("-", "")[:8]
            novo = ""
            if len(valor) > 0:
                novo += valor[:2]
            if len(valor) > 2:
                novo += "-" + valor[2:4]
            if len(valor) > 4:
                novo += "-" + valor[4:8]
            entry_data_nascimento.delete(0, tk.END)
            entry_data_nascimento.insert(0, novo)    
        
        def aplicar_mascara_numero_banco(event):
            valor = entry_numero_banco.get().replace("-", "")[:3]
            novo = ""
            if len(valor) > 0:
                novo += valor[:3]
            entry_numero_banco.delete(0, tk.END)
            entry_numero_banco.insert(0, novo)


        # Após criar os campos:
        entry_cpf.bind("<KeyRelease>", aplicar_mascara_cpf)
        entry_cep.bind("<KeyRelease>", aplicar_mascara_cep)
        entry_telefone.bind("<KeyRelease>", aplicar_mascara_telefone)
        entry_data_decisao.bind("<KeyRelease>", aplicar_mascara_data)
        entry_data_oficio.bind("<KeyRelease>", aplicar_mascara_data_oficio)
        entry_numero_banco.bind("<KeyRelease>", aplicar_mascara_numero_banco)
        entry_numero_banco.bind("<KeyRelease>", preencher_agencia_edit)
        entry_data_nascimento.bind("<KeyRelease>", mascara_data_de_nascimento)
#==============================================================================================#

def listar_representantes_legais():
    conn = sqlite3.connect(resource_path('banco.db'))
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            r.id, r.nome_completo, r.identidade, r.cpf, r.email, r.orgao_emissor, r.endereco, r.telefone,
            r.agencia, r.numero_conta, r.digitoconta, r.tipo_conta, r.numero_banco, r.descricao_banco, b.nome_completo
        FROM representantes_legais r
        LEFT JOIN beneficiarios b ON r.cpf_beneficiario = b.cpf
        ORDER BY r.nome_completo
    """)
    representantes = cursor.fetchall()
    conn.close()

    if not representantes:
        messagebox.showinfo("Info", "Nenhum representante legal cadastrado.")
        return

    janelaListar = ctk.CTkToplevel()
    janelaListar.title("Lista de Representantes Legais")
    janelaListar.geometry("1100x500")
    janelaListar.wm_attributes("-topmost", True)
    ctk.set_default_color_theme("blue")

    frame_principal = ctk.CTkFrame(janelaListar)
    frame_principal.pack(fill="both", expand=True, padx=5, pady=5)

    style = ttk.Style()
    style.theme_use("default")
    style.configure("Treeview", background="#ffffff", foreground="black", rowheight=25, fieldbackground="#ffffff")
    style.map('Treeview', background=[('selected', '#a1970c')])
    style.configure("Treeview.Heading", font=('Calibri', 10, 'bold'))

    colunas = (
        "ID", "Nome do Representante", "Identidade", "CPF", "Email", "Órgão Emissor", "Endereço", "Telefone",
        "Agência", "Conta", "Dígito", "Tipo Conta", "Nº Banco", "Descrição do Banco", "Beneficiário Vinculado"
    )
    tree = ttk.Treeview(frame_principal, columns=colunas, show='headings')

    for col in colunas:
        tree.heading(col, text=col, command=lambda c=col: sort_by_column(tree, c, False))
        tree.column(col, width=120, anchor='center')

    scrollbar_vertical = ttk.Scrollbar(frame_principal, orient="vertical", command=tree.yview)
    scrollbar_horizontal = ttk.Scrollbar(frame_principal, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=scrollbar_vertical.set, xscrollcommand=scrollbar_horizontal.set)
    tree.grid(row=0, column=0, sticky='nsew')
    scrollbar_vertical.grid(row=0, column=1, sticky='ns')
    scrollbar_horizontal.grid(row=1, column=0, sticky='ew')
    frame_principal.grid_rowconfigure(0, weight=1)
    frame_principal.grid_columnconfigure(0, weight=1)

    tree.tag_configure('oddrow', background='#F0F0F0')
    tree.tag_configure('evenrow', background='white')

    for i, representante in enumerate(representantes):
        representante_tratado = ["" if valor is None else valor for valor in representante]
        tree.insert("", tk.END, values=representante_tratado, tags=('evenrow' if i % 2 == 0 else 'oddrow',))

    def carregar_dados():
        for item in tree.get_children():
            tree.delete(item)
        
        conn = sqlite3.connect(resource_path('banco.db'))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                r.id, r.nome_completo, r.identidade, r.cpf, r.email, r.orgao_emissor, r.endereco, r.telefone,
                r.agencia, r.numero_conta, r.digitoconta, r.tipo_conta, r.numero_banco, r.descricao_banco, b.nome_completo
            FROM representantes_legais r
            LEFT JOIN beneficiarios b ON r.cpf_beneficiario = b.cpf
            ORDER BY r.nome_completo
        """)
        representantes = cursor.fetchall()
        conn.close()
        
        for i, representante in enumerate(representantes):
            representante_tratado = tuple("" if valor is None else valor for valor in representante)
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            tree.insert("", "end", values=representante_tratado, tags=(tag,))

    def editar_representante_legal(id_representante):
        conn = sqlite3.connect(resource_path('banco.db'))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT nome_completo, identidade, cpf, orgao_emissor, endereco, telefone, email,
                   agencia, numero_conta, tipo_conta, numero_banco, descricao_banco, cpf_beneficiario, digitoconta
            FROM representantes_legais WHERE id = ?
        """, (id_representante,))
        dados = cursor.fetchone()
        conn.close()

        if not dados:
            messagebox.showerror("Erro", "Representante não encontrado!", parent=janelaListar)
            return

        nome, identidade, cpf, orgao_emissor, endereco, telefone, email, agencia, numero_conta, tipo_conta, numero_banco, descricao_banco, cpf_beneficiario, digito_conta = dados

        def salvar_edicoes():
            novo_nome = entry_nome.get().strip()
            nova_identidade = entry_identidade.get().strip()
            novo_cpf = entry_cpf.get().strip()
            novo_orgao_emissor = entry_orgao_emissor.get().strip()
            novo_endereco = entry_endereco.get().strip()
            novo_telefone = entry_telefone.get().strip()
            nova_agencia = entry_agencia.get().strip()
            novo_numero_conta = entry_numero_conta.get().strip()
            novo_tipo_conta = combo_tipo_conta.get().strip()
            novo_numero_banco = entry_numero_banco.get().strip()
            novo_email = entry_email.get().strip()
            novo_digito_conta = entry_digito_conta.get().strip()
            novo_banco = entry_descricao_banco.get().strip()
            novo_cpf_beneficiario = entry_cpf_beneficiario.get().strip()

            if not (novo_nome and novo_cpf and nova_identidade):
                messagebox.showerror("Erro", "Nome, CPF e Identidade são obrigatórios!", parent=janelaEditar)
                return

            conn = sqlite3.connect(resource_path('banco.db'))
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    UPDATE representantes_legais SET
                        nome_completo = ?, identidade = ?, cpf = ?, orgao_emissor = ?, endereco = ?, telefone = ?, email = ?,
                        agencia = ?, numero_conta = ?, tipo_conta = ?, numero_banco = ?, cpf_beneficiario = ?, descricao_banco = ?, digitoconta = ?
                    WHERE id = ?
                """, (
                    novo_nome, nova_identidade, novo_cpf, novo_orgao_emissor, novo_endereco, novo_telefone, novo_email,
                    nova_agencia, novo_numero_conta, novo_tipo_conta, novo_numero_banco, novo_cpf_beneficiario,
                    novo_banco, novo_digito_conta, id_representante
                ))
                conn.commit()
                janelaEditar.destroy()
                carregar_dados()
            except sqlite3.IntegrityError as e:
                messagebox.showerror("Erro", f"Erro de integridade de dados (ex: CPF duplicado).\n{e}", parent=janelaEditar)
            finally:
                conn.close()

        janelaEditar = ctk.CTkToplevel()
        janelaEditar.title("Editar Representante Legal")
        janelaEditar.geometry("400x600")
        janelaEditar.wm_attributes("-topmost", True)

        scroll_frame_edit = ctk.CTkScrollableFrame(janelaEditar, width=420, height=650)
        scroll_frame_edit.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(scroll_frame_edit, text="Nome Completo:").pack(pady=3)
        entry_nome = ctk.CTkEntry(scroll_frame_edit, width=200)
        entry_nome.insert(0, str(nome) if nome is not None else "")
        entry_nome.pack(pady=2)
        
        ctk.CTkLabel(scroll_frame_edit, text="CPF:").pack(pady=3)
        entry_cpf = ctk.CTkEntry(scroll_frame_edit, width=200)
        entry_cpf.insert(0, str(cpf) if cpf is not None else "")
        entry_cpf.pack(pady=2)
        
        ctk.CTkLabel(scroll_frame_edit, text="Identidade:").pack(pady=3)
        entry_identidade = ctk.CTkEntry(scroll_frame_edit, width=200)
        entry_identidade.insert(0, str(identidade) if identidade is not None else "")
        entry_identidade.pack(pady=2)

        ctk.CTkLabel(scroll_frame_edit, text="Órgão Emissor:").pack(pady=3)
        entry_orgao_emissor = ctk.CTkEntry(scroll_frame_edit, width=200)
        entry_orgao_emissor.insert(0, str(orgao_emissor) if orgao_emissor is not None else "")
        entry_orgao_emissor.pack(pady=2)
        
        ctk.CTkLabel(scroll_frame_edit, text="Email:").pack(pady=3)
        entry_email = ctk.CTkEntry(scroll_frame_edit, width=200)
        entry_email.insert(0, str(email) if email is not None else "")
        entry_email.pack(pady=2)
        
        ctk.CTkLabel(scroll_frame_edit, text="Endereço:").pack(pady=3)
        entry_endereco = ctk.CTkEntry(scroll_frame_edit, width=200)
        entry_endereco.insert(0, str(endereco) if endereco is not None else "")
        entry_endereco.pack(pady=2)
        
        ctk.CTkLabel(scroll_frame_edit, text="Telefone:").pack(pady=3)
        entry_telefone = ctk.CTkEntry(scroll_frame_edit, width=200)
        entry_telefone.insert(0, str(telefone) if telefone is not None else "")
        entry_telefone.pack(pady=2)
        
        
        ctk.CTkLabel(scroll_frame_edit, text="Número do Banco:").pack(pady=3)
        entry_numero_banco = ctk.CTkEntry(scroll_frame_edit, width=200)
        entry_numero_banco.insert(0, str(numero_banco) if numero_banco is not None else "")
        entry_numero_banco.pack(pady=2)
        
        
        def preencher_agencia_editResponsavel(event):
            banco = entry_numero_banco.get().strip()
            banco_nome = BANCOS.get(banco, "")
            if banco_nome:
                entry_descricao_banco.delete(0, tk.END)
                entry_descricao_banco.insert(0, banco_nome)
            else:
                entry_descricao_banco.delete(0, tk.END)
                
        ctk.CTkLabel(scroll_frame_edit, text="Descrição do banco:").pack(pady=3)
        entry_descricao_banco = ctk.CTkEntry(scroll_frame_edit, width=200)
        entry_descricao_banco.pack(pady=2)
        
        ctk.CTkLabel(scroll_frame_edit, text="Agência:").pack(pady=3)
        entry_agencia = ctk.CTkEntry(scroll_frame_edit, width=200)
        entry_agencia.insert(0, str(agencia) if agencia is not None else "")
        entry_agencia.pack(pady=2)
        
        entry_numero_banco.bind("<KeyRelease>", preencher_agencia_editResponsavel)
        
        ctk.CTkLabel(scroll_frame_edit, text="Tipo de Conta:").pack(pady=3)
        combo_tipo_conta = ctk.CTkComboBox(scroll_frame_edit, width=200, values=["Corrente", "Poupança", "Judicial"])
        combo_tipo_conta.set(tipo_conta if tipo_conta in ["Corrente", "Poupança", "Judicial"] else "Corrente")
        combo_tipo_conta.pack(pady=2)
        
        ctk.CTkLabel(scroll_frame_edit, text="Número da Conta:").pack(pady=3)
        entry_numero_conta = ctk.CTkEntry(scroll_frame_edit, width=200)
        entry_numero_conta.insert(0, str(numero_conta) if numero_conta is not None else "")
        entry_numero_conta.pack(pady=2)

        ctk.CTkLabel(scroll_frame_edit, text="Dígito da Conta:").pack(pady=3)
        entry_digito_conta = ctk.CTkEntry(scroll_frame_edit, width=200)
        entry_digito_conta.insert(0, str(digito_conta) if digito_conta is not None else "")
        entry_digito_conta.pack(pady=2)

        ctk.CTkLabel(scroll_frame_edit, text="CPF do Beneficiário Vinculado:").pack(pady=3)
        entry_cpf_beneficiario = ctk.CTkEntry(scroll_frame_edit, width=200)
        entry_cpf_beneficiario.insert(0, str(cpf_beneficiario) if cpf_beneficiario is not None else "")
        entry_cpf_beneficiario.pack(pady=2)

        ctk.CTkButton(scroll_frame_edit, text="Salvar", command=salvar_edicoes, fg_color="#a1970c", hover_color="#d37b08", text_color="#fff", corner_radius=18).pack(pady=10)
        ctk.CTkButton(scroll_frame_edit, text="Cancelar", command=janelaEditar.destroy, fg_color="#a1970c", hover_color="#d37b08", text_color="#fff", corner_radius=18).pack(pady=5)


    filtrar = ctk.CTkLabel(frame_principal, text="Filtrar:")
    filtrar.grid(row=2, column=0, sticky='w', padx=2, pady=5)
    entry_filtro = ctk.CTkEntry(frame_principal, width=200)
    entry_filtro.grid(row=2, column=0, sticky='w', padx=50, pady=5)

    def filtrar_representantes(event=None):
        filtro = entry_filtro.get().strip().lower()
        for item in tree.get_children():
            tree.delete(item)
        for i, representante in enumerate(representantes):
            representante_tratado = ["" if valor is None else valor for valor in representante]
            if any(filtro in str(valor).lower() for valor in representante_tratado):
                tree.insert("", tk.END, values=representante_tratado, tags=('evenrow' if i % 2 == 0 else 'oddrow',))

    entry_filtro.bind("<KeyRelease>", filtrar_representantes)
        
    def sort_by_column(tree, col, descending):
        data = [(tree.set(child, col), child) for child in tree.get_children('')]
        try:
            data.sort(key=lambda t: float(t[0]) if t[0].replace('.', '', 1).isdigit() else t[0], reverse=descending)
        except ValueError:
            data.sort(key=lambda t: t[0], reverse=descending)
        for index, (val, child) in enumerate(data):
            tree.move(child, '', index)
        tree.heading(col, command=lambda: sort_by_column(tree, col, not descending))

    def on_double_click(event):
        item = tree.selection()
        if item:
            id_representante = tree.item(item, "values")[0]
            editar_representante_legal(id_representante)

    btn_atualizar = ctk.CTkButton(frame_principal, text="Atualizar", command=carregar_dados, fg_color="#a1970c", hover_color="#d37b08", text_color="#fff", corner_radius=18)
    btn_atualizar.grid(row=2, column=0, pady=10, sticky='e')
    tree.bind("<Double-1>", on_double_click)
    
#==============================================================================================#

def novo_indice():
    tipos_de_indice = ["Salário Mínimo", "Índice Judicial A", "Índice Judicial B", "Índice Judicial C"]

    def salvar_novo_indice():
        tipo_indice = combo_tipo_indice.get()
        valor = entry_valor_indice.get().strip().replace(",", ".")
        data_vigencia_str = entry_data_vigencia.get().strip()

        if not all([tipo_indice, valor, data_vigencia_str]):
            messagebox.showerror("Erro", "Todos os campos são obrigatórios!", parent=janela_novo_indice)
            return
        
        try:
            valor_float = float(valor)
        except ValueError:
            messagebox.showerror("Erro", "Valor do índice inválido!", parent=janela_novo_indice)
            return

        try:
            # Valida e formata a data para o padrão do banco (AAAA-MM-DD)
            data_vigencia_dt = datetime.strptime(data_vigencia_str, "%m/%Y")
            data_vigencia_db = data_vigencia_dt.strftime("%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Erro", "Formato da data de vigência inválido. Use MM/AAAA.", parent=janela_novo_indice)
            return

        try:
            # O bloco 'with' gerencia a conexão, commit/rollback e fechamento automaticamente.
            # O 'timeout' ajuda a evitar erros de "database is locked".
            with sqlite3.connect(resource_path('banco.db'), timeout=10) as conn:
                cursor = conn.cursor()
                data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute(
                    "INSERT INTO indice (tipo_indice, valor, data_vigencia, data_atualizacao, usuario_id) VALUES (?, ?, ?, ?, ?)",
                    (tipo_indice, valor_float, data_vigencia_db, data_atual, id_usuario_logado)
                )
            messagebox.showinfo("Sucesso", "Índice cadastrado com sucesso!", parent=janela_novo_indice)
            janela_novo_indice.destroy()
        except sqlite3.Error as e:
            messagebox.showerror("Erro", f"Erro ao salvar no banco de dados:\n{e}", parent=janela_novo_indice)

    janela_novo_indice = ctk.CTkToplevel()
    janela_novo_indice.title("Cadastrar Novo Valor de Índice")
    janela_novo_indice.geometry("400x450")
    janela_novo_indice.wm_attributes("-topmost", True)
    janela_novo_indice.resizable(False, False)

    frame_principal = ctk.CTkFrame(janela_novo_indice, fg_color="transparent")
    frame_principal.pack(expand=True, padx=20, pady=20)

    ctk.CTkLabel(frame_principal, text="Cadastrar Índice", font=('Calibri', 16, 'bold')).pack(pady=(0, 10))
    ctk.CTkLabel(frame_principal, text="Adicione um novo valor para um dos índices do sistema.", justify="center").pack(pady=(0, 20))

    ctk.CTkLabel(frame_principal, text="Tipo de Índice:").pack(pady=5)
    combo_tipo_indice = ctk.CTkComboBox(frame_principal, width=200, values=tipos_de_indice, state="readonly")
    combo_tipo_indice.pack(pady=2)
    combo_tipo_indice.set(tipos_de_indice[0]) # Padrão

    ctk.CTkLabel(frame_principal, text="Valor (R$):").pack(pady=5)
    entry_valor_indice = ctk.CTkEntry(frame_principal, width=150, justify="center")
    entry_valor_indice.pack(pady=2)

    ctk.CTkLabel(frame_principal, text="Vigência (MM/AAAA):").pack(pady=5)
    entry_data_vigencia = ctk.CTkEntry(frame_principal, width=150, justify="center")
    entry_data_vigencia.pack(pady=2)

    entry_data_vigencia.bind("<KeyRelease>", mascara_data_referencia)

    ctk.CTkButton(frame_principal, text="Salvar", command=salvar_novo_indice, fg_color="#a1970c", hover_color="#d37b08", text_color="#fff", corner_radius=18).pack(pady=20)
    ctk.CTkButton(frame_principal, text="Cancelar", command=janela_novo_indice.destroy, fg_color="#6c757d", hover_color="#5a6268", text_color="#fff", corner_radius=18).pack()

def alterar_status_indice(indice_id, status_atual, callback_atualizar):
    """Altera o status de um índice para ATIVO ou INATIVO com avisos de segurança."""
    novo_status = "INATIVO" if status_atual == "ATIVO" else "ATIVO"
    
    if novo_status == "INATIVO":
        titulo = "ALERTA DE RISCO"
        mensagem = (
            "Você está prestes a INATIVAR um índice.\n\n"
            "Índices inativos NÃO são usados para cálculos. Se este for o único índice válido "
            "para um período, os pagamentos daquele período não poderão mais ser calculados corretamente.\n\n"
            "Tem certeza absoluta que deseja continuar?"
        )
        icon = 'warning'
    else: # Ativando
        titulo = "Confirmar Ativação"
        mensagem = (
            "Você está prestes a ATIVAR um índice.\n\n"
            "Este índice voltará a ser considerado para os cálculos de pagamento.\n\n"
            "Tem certeza que deseja continuar?"
        )
        icon = 'question'

    resposta = messagebox.askyesno(titulo, mensagem, icon=icon)
    if not resposta:
        return

    with sqlite3.connect(resource_path('banco.db')) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE indice SET status = ? WHERE id = ?", (novo_status, indice_id))
    
    callback_atualizar()
    

#==============================================================================================#    
    
def listar_folhas_pagamento():
    janela_folhas = ctk.CTkToplevel()
    janela_folhas.title("Folhas de Pagamento")
    janela_folhas.geometry("950x600")
    janela_folhas.grab_set()
    
    frame = ctk.CTkFrame(janela_folhas, fg_color="transparent")
    frame.pack(expand=True, fill="both", padx=20, pady=20)
    
    colunas = ('id', 'referencia', 'status', 'data alterçao', 'usuario')
    tree = ttk.Treeview(frame, columns=colunas, show='headings', height=20)
    
    def sort_by_column(col, descending):
        data = []
        for child in tree.get_children(''):
            data.append((tree.set(child, col), child))
        
        def sort_key(item):
            value = item[0]
            if col == 'referencia':
                try:
                    return datetime.strptime(value, '%m/%Y')
                except ValueError:
                    return datetime.min
            elif col == 'data alterçao':
                try:
                    return datetime.strptime(value, '%d/%m/%Y %H:%M')
                except ValueError:
                    return datetime.min
            elif col == 'id':
                try:
                    return int(value)
                except (ValueError, TypeError):
                    return float('-inf')
            return value
        
        data.sort(key=sort_key, reverse=descending)
        
        for index, (val, child) in enumerate(data):
            tree.move(child, '', index)
        
        tree.heading(col, command=lambda: sort_by_column(col, not descending))
        
    tree.column('id', width=50, anchor='center')
    tree.column('referencia', width=150, anchor='center')
    tree.column('status', width=100, anchor='center')
    tree.column('data alterçao', width=180, anchor='center')
    tree.column('usuario', width=150)
    
    tree.heading('id', text='ID', command=lambda: sort_by_column('id', False))
    tree.heading('referencia', text='Referência', command=lambda: sort_by_column('referencia', False))
    tree.heading('status', text='Status', command=lambda: sort_by_column('status', False))
    tree.heading('data alterçao', text='Data da Alteração', command=lambda: sort_by_column('data alterçao', False))
    tree.heading('usuario', text='Usuário', command=lambda: sort_by_column('usuario', False))
    
    scrollbar = ctk.CTkScrollbar(frame, command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    tree.pack(side="left", expand=True, fill="both")
    
    def carregar_dados_folhas():
        for item in tree.get_children():
            tree.delete(item)
        
        try:
            with sqlite3.connect(resource_path('banco.db')) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT f.id, f.mes_referencia, f.status, f.data_alteracao, f.alterado_por
                    FROM folhas AS f
                    ORDER BY f.mes_referencia DESC, f.id DESC
                """)
                for folha in cursor.fetchall():
                    # Normaliza a referência aceitando tanto 'YYYY-MM' quanto 'MM/YYYY'
                    raw_ref = folha[1] or ''
                    referencia_formatada = raw_ref
                    try:
                        # tentar formato banco atual 'YYYY-MM'
                        referencia_formatada = datetime.strptime(raw_ref, '%Y-%m').strftime('%m/%Y')
                    except Exception:
                        try:
                            # tentar formato antigo 'MM/YYYY'
                            referencia_formatada = datetime.strptime(raw_ref, '%m/%Y').strftime('%m/%Y')
                        except Exception:
                            # se falhar, mantém o raw
                            referencia_formatada = raw_ref

                    # Normaliza data de alteração com tolerância a múltiplos formatos
                    raw_data_alt = folha[3]
                    data_alteracao_formatada = 'N/A'
                    if raw_data_alt:
                        for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%d/%m/%Y %H:%M', '%Y-%m-%d'):
                            try:
                                data_alteracao_formatada = datetime.strptime(raw_data_alt, fmt).strftime('%d/%m/%Y %H:%M')
                                break
                            except Exception:
                                continue
                    usuario = folha[4] if folha[4] else "N/A (Antigo)"
                    tree.insert('', 'end', values=(folha[0], referencia_formatada, folha[2], data_alteracao_formatada, usuario))
        except sqlite3.Error as e:
            messagebox.showerror("Erro", f"Erro ao carregar dados do banco:\n{e}", parent=janela_folhas)
    
    carregar_dados_folhas()
    
    ctk.CTkButton(janela_folhas, text="Fechar", command=janela_folhas.destroy, fg_color="#6c757d", hover_color="#5a6268").pack(pady=(10, 10))

#==============================================================================================#

def listar_auditoria_indices():
    """
    Cria uma janela para exibir o histórico completo de alterações nos índices,
    incluindo o usuário responsável.
    """
    janela_auditoria = ctk.CTkToplevel()
    janela_auditoria.title("Auditoria de Índices Cadastrados")
    janela_auditoria.geometry("950x600")
    janela_auditoria.grab_set()

    frame = ctk.CTkFrame(janela_auditoria, fg_color="transparent")
    frame.pack(expand=True, fill="both", padx=20, pady=20)

    # Treeview para exibir os dados
    colunas = ('id', 'tipo', 'valor', 'vigencia', 'insercao', 'usuario', 'status')
    tree = ttk.Treeview(frame, columns=colunas, show='headings', height=20)

    # Cabeçalhos
    def sort_by_column(col, descending):
        """Função para ordenar a treeview pela coluna clicada."""
        data = []
        for child in tree.get_children(''):
            # Armazena o valor original e o item para manter a referência
            data.append((tree.set(child, col), child))

        # Chave de ordenação personalizada
        def sort_key(item):
            value = item[0]
            if col in ['vigencia', 'insercao']:
                try:
                    # Tenta converter para data/datetime para ordenação correta
                    return datetime.strptime(value, '%m/%Y' if col == 'vigencia' else '%d/%m/%Y %H:%M')
                except ValueError:
                    return datetime.min # Coloca valores inválidos no início
            elif col == 'valor':
                try:
                    # Remove "R$", espaços e converte vírgula para ponto
                    return float(value.replace("R$", "").strip().replace(".", "").replace(",", "."))
                except (ValueError, AttributeError):
                    return float('-inf') # Coloca valores inválidos no início
            elif col == 'id':
                try:
                    return int(value)
                except (ValueError, TypeError):
                    return float('-inf')
            return value # Ordenação de string padrão para outras colunas

        data.sort(key=sort_key, reverse=descending)

        for index, (val, child) in enumerate(data):
            tree.move(child, '', index)

        # Inverte a direção da ordenação para o próximo clique
        tree.heading(col, command=lambda: sort_by_column(col, not descending))

    # Colunas
    tree.column('id', width=50, anchor='center')
    tree.column('tipo', width=150)
    tree.column('valor', width=120, anchor='e') # 'e' for east (right align)
    tree.column('vigencia', width=120, anchor='center')
    tree.column('insercao', width=140, anchor='center')
    tree.column('usuario', width=150)
    tree.column('status', width=80, anchor='center')

    # Associa a função de ordenação a cada cabeçalho
    tree.heading('id', text='ID', command=lambda: sort_by_column('id', False))
    tree.heading('tipo', text='Tipo de Índice', command=lambda: sort_by_column('tipo', False))
    tree.heading('valor', text='Valor (R$)', command=lambda: sort_by_column('valor', False))
    tree.heading('vigencia', text='Vigência', command=lambda: sort_by_column('vigencia', False))
    tree.heading('insercao', text='Inserção', command=lambda: sort_by_column('insercao', False))
    tree.heading('usuario', text='Usuário', command=lambda: sort_by_column('usuario', False))
    tree.heading('status', text='Status', command=lambda: sort_by_column('status', False))

    # Scrollbar
    scrollbar = ctk.CTkScrollbar(frame, command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    tree.pack(side="left", expand=True, fill="both")

    def carregar_dados_auditoria():
        # Limpa a treeview antes de carregar
        for item in tree.get_children():
            tree.delete(item)
            
        try:
            with sqlite3.connect(resource_path('banco.db')) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                SELECT i.id, i.tipo_indice, i.valor, i.data_vigencia, i.data_atualizacao, u.nome_usuario, i.status
                FROM indice AS i
                LEFT JOIN users AS u ON i.usuario_id = u.id_usuario
                ORDER BY i.data_vigencia DESC, i.id DESC
            """)
                for indice in cursor.fetchall():
                    valor_formatado = f"R$ {indice[2]:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    data_vigencia_formatada = datetime.strptime(indice[3], '%Y-%m-%d').strftime('%m/%Y')
                    data_insercao_formatada = datetime.strptime(indice[4], '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y %H:%M')
                    usuario = indice[5] if indice[5] else "N/A (Antigo)"
                    status = indice[6] if indice[6] else "ATIVO"
                    
                    tree.insert('', 'end', values=(
                        indice[0], indice[1], valor_formatado, 
                        data_vigencia_formatada, data_insercao_formatada, usuario, status
                    ))
        except sqlite3.Error as e:
            messagebox.showerror("Erro de Banco de Dados", f"Não foi possível carregar os dados de auditoria.\n\nErro: {e}", parent=janela_auditoria)

    def on_double_click(event):
        item_selecionado = tree.selection()
        if not item_selecionado:
            return
        
        valores = tree.item(item_selecionado[0], "values")
        indice_id = valores[0]
        status_atual = valores[6]
        alterar_status_indice(indice_id, status_atual, carregar_dados_auditoria)

    tree.bind("<Double-1>", on_double_click)
    carregar_dados_auditoria()

    ctk.CTkButton(janela_auditoria, text="Fechar", command=janela_auditoria.destroy, fg_color="#6c757d", hover_color="#5a6268").pack(pady=(10, 10))

#==============================================================================================#

def cadastro_pagamentos():
    global combo_beneficiarios_ativos
    atualizar_combos()
    tipos_de_indice = ["Salário Mínimo", "Índice Judicial A", "Índice Judicial B", "Índice Judicial C"]
    def salvar_pagamento():
        # 1. Obter todos os valores dos widgets da interface
        valor = valor_var.get().strip()
        data_inicial = entry_data_inicial.get().strip()
        data_final = entry_data_final.get().strip()
        percentual_concedido = percentual_var.get().strip()
        salario_13 = var_salario_13.get()
        indice_vinculado = combo_indice_vinculado.get() if percentual_concedido else None
        um_terco_ferias = var_um_terco_ferias.get()
        observacoes = entry_observacoes.get("1.0", tk.END).strip()
        nome_selecionado = combo_beneficiarios.get()
        cpf_beneficiario = entry_cpf.get().strip()

        # 2. Validações essenciais antes de acessar o banco
        if not nome_selecionado:
            messagebox.showerror("Erro de Validação", "É necessário selecionar um beneficiário.", parent=janelaPagamentos)
            return
        if not data_inicial:
            messagebox.showerror("Erro de Validação", "O campo 'Data Inicial' é obrigatório.", parent=janelaPagamentos)
            return
        if not valor and not percentual_concedido:
            messagebox.showerror("Erro de Validação", "É necessário informar um 'Valor' ou um 'Percentual'.", parent=janelaPagamentos)
            return
        if percentual_concedido and not indice_vinculado:
            messagebox.showerror("Erro de Validação", "Se um percentual for informado, é necessário vincular a um índice.", parent=janelaPagamentos)
            return

        # Validação de datas
        if data_final:
            try:
                data_inicial_dt = datetime.strptime(data_inicial, "%m/%Y")
                data_final_dt = datetime.strptime(data_final, "%m/%Y")
                if data_final_dt < data_inicial_dt:
                    messagebox.showerror("Erro de Validação", "A data final não pode ser anterior à data inicial.", parent=janelaPagamentos)
                    return
            except ValueError:
                messagebox.showerror("Erro de Formato", "As datas devem estar no formato MM/AAAA.", parent=janelaPagamentos)
                return

        # 3. Operações de banco de dados de forma segura
        try:
            with sqlite3.connect(resource_path('banco.db')) as conn:
                cursor = conn.cursor()

                cursor.execute("SELECT id FROM beneficiarios WHERE nome_completo = ?", (nome_selecionado,))
                result = cursor.fetchone()
                if not result:
                    messagebox.showerror("Erro", "Beneficiário não encontrado no banco de dados.", parent=janelaPagamentos)
                    return
                
                beneficiario_id = result[0]
                data_pagamento = datetime.now().strftime("%d-%m-%Y")

                # Ação 1: Inativa qualquer parâmetro ATIVO existente para este beneficiário
                cursor.execute("""
                    UPDATE pagamentos 
                    SET status = 'INATIVO' 
                    WHERE beneficiario_id = ? AND status = 'ATIVO'
                """, (beneficiario_id,))

                # Ação 2: Insere o novo parâmetro como ATIVO
                data_atualizacao = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("""
                    INSERT INTO pagamentos (
                        valor, data_inicial, data_final, percentual_concedido, salario_13, um_terco_ferias, 
                        observacoes, beneficiario_id, cpf_beneficiario, data_pagamento, indice_vinculado,
                        data_atualizacao, usuario_id, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ATIVO')""", 
                    (valor, data_inicial, data_final, percentual_concedido, salario_13, um_terco_ferias, 
                     observacoes, beneficiario_id, cpf_beneficiario, data_pagamento, indice_vinculado, data_atualizacao, id_usuario_logado))
            messagebox.showinfo("Sucesso", "Parâmetro cadastrado com sucesso! O parâmetro anterior (se houver) foi inativado.", parent=janelaPagamentos)
            janelaPagamentos.destroy()
        except sqlite3.Error as e:
            messagebox.showerror("Erro de Banco de Dados", f"Ocorreu um erro ao salvar o pagamento:\n{e}", parent=janelaPagamentos)

    # --- Lógica para mostrar/esconder campos dinamicamente ---
    percentual_var = tk.StringVar()
    valor_var = tk.StringVar()

    def on_percentual_change(*args):
        if percentual_var.get().strip():
            entry_valor.configure(state="disabled")
            valor_var.set("")
            label_indice_vinculado.pack(pady=3)
            combo_indice_vinculado.pack(pady=2)
        else:
            if not valor_var.get().strip():
                entry_valor.configure(state="normal")
            label_indice_vinculado.pack_forget()
            combo_indice_vinculado.pack_forget()

    def on_valor_change(*args):
        if valor_var.get().strip():
            entry_percentual.configure(state="disabled")
            percentual_var.set("")
            label_indice_vinculado.pack_forget()
            combo_indice_vinculado.pack_forget()
        else:
            if not percentual_var.get().strip():
                entry_percentual.configure(state="normal")

    percentual_var.trace_add("write", on_percentual_change)
    valor_var.trace_add("write", on_valor_change)
    # --- Fim da lógica dinâmica ---

    janelaPagamentos = ctk.CTkToplevel()
    janelaPagamentos.title("Cadastro Pagamento")
    janelaPagamentos.geometry("400x700")
    janelaPagamentos.wm_attributes("-topmost", True)
    ctk.set_default_color_theme("blue")
    
    scroll_frame = ctk.CTkScrollableFrame(janelaPagamentos, width=420, height=620)
    scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    ctk.CTkLabel(scroll_frame, text="Data Inicial (MM/AAAA):").pack(pady=3)
    entry_data_inicial = ctk.CTkEntry(scroll_frame, width=200)
    entry_data_inicial.pack(pady=2)
    
    ctk.CTkLabel(scroll_frame, text="Data Final (MM/AAAA):").pack(pady=3)
    entry_data_final = ctk.CTkEntry(scroll_frame, width=200)
    entry_data_final.pack(pady=2)

    ctk.CTkLabel(scroll_frame, text="Percentual Concedido (%):").pack(pady=3)
    entry_percentual = ctk.CTkEntry(scroll_frame, width=200, textvariable=percentual_var)
    entry_percentual.pack(pady=2)
    
    # Widgets para o índice vinculado (inicialmente escondidos)
    label_indice_vinculado = ctk.CTkLabel(scroll_frame, text="Vincular ao Índice:")
    combo_indice_vinculado = ctk.CTkComboBox(scroll_frame, width=200, values=tipos_de_indice, state="readonly")
    combo_indice_vinculado.set(tipos_de_indice[0])
    label_indice_vinculado.pack_forget()
    combo_indice_vinculado.pack_forget()

    ctk.CTkLabel(scroll_frame, text="Valor Informado:").pack(pady=3)
    entry_valor = ctk.CTkEntry(scroll_frame, width=200, textvariable=valor_var)
    entry_valor.pack(pady=2)
    
    var_salario_13 = tk.IntVar()
    ctk.CTkCheckBox(scroll_frame, text="13º Salário", variable=var_salario_13).pack(pady=5)
    
    var_um_terco_ferias = tk.IntVar()
    ctk.CTkCheckBox(scroll_frame, text="1/3 de férias", variable=var_um_terco_ferias).pack(pady=5)

    ctk.CTkLabel(scroll_frame, text="Observação:").pack(pady=3)
    entry_observacoes = tk.Text(scroll_frame, width=38, height=4)
    entry_observacoes.pack(pady=2)
    
    conn = sqlite3.connect(resource_path('banco.db'))
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome_completo FROM beneficiarios")
    beneficiarios = cursor.fetchall()
    conn.close()
    nomes_beneficiarios = [nome for (id, nome) in beneficiarios]
    nomes_beneficiarios_base = sorted(list(nomes_beneficiarios))

    ctk.CTkLabel(scroll_frame, text="Beneficiário:").pack(pady=3)
    search_var = tk.StringVar()
    entry_search = ctk.CTkEntry(scroll_frame, width=200, placeholder_text="Pesquisar beneficiário...", textvariable=search_var)
    entry_search.pack(pady=(0, 4))

    # Lista base (ordenada) e lista atual que será mostrada no combo
    nomes_beneficiarios_base = sorted(list(nomes_beneficiarios))
    nomes_beneficiarios_atual = list(nomes_beneficiarios_base)  # cópia mutável usada para filtrar

    combo_beneficiarios = ctk.CTkComboBox(scroll_frame, width=200, values=nomes_beneficiarios_atual, state="readonly")
    combo_beneficiarios.pack(pady=2)

    ctk.CTkLabel(scroll_frame, text="CPF do Beneficiário:").pack(pady=3)
    entry_cpf = ctk.CTkEntry(scroll_frame, width=200)
    entry_cpf.pack(pady=2)

    def atualizar_opcoes_combo(termo=""):
        termo = termo.strip().lower()
        # sempre manter ordenação alfabética; quando termo vazio, mostrar todos
        if termo == "":
            filtrar = nomes_beneficiarios_base
        else:
            filtrar = [n for n in nomes_beneficiarios_base if termo in n.lower()]
        # atualiza a lista usada pelo combo
        nomes_beneficiarios_atual[:] = filtrar  # modifica a lista em-place
        # atualizar valores do combo; se não houver resultados, mostrar vazio
        combo_beneficiarios.configure(values=nomes_beneficiarios_atual)
        # opcional: resetar seleção se a atual não estiver mais presente
        atual = combo_beneficiarios.get()
        if atual not in nomes_beneficiarios_atual:
            if nomes_beneficiarios_atual:
                combo_beneficiarios.set(nomes_beneficiarios_atual[0])
            else:
                combo_beneficiarios.set("")

    # ligar evento de digitação para filtrar em tempo real
    def on_search_var_change(*args):
        atualizar_opcoes_combo(search_var.get())

    search_var.trace_add("write", on_search_var_change)

    def preencher_cpf(nome=None):
        if nome is None:
            nome = combo_beneficiarios.get()
        conn = sqlite3.connect(resource_path('banco.db'))
        cursor = conn.cursor()
        cursor.execute("SELECT cpf FROM beneficiarios WHERE nome_completo = ?", (nome,))
        result = cursor.fetchone()
        conn.close()
        if result:
            entry_cpf.delete(0, tk.END)
            entry_cpf.insert(0, result[0])
        else:
            entry_cpf.delete(0, tk.END)

    # manter vinculação para preenchimento automático ao mudar seleção no combo
    combo_beneficiarios.configure(command=preencher_cpf)

    # inicializa CPF/seleção (exatamente como antes)
    if nomes_beneficiarios_atual:
        combo_beneficiarios.set(nomes_beneficiarios_atual[0])
    preencher_cpf()

    
    # def mascara_data_inicial(event):
    #     valor = entry_data_inicial.get().replace("-", "")[:8]
    #     novo = ""
    #     if len(valor) > 0:
    #         novo += valor[:2]
    #     if len(valor) > 2:
    #         novo += "-" + valor[2:4]
    #     if len(valor) > 4:
    #         novo += "-" + valor[4:8]
    #     entry_data_inicial.delete(0, tk.END)
    #     entry_data_inicial.insert(0, novo)
    
    def mascara_data_inicial(event):
        valor = entry_data_inicial.get().replace("/", "")[:6]
        novo = ""
        if len(valor) > 0:
            novo += valor[:2]
        if len(valor) > 2:
            novo += "/" + valor[2:6]
        entry_data_inicial.delete(0, tk.END)
        entry_data_inicial.insert(0, novo)

    def mascara_data_final(event):
        valor = entry_data_final.get().replace("/", "")[:6]
        novo = ""
        if len(valor) > 0:
            novo += valor[:2]
        if len(valor) > 2:
            novo += "/" + valor[2:6]
        entry_data_final.delete(0, tk.END)
        entry_data_final.insert(0, novo)
        
    # def mascara_data_pagamento(event):
    #     valor = entry_data_pagamento.get().replace("-", "")[:8]
    #     novo = ""
    #     if len(valor) > 0:
    #         novo += valor[:2]
    #     if len(valor) > 2:
    #         novo += "-" + valor[2:4]
    #     if len(valor) > 4:
    #         novo += "-" + valor[4:8]
    #     entry_data_pagamento.delete(0, tk.END)
    #     entry_data_pagamento.insert(0, novo)
        
    
    ctk.CTkButton(scroll_frame, text="Salvar", command=salvar_pagamento, fg_color="#a1970c", hover_color="#d37b08", text_color="#fff", corner_radius=18).pack(pady=10)
    ctk.CTkButton(scroll_frame, text="Cancelar", command=janelaPagamentos.destroy, fg_color="#a1970c", hover_color="#d37b08", text_color="#fff", corner_radius=18).pack(pady=5)
    
    entry_data_inicial.bind("<KeyRelease>", mascara_data_referencia)
    entry_data_final.bind("<KeyRelease>", mascara_data_referencia)

#==============================================================================================#

def listar_pagamentos():
    janelaListarPagamentos = ctk.CTkToplevel()
    janelaListarPagamentos.title("Lista de Parâmetros de Pagamentos")
    janelaListarPagamentos.geometry("1000x500")
    janelaListarPagamentos.wm_attributes("-topmost", True)
    ctk.set_default_color_theme("blue")
    
    frame_principal = ctk.CTkFrame(janelaListarPagamentos)
    frame_principal.pack(fill="both", expand=True, padx=5, pady=5)
    
    colunas =("ID", "Beneficiário", "CPF", "Valor Fixo", "Percentual", "Índice Vinculado", "Data Inicial", "Data Final", "1/3 Férias", "13º Salário", "Observações", "Data Alteração", "Usuário", "Status")
    
    tree = ttk.Treeview(frame_principal, columns=colunas, show='headings')
    
    for col in colunas:
        tree.heading(col, text=col, command=lambda c=col: sort_by_column(tree, c, False))
        tree.column(col, width=120, anchor='center')
    
    scrollbar_vertical = ttk.Scrollbar(frame_principal, orient="vertical", command=tree.yview)
    scrollbar_horizontal = ttk.Scrollbar(frame_principal, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=scrollbar_vertical.set, xscrollcommand=scrollbar_horizontal.set)
    tree.grid(row=0, column=0, sticky='nsew')
    scrollbar_vertical.grid(row=0, column=1, sticky='ns')
    scrollbar_horizontal.grid(row=1, column=0, sticky='ew')
    frame_principal.grid_rowconfigure(0, weight=1)
    frame_principal.grid_columnconfigure(0, weight=1)
    
    # Tags para cores de linha alternadas (efeito "zebra")
    tree.tag_configure('oddrow', background='#F0F0F0') # Cinza claro
    tree.tag_configure('evenrow', background='white')

    # Variável para manter a lista completa de dados para o filtro
    lista_completa_parametros = []

    def carregar_e_formatar_parametros():
        """Busca os dados do banco e os formata para exibição."""
        with sqlite3.connect(resource_path('banco.db')) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    p.id, b.nome_completo, p.cpf_beneficiario, p.valor, p.percentual_concedido,
                    p.indice_vinculado, p.data_inicial, p.data_final, p.um_terco_ferias, p.salario_13, 
                    p.observacoes, p.data_atualizacao, u.nome_usuario, p.status
                FROM pagamentos p
                JOIN beneficiarios b ON p.beneficiario_id = b.id
                LEFT JOIN users u ON p.usuario_id = u.id_usuario
            """)
            pagamentos_db = cursor.fetchall()

        pagamentos_formatados = []
        for pagamento in pagamentos_db:
            pagamento_lista = list(pagamento)
            pagamento_lista = ["" if valor is None else valor for valor in pagamento_lista]
            pagamento_lista[8] = "Sim" if pagamento_lista[8] else "Não"
            pagamento_lista[9] = "Sim" if pagamento_lista[9] else "Não"
            if pagamento_lista[11]:
                pagamento_lista[11] = datetime.strptime(pagamento_lista[11], '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y %H:%M')
            else:
                pagamento_lista[11] = "N/A"
            if not pagamento_lista[12]:
                pagamento_lista[12] = "N/A (Antigo)"
            if not pagamento_lista[13]:
                pagamento_lista[13] = "ATIVO" 
            pagamentos_formatados.append(tuple(pagamento_lista))
        return pagamentos_formatados

    def popular_tree(dados):
        """Limpa e preenche a Treeview com os dados fornecidos."""
        for item in tree.get_children():
            tree.delete(item)
        for i, pagamento in enumerate(dados):
            tree.insert("", tk.END, values=pagamento, tags=('evenrow' if i % 2 == 0 else 'oddrow',))

    def atualizar_dados_e_popular_tree():
        """Função central para recarregar e exibir os dados."""
        nonlocal lista_completa_parametros
        lista_completa_parametros = carregar_e_formatar_parametros()
        popular_tree(lista_completa_parametros)
        
    filtrar = ctk.CTkLabel(frame_principal, text="Filtrar:")
    filtrar.grid(row=2, column=0, sticky='w', padx=2, pady=5)
    entry_filtro = ctk.CTkEntry(frame_principal, width=200)
    entry_filtro.grid(row=2, column=0, sticky='w', padx=50, pady=5)

    def filtrar_pagamentos(event=None):
        """Filtra os dados da lista principal sem acessar o banco novamente."""
        filtro = entry_filtro.get().strip().lower()
        dados_filtrados = [p for p in lista_completa_parametros if any(filtro in str(val).lower() for val in p)]
        popular_tree(dados_filtrados)

    entry_filtro.bind("<KeyRelease>", filtrar_pagamentos)

    def sort_by_column(tree, col, descending):
        data = [(tree.set(child, col), child) for child in tree.get_children('')]

        try:
            data.sort(key=lambda t: float(t[0]) if t[0].replace('.', '', 1).isdigit() else t[0], reverse=descending)
        except ValueError:
            data.sort(key=lambda t: t[0], reverse=descending)

        for index, (val, child) in enumerate(data):
            tree.move(child, '', index)

        tree.heading(col, command=lambda: sort_by_column(tree, col, not descending))

    def editar_parametro_pagamento(id_parametro, callback_atualizar, parent_window):
        conn = sqlite3.connect(resource_path('banco.db'), timeout=10)
        cursor = conn.cursor()
        cursor.execute("SELECT valor, data_inicial, data_final, percentual_concedido, salario_13, um_terco_ferias, observacoes, beneficiario_id, indice_vinculado, status FROM pagamentos WHERE id=?", (id_parametro,))
        parametro = cursor.fetchone()
        
        if not parametro:
            messagebox.showerror("Erro", "Parâmetro não encontrado.")
            conn.close()
            return

        valor, data_inicial, data_final, percentual, salario_13, um_terco_ferias, observacoes, beneficiario_id, indice_vinculado, status_atual = parametro

        if status_atual != 'ATIVO':
            messagebox.showwarning("Aviso", "Este é um parâmetro antigo (INATIVO) e não pode ser editado.\n\nPara fazer uma correção, edite o parâmetro ATIVO mais recente deste beneficiário.", parent=janelaListarPagamentos)
            conn.close()
            return
        
        cursor.execute("SELECT nome_completo, cpf FROM beneficiarios WHERE id=?", (beneficiario_id,))
        beneficiario_info = cursor.fetchone()
        conn.close()

        nome_beneficiario, cpf_beneficiario = beneficiario_info if beneficiario_info else ("Desconhecido", "")

        janelaEditar = ctk.CTkToplevel(parent_window)
        janelaEditar.title("Editar Parâmetro de Pagamento")
        janelaEditar.geometry("400x600")
        janelaEditar.grab_set()
        janelaEditar.transient(parent_window) # Garante que a janela fique sempre na frente da janela pai

        scroll_frame = ctk.CTkScrollableFrame(janelaEditar, width=380, height=580)
        scroll_frame.pack(expand=True, fill="both", padx=10, pady=10)

        ctk.CTkLabel(scroll_frame, text=f"Beneficiário: {nome_beneficiario}", font=("Calibri", 12, "bold")).pack(pady=5)
        ctk.CTkLabel(scroll_frame, text=f"CPF: {cpf_beneficiario}").pack(pady=5)

        # --- Lógica para mostrar/esconder campos dinamicamente ---
        percentual_var = tk.StringVar(value=str(percentual) if percentual is not None else "")
        valor_var = tk.StringVar(value=str(valor) if valor is not None else "")

        def on_percentual_change(*args):
            if percentual_var.get().strip():
                entry_valor.configure(state="disabled")
                valor_var.set("")
                label_indice.pack(pady=3)
                combo_indice.pack(pady=2)
            else:
                if not valor_var.get().strip():
                    entry_valor.configure(state="normal")
                label_indice.pack_forget()
                combo_indice.pack_forget()

        def on_valor_change(*args):
            if valor_var.get().strip():
                entry_percentual.configure(state="disabled")
                percentual_var.set("")
                label_indice.pack_forget()
                combo_indice.pack_forget()
            else:
                if not percentual_var.get().strip():
                    entry_percentual.configure(state="normal")

        percentual_var.trace_add("write", on_percentual_change)
        valor_var.trace_add("write", on_valor_change)
        # --- Fim da lógica dinâmica ---

        ctk.CTkLabel(scroll_frame, text="Data Inicial (MM/AAAA):").pack(pady=3)
        entry_data_inicial = ctk.CTkEntry(scroll_frame, width=200)
        entry_data_inicial.insert(0, data_inicial or "")
        entry_data_inicial.pack(pady=2)
        entry_data_inicial.bind("<KeyRelease>", mascara_data_referencia)

        ctk.CTkLabel(scroll_frame, text="Data Final (MM/AAAA):").pack(pady=3)
        entry_data_final = ctk.CTkEntry(scroll_frame, width=200)
        entry_data_final.insert(0, data_final or "")
        entry_data_final.pack(pady=2)
        entry_data_final.bind("<KeyRelease>", mascara_data_referencia)

        ctk.CTkLabel(scroll_frame, text="Valor Fixo:").pack(pady=3)
        entry_valor = ctk.CTkEntry(scroll_frame, width=200, textvariable=valor_var)
        entry_valor.pack(pady=2)

        ctk.CTkLabel(scroll_frame, text="Percentual (%):").pack(pady=3)
        entry_percentual = ctk.CTkEntry(scroll_frame, width=200, textvariable=percentual_var)
        entry_percentual.pack(pady=2)

        label_indice = ctk.CTkLabel(scroll_frame, text="Índice Vinculado:")
        tipos_de_indice = ["Salário Mínimo", "Índice Judicial A", "Índice Judicial B", "Índice Judicial C"]
        combo_indice = ctk.CTkComboBox(scroll_frame, width=200, values=tipos_de_indice, state="readonly")
        combo_indice.set(indice_vinculado or tipos_de_indice[0])

        # Estado inicial dos campos
        if percentual_var.get():
            entry_valor.configure(state="disabled")
            label_indice.pack(pady=3)
            combo_indice.pack(pady=2)
        elif valor_var.get():
            entry_percentual.configure(state="disabled")
            label_indice.pack_forget()
            combo_indice.pack_forget()

        var_13 = tk.IntVar(value=salario_13 or 0)
        ctk.CTkCheckBox(scroll_frame, text="13º Salário", variable=var_13).pack(pady=5)

        var_ferias = tk.IntVar(value=um_terco_ferias or 0)
        ctk.CTkCheckBox(scroll_frame, text="1/3 de Férias", variable=var_ferias).pack(pady=5)

        ctk.CTkLabel(scroll_frame, text="Observações:").pack(pady=3)
        text_obs = tk.Text(scroll_frame, width=38, height=4)
        try:
            txt = "" if observacoes is None else str(observacoes)
        except Exception:
            txt = ""
        text_obs.delete("1.0", tk.END)
        text_obs.insert("1.0", txt)
        text_obs.pack(pady=2)

        def salvar():
            # Coleta e valida os dados da tela
            novo_valor = entry_valor.get().strip()
            novo_percentual = entry_percentual.get().strip()
            nova_data_inicial = entry_data_inicial.get().strip()
            nova_data_final = entry_data_final.get().strip()
            novo_indice_vinculado = combo_indice.get() if novo_percentual else None
            novo_salario_13 = var_13.get()
            novas_ferias = var_ferias.get()
            novas_observacoes = text_obs.get("1.0", tk.END).strip()

            # Validações (simplificadas, podem ser expandidas)
            if not nova_data_inicial:
                messagebox.showerror("Erro", "Data Inicial é obrigatória.", parent=janelaEditar)
                return
            if not novo_valor and not novo_percentual:
                messagebox.showerror("Erro", "É necessário informar um Valor Fixo ou um Percentual.", parent=janelaEditar)
                return

            try:
                with sqlite3.connect(resource_path('banco.db')) as conn:
                    cursor = conn.cursor()
                    
                    # Ação 1: Inativa o registro antigo, marcando-o como 'INATIVO'
                    cursor.execute("UPDATE pagamentos SET status = 'INATIVO' WHERE id = ?", (id_parametro,))

                    # Ação 2: Insere um novo registro com os dados atualizados e status 'ATIVO'
                    cursor.execute("""
                        INSERT INTO pagamentos (
                            valor, data_inicial, data_final, percentual_concedido, salario_13, 
                            um_terco_ferias, observacoes, beneficiario_id, cpf_beneficiario, 
                            indice_vinculado, data_atualizacao, usuario_id, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ATIVO')
                    """, (
                        novo_valor or None, nova_data_inicial, nova_data_final or None, novo_percentual or None,
                        novo_salario_13, novas_ferias, novas_observacoes, beneficiario_id,
                        cpf_beneficiario, novo_indice_vinculado, datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        id_usuario_logado
                    ))
                
                # 1. Destrói a janela de edição PRIMEIRO para liberar o foco (grab_set).
                janelaEditar.destroy()
                # 2. Atualiza a lista de parâmetros na janela principal.
                callback_atualizar()
                # 3. Exibe a mensagem de sucesso por último, agora sem conflitos.
                messagebox.showinfo("Sucesso", "Parâmetro atualizado com sucesso! A versão anterior foi marcada como INATIVA.")

            except sqlite3.Error as e:
                messagebox.showerror("Erro de Banco de Dados", f"Ocorreu um erro ao salvar a nova versão do parâmetro:\n{e}", parent=janelaEditar)

        ctk.CTkButton(scroll_frame, text="Salvar Alterações", command=salvar).pack(pady=10)

    def on_double_click(event):
        item_selecionado = tree.selection()
        if item_selecionado:
            id_parametro = tree.item(item_selecionado[0], "values")[0]
            # Passa a função de atualização e a janela pai como argumentos
            editar_parametro_pagamento(id_parametro, atualizar_dados_e_popular_tree, janelaListarPagamentos)

    tree.bind("<Double-1>", on_double_click)
    # Carga inicial dos dados
    atualizar_dados_e_popular_tree()

#==============================================================================================#

def abrir_gerar_pagamento(prefill_mes=None):
    # Busca a lista de beneficiários para popular o combobox
    try:
        conn = sqlite3.connect(resource_path('banco.db'))
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome_completo FROM beneficiarios ORDER BY nome_completo")
        beneficiarios_db = cursor.fetchall()
        conn.close()
        
        mapa_beneficiarios = {nome: id for id, nome in beneficiarios_db}
        nomes_beneficiarios_base = sorted(list(mapa_beneficiarios.keys()))
        # Adiciona a opção para gerar para todos
        nomes_beneficiarios = ["-- Todos os Beneficiários --"] + nomes_beneficiarios_base
    except sqlite3.Error as e:
        messagebox.showerror("Erro de Banco de Dados", f"Não foi possível carregar a lista de beneficiários:\n{e}")
        return

    def gerar():
        data_referencia = entry_data_referencia.get().strip()
        nome_selecionado = combo_beneficiarios.get()

        if not re.match(r"^(0[1-9]|1[0-2])/[0-9]{4}$", data_referencia):
            messagebox.showerror("Erro", "Formato da data de referência inválido. Use MM/AAAA.", parent=janela)
            return

        beneficiario_id = None
        msg_beneficiario = "todos os beneficiários ativos"
        if nome_selecionado != "-- Todos os Beneficiários --":
            beneficiario_id = mapa_beneficiarios.get(nome_selecionado)
            msg_beneficiario = f"o beneficiário '{nome_selecionado}'"
            if beneficiario_id is None:
                messagebox.showerror("Erro", "Beneficiário selecionado não encontrado.", parent=janela)
                return

        resposta = messagebox.askyesno(
            "Confirmar Geração",
            f"Você está prestes a gerar/sobrescrever os pagamentos para {msg_beneficiario} no mês de referência {data_referencia}.\n\nIsso apagará quaisquer pagamentos já gerados para este(s) beneficiário(s) neste mês. Deseja continuar?",
            parent=janela
        )
        if not resposta:
            return

        try:
            # Verifica se a folha do mês de referência está aberta antes de gerar
            def _is_folha_aberta(mes):
                try:
                    conn = sqlite3.connect(resource_path('banco.db'))
                    cursor = conn.cursor()
                    mes_norm = mes.strip()
                    cursor.execute(
                        "SELECT status FROM folhas WHERE TRIM(mes_referencia) = ? "
                        "ORDER BY COALESCE(data_alteracao, data_fechamento) DESC, id DESC LIMIT 1",
                        (mes_norm,)
                    )
                    r = cursor.fetchone()
                    if not r:
                        # Se não existe registro, consideramos aberta (será criada ao fechar)
                        return True
                    status_db = r[0]
                    return str(status_db).upper() != 'FECHADA'
                except sqlite3.Error:
                    # Em caso de erro de BD, permitir a operação para não quebrar fluxo
                    return True
                finally:
                    try:
                        conn.close()
                    except Exception:
                        pass

            if not _is_folha_aberta(data_referencia):
                messagebox.showwarning("Folha Fechada", "Folha de pagamento fechada!", parent=janela)
                return
            

            # Passa a data de pagamento informada ao gerar os registros (se vazia, será tratada pelo gerar_pagamentos)
            data_pagamento_informada = None
            try:
                data_pagamento_informada = entry_data_pagamento.get().strip() if entry_data_pagamento.get().strip() != "" else None
            except Exception:
                data_pagamento_informada = None

            status_geracao = gerar_pagamentos(mes_referencia=data_referencia, beneficiario_id=beneficiario_id, data_de_pagamento=data_pagamento_informada)
            
            if status_geracao == "SUCCESS":
                if beneficiario_id is not None:
                    messagebox.showinfo("Sucesso", 
                        f"Pagamento para '{nome_selecionado}' no mês {data_referencia} gerado com sucesso!", 
                        parent=janela)
                else: # Todos os beneficiários
                    messagebox.showinfo("Sucesso", f"Pagamentos e relatórios para {data_referencia} gerados com sucesso!", parent=janela)

            elif status_geracao == "PARTIAL_SUCCESS":
                messagebox.showwarning("Sucesso Parcial", f"Os pagamentos para {data_referencia} foram gerados, mas houve um erro ao criar o relatório PDF.", parent=janela)
            
            elif status_geracao == "ERROR":
                messagebox.showerror("Erro de Banco de Dados", "Ocorreu um erro ao salvar os pagamentos. Verifique o console para mais detalhes.", parent=janela)

            janela.destroy()
        except Exception as e:
            messagebox.showerror("Erro", f"Ocorreu um erro inesperado ao gerar os pagamentos: {e}", parent=janela)

    janela = ctk.CTkToplevel()
    janela.title("Gerar Pagamentos")
    janela.geometry("400x450")
    janela.wm_attributes("-topmost", True)
    janela.resizable(False, False)

    frame = ctk.CTkFrame(janela, fg_color="transparent")
    frame.pack(expand=True, padx=20, pady=20)

    ctk.CTkLabel(frame, text="Gerar Pagamentos por Mês de Referência", font=('Calibri', 16, 'bold')).pack(pady=(0, 10))
    ctk.CTkLabel(frame, text="Esta operação irá calcular e salvar os pagamentos\npara o(s) beneficiário(s) no mês informado.", justify="center").pack(pady=(0, 20))

    ctk.CTkLabel(frame, text="Data de Pagamento (DD/MM/AAAA):").pack(pady=5)
    entry_data_pagamento = ctk.CTkEntry(frame, width=150, justify="center")
    entry_data_pagamento.pack(pady=2)
    
    ctk.CTkLabel(frame, text="Mês de Referência (MM/AAAA):").pack(pady=5)
    entry_data_referencia = ctk.CTkEntry(frame, width=150, justify="center")
    entry_data_referencia.pack(pady=2)
    # Se for passado um mês para pré-preenchimento (por exemplo após reabrir a folha), insere no campo
    try:
        if prefill_mes:
            entry_data_referencia.delete(0, tk.END)
            entry_data_referencia.insert(0, prefill_mes)
    except Exception:
        pass

    ctk.CTkLabel(frame, text="Beneficiário (Opcional):").pack(pady=(10, 5))
    search_var = tk.StringVar()
    entry_search = ctk.CTkEntry(frame, width=150, placeholder_text="Pesquisar beneficiário...", textvariable=search_var)
    entry_search.pack(pady=(0, 4))
    
    combo_beneficiarios = ctk.CTkComboBox(frame, width=300, values=nomes_beneficiarios)
    combo_beneficiarios.set("-- Todos os Beneficiários --")
    combo_beneficiarios.pack(pady=2)
    
    def atualizar_opcoes_combo(termo=""):
        termo = termo.strip().lower()
        if termo == "":
            filtrar = nomes_beneficiarios_base
        else:
            filtrar = [n for n in nomes_beneficiarios_base if termo in n.lower()]
        valores_combo = ["-- Todos os Beneficiários --"] + filtrar
        combo_beneficiarios.configure(values=valores_combo)
        atual = combo_beneficiarios.get()
        if atual not in valores_combo:
            combo_beneficiarios.set("-- Todos os Beneficiários --")
        else:
            combo_beneficiarios.set(atual)
            
    def on_search_var_change(*args):
        atualizar_opcoes_combo(search_var.get())
        
    search_var.trace_add("write", on_search_var_change)
    
    def aplicar_mascara_data_nascimento(event):
        valor = entry_data_pagamento.get().replace("/", "")[:8]
        novo = ""
        if len(valor) > 0:
            novo += valor[:2]
        if len(valor) > 2:
            novo += "/" + valor[2:4]
        if len(valor) > 4:
            novo += "/" + valor[4:8]
        entry_data_pagamento.delete(0, tk.END)
        entry_data_pagamento.insert(0, novo)
    
    entry_data_pagamento.bind("<KeyRelease>", aplicar_mascara_data_nascimento)
    entry_data_referencia.bind("<KeyRelease>", mascara_data_referencia)

    ctk.CTkButton(frame, text="Gerar Pagamentos", command=gerar, fg_color="#a1970c", hover_color="#d37b08", text_color="#fff", corner_radius=18).pack(pady=(20, 5))
    ctk.CTkButton(frame, text="Cancelar", command=janela.destroy, fg_color="#6c757d", hover_color="#5a6268", text_color="#fff", corner_radius=18).pack()
#==============================================================================================#

def listar_pagamentos_gerados():
    conn = sqlite3.connect(resource_path('banco.db'))
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            p.id, p.nome_beneficiario, b.cpf, p.mes_referencia,
            p.valor_13_salario, p.valor_um_terco_ferias, p.valor, -- O campo 'valor' agora é o total
            p.percentual_concedido, p.valor_indice, p.data_geracao,
            p.beneficiario_id -- ID necessário para a regeração individual
        FROM pagamento_gerados p
        LEFT JOIN beneficiarios b ON p.beneficiario_id = b.id
    """)
    pagamentos = cursor.fetchall()
    conn.close()

    if not pagamentos:
        messagebox.showinfo("Info", "Nenhum pagamento gerado encontrado.")
        return

    janelaPagementos_gerados = ctk.CTkToplevel()
    janelaPagementos_gerados.title("Pagamentos Gerados")
    janelaPagementos_gerados.geometry("1300x400")
    janelaPagementos_gerados.wm_attributes("-topmost", True)
    ctk.set_default_color_theme("blue")

    frame_principal = ctk.CTkFrame(janelaPagementos_gerados)
    frame_principal.pack(fill="both", expand=True, padx=5, pady=5)
    
    colunas =("ID", "Beneficiário", "CPF", "Mês Ref.", "Valor Base", "Valor 13º", "Valor Férias", "Valor Total", "Percentual", "Valor Índice", "Data Geração", "Data Pagamento")
    
    tree = ttk.Treeview(frame_principal, columns=colunas, show='headings')
    
    for col in colunas:
        tree.heading(col, text=col, command=lambda c=col: sort_by_column(tree, c, False))
        tree.column(col, width=120, anchor='center')
    
    scrollbar_vertical = ttk.Scrollbar(frame_principal, orient="vertical", command=tree.yview)
    scrollbar_horizontal = ttk.Scrollbar(frame_principal, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=scrollbar_vertical.set, xscrollcommand=scrollbar_horizontal.set)
    tree.grid(row=0, column=0, sticky='nsew')
    scrollbar_vertical.grid(row=0, column=1, sticky='ns')
    scrollbar_horizontal.grid(row=1, column=0, sticky='ew')
    frame_principal.grid_rowconfigure(0, weight=1)
    frame_principal.grid_columnconfigure(0, weight=1)
    
    def sort_by_column(tree, col, descending):
        data = [(tree.set(child, col), child) for child in tree.get_children('')]

        try:
            data.sort(key=lambda t: float(t[0]) if t[0].replace('.', '', 1).isdigit() else t[0], reverse=descending)
        except ValueError:
            data.sort(key=lambda t: t[0], reverse=descending)

        for index, (val, child) in enumerate(data):
            tree.move(child, '', index)

        tree.heading(col, command=lambda: sort_by_column(tree, col, not descending))

    def carregar_dados(tree_widget):
        # Limpa a árvore antes de carregar novos dados
        for item in tree_widget.get_children():
            tree_widget.delete(item)

        conn = sqlite3.connect(resource_path('banco.db'))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                p.id, p.nome_beneficiario, b.cpf, p.mes_referencia, 
                p.valor_13_salario, p.valor_um_terco_ferias, p.valor,
                p.percentual_concedido, p.valor_indice, p.data_geracao, p.data_de_pagamento,
                p.beneficiario_id
            FROM pagamento_gerados p
            LEFT JOIN beneficiarios b ON p.beneficiario_id = b.id
        """)
        pagamentos = cursor.fetchall()
        conn.close()

        tree.tag_configure('oddrow', background='#F0F0F0')
        tree.tag_configure('evenrow', background='white')

        for i, pagamento_tupla in enumerate(pagamentos):
            pagamento_lista = list(pagamento_tupla)
            try:
                valor_13 = float(pagamento_lista[4] or 0)
                valor_ferias = float(pagamento_lista[5] or 0)
                valor_total = float(pagamento_lista[6] or 0)
                valor_base = valor_total - valor_13 - valor_ferias
            except (ValueError, TypeError):
                valor_base = 0.0
            
            pagamento_lista.insert(4, f"{valor_base:.2f}")
            # Formata a coluna 'data_de_pagamento' (índice original 10) para dd-mm-YYYY ao exibir
            try:
                idx_data_pag = 10
                raw_data = pagamento_lista[idx_data_pag]
                if raw_data and isinstance(raw_data, str):
                    # Se estiver no formato YYYY-MM-DD ou YYYY-MM-DD HH:MM:SS
                    import re
                    m_iso = re.match(r"^(\d{4})-(\d{2})-(\d{2})(?:.*)$", raw_data)
                    m_dmy = re.match(r"^(\d{2})-(\d{2})-(\d{4})(?:.*)$", raw_data)
                    if m_iso:
                        y, mo, d = m_iso.group(1), m_iso.group(2), m_iso.group(3)
                        pagamento_lista[idx_data_pag] = f"{d}-{mo}-{y}"
                    elif m_dmy:
                        # já está dd-mm-YYYY
                        pagamento_lista[idx_data_pag] = raw_data.split(' ')[0]
                    else:
                        # mantem como string original
                        pagamento_lista[idx_data_pag] = raw_data
                else:
                    pagamento_lista[idx_data_pag] = '' if not raw_data else str(raw_data)
            except Exception:
                # Se algo falhar, segue com o valor original
                pass
            tree_widget.insert("", tk.END, values=pagamento_lista, tags=('evenrow' if i % 2 == 0 else 'oddrow',))

    def regerar_pagamento_selecionado():
        selected_item = tree.selection()
        if not selected_item:
            messagebox.showwarning("Nenhuma Seleção", "Por favor, selecione um pagamento na lista para regerar.", parent=janelaPagementos_gerados)
            return

        item_values = tree.item(selected_item[0], "values")
        mes_referencia = item_values[3]
        beneficiario_id = item_values[-1]  # O ID do beneficiário está no final da tupla de dados
        nome_beneficiario = item_values[1]

        resposta = messagebox.askyesno(
            "Confirmar Geração Individual",
            f"Você está prestes a regerar o pagamento para:\n\n"
            f"Beneficiário: {nome_beneficiario}\n"
            f"Mês de Referência: {mes_referencia}\n\n"
            "Isso irá substituir o pagamento existente. Deseja continuar?",
            parent=janelaPagementos_gerados
        )
        if not resposta:
            return

        # Antes de regerar, verifica se a folha do mês está aberta
        try:
            conn = sqlite3.connect(resource_path('banco.db'))
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM folhas WHERE mes_referencia = ?", (mes_referencia,))
            r = cursor.fetchone()
            if r and str(r[0]).upper() == 'FECHADA':
                messagebox.showwarning("Folha Fechada", "folha de pagamento fechada", parent=janelaPagementos_gerados)
                return
        except sqlite3.Error:
            # Em caso de erro de BD, permite tentar regerar (comportamento antigo)
            pass
        finally:
            try:
                conn.close()
            except Exception:
                pass

        # A função agora só retorna "SUCCESS" ou "ERROR" para chamadas individuais
        status_geracao = gerar_pagamentos(mes_referencia=mes_referencia, beneficiario_id=int(beneficiario_id))
        if status_geracao == "SUCCESS":
            messagebox.showinfo("Sucesso", 
                f"Pagamento para {nome_beneficiario} regerado com sucesso!\n\n"
                "Para atualizar o relatório do mês, use a opção:\n"
                "'Ferramentas -> Gerar Relatório de Pagamentos'", 
                parent=janelaPagementos_gerados)
            carregar_dados(tree) # Atualiza a lista
        else:
            messagebox.showerror("Erro", "Ocorreu um erro ao regerar o pagamento. Verifique o console.", parent=janelaPagementos_gerados)

    # Frame para os botões
    frame_botoes = ctk.CTkFrame(frame_principal, fg_color="transparent")
    frame_botoes.grid(row=2, column=0, pady=10, sticky='e')
    
    filtrar = ctk.CTkLabel(frame_principal, text="Filtrar:", font=('Calibri', 16, 'italic'), text_color="black")
    filtrar.grid(row=2, column=0, pady=2, sticky='w')
    
    entry_filtro = ctk.CTkEntry(frame_principal, width=150)
    entry_filtro.grid(row=2, column=0, padx=50, sticky='w')
    
    def filtrar_pagamentos(event=None):
        filtro = entry_filtro.get().strip().lower()
        for item in tree.get_children():
            tree.delete(item)
        for i, pagamento_tupla in enumerate(pagamentos):
            pagamento_lista = list(pagamento_tupla)
            try:
                valor_13 = float(pagamento_lista[4] or 0)
                valor_ferias = float(pagamento_lista[5] or 0)
                valor_total = float(pagamento_lista[6] or 0)
                valor_base = valor_total - valor_13 - valor_ferias
            except (ValueError, TypeError):
                valor_base = 0.0
            pagamento_lista.insert(4, f"{valor_base:.2f}")
            if any(filtro in str(valor).lower() for valor in pagamento_lista):
                tree.insert("", tk.END, values=pagamento_lista, tags=('evenrow' if i % 2 == 0 else 'oddrow',))
                
    entry_filtro.bind("<KeyRelease>", filtrar_pagamentos)

    btn_regerar = ctk.CTkButton(frame_botoes, text="Reabrir a folha", command=regerar_pagamento_selecionado, fg_color="#a1970c", hover_color="#d37b08", text_color="#fff", corner_radius=18)
    btn_regerar.pack()

    # Carrega os dados na árvore ao abrir a janela
    carregar_dados(tree)

def abrir_gerar_relatorio(): 
    # Busca a lista de beneficiários para popular o combobox
    try:
        conn = sqlite3.connect(resource_path('banco.db'))
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome_completo FROM beneficiarios ORDER BY nome_completo")
        beneficiarios_db = cursor.fetchall()
        conn.close()
        
        mapa_beneficiarios_relatorio = {nome: id for id, nome in beneficiarios_db}
        # Adiciona a opção para gerar o relatório completo
        nomes_beneficiarios_relatorio = ["-- Todos os Beneficiários --"] + list(mapa_beneficiarios_relatorio.keys())
    except sqlite3.Error as e:
        messagebox.showerror("Erro de Banco de Dados", f"Não foi possível carregar a lista de beneficiários:\n{e}")
        return

    def gerar():
        mes_inicial = entry_data_inicial.get().strip()
        mes_final = entry_data_final.get().strip()
        save_path = entry_caminho_pasta.get().strip()
        nome_selecionado = combo_beneficiarios.get()

        # Validações
        if not (re.match(r"^(0[1-9]|1[0-2])/[0-9]{4}$", mes_inicial) and re.match(r"^(0[1-9]|1[0-2])/[0-9]{4}$", mes_final)):
            messagebox.showerror("Erro de Formato", "Formato da data de referência inválido. Use MM/AAAA.", parent=janela)
            return
        
        if not save_path:
            messagebox.showerror("Erro de Validação", "Por favor, selecione uma pasta para salvar os relatórios.", parent=janela)
            return

        try:
            data_inicial_dt = datetime.strptime(mes_inicial, "%m/%Y")
            data_final_dt = datetime.strptime(mes_final, "%m/%Y")
            if data_final_dt < data_inicial_dt:
                messagebox.showerror("Erro de Validação", "A data final não pode ser anterior à data inicial.", parent=janela)
                return
        except ValueError: # Segurança extra, embora o regex já filtre
            messagebox.showerror("Erro de Formato", "As datas devem estar no formato MM/AAAA.", parent=janela)
            return

        beneficiario_id = None
        if nome_selecionado != "-- Todos os Beneficiários --":
            beneficiario_id = mapa_beneficiarios_relatorio.get(nome_selecionado)

        try:
            status_relatorio = gerar_relatorios_por_periodo(
                mes_inicial=mes_inicial,
                mes_final=mes_final,
                save_path=save_path,
                beneficiario_id=beneficiario_id
            )
            
            if status_relatorio == "SUCCESS":
                messagebox.showinfo("Sucesso", f"Relatórios para o período de {mes_inicial} a {mes_final} gerados com sucesso em:\n{save_path}", parent=janela)
                janela.destroy()
            elif status_relatorio == "PARTIAL_SUCCESS":
                messagebox.showwarning("Sucesso Parcial", f"Relatório TXT foi gerado, mas houve um erro ao criar o relatório PDF.", parent=janela)
                janela.destroy()
            elif status_relatorio == "NO_DATA":
                msg = f"Nenhum pagamento encontrado no período de {mes_inicial} a {mes_final}."
                if beneficiario_id:
                    msg += f" para '{nome_selecionado}'."
                messagebox.showinfo("Informação", f"{msg} Nenhum relatório foi gerado.", parent=janela)
            elif status_relatorio == "ERROR":
                messagebox.showerror("Erro de Banco de Dados", "Ocorreu um erro ao buscar os dados para o relatório. Verifique o console para mais detalhes.", parent=janela)

        except Exception as e:
            messagebox.showerror("Erro", f"Ocorreu um erro inesperado ao gerar os relatórios: {e}", parent=janela)

    def selecionar_pasta():
        caminho = filedialog.askdirectory(title="Selecione a pasta para salvar os relatórios", parent=janela)
        if caminho:
            entry_caminho_pasta.delete(0, tk.END)
            entry_caminho_pasta.insert(0, caminho)

    janela = ctk.CTkToplevel()
    janela.title("Gerar Relatório de Pagamentos")
    janela.geometry("450x600")
    janela.wm_attributes("-topmost", True)

    frame = ctk.CTkFrame(janela, fg_color="transparent")
    frame.pack(expand=True, padx=20, pady=20)

    ctk.CTkLabel(frame, text="Gerar Relatórios por Período", font=('Calibri', 16, 'bold')).pack(pady=(0, 10))
    ctk.CTkLabel(frame, text="Esta operação irá gerar os arquivos TXT e PDF\ncom base nos pagamentos já existentes no banco.", justify="center").pack(pady=(0, 20))

    # --- Campos de Período ---
    ctk.CTkLabel(frame, text="Referência Inicial (MM/AAAA):").pack(pady=5)
    entry_data_inicial = ctk.CTkEntry(frame, width=150, justify="center")
    entry_data_inicial.pack(pady=2)

    ctk.CTkLabel(frame, text="Referência Final (MM/AAAA):").pack(pady=5)
    entry_data_final = ctk.CTkEntry(frame, width=150, justify="center")
    entry_data_final.pack(pady=2)

    # Preenche os campos com o mês e ano atuais para conveniência do usuário
    data_atual = datetime.now().strftime("%m/%Y")
    entry_data_inicial.insert(0, data_atual)
    entry_data_final.insert(0, data_atual)

    # --- Seletor de Beneficiário (Opcional) ---
    ctk.CTkLabel(frame, text="Beneficiário (Opcional):").pack(pady=(10, 5))
    search_var = tk.StringVar()
    entry_search = ctk.CTkEntry(frame, width=150, placeholder_text="Pesquisar beneficiário...", textvariable=search_var)
    entry_search.pack(pady=(0, 4))

    
    combo_beneficiarios = ctk.CTkComboBox(frame, width=300, values=nomes_beneficiarios_relatorio)
    combo_beneficiarios.set("-- Todos os Beneficiários --")
    combo_beneficiarios.pack(pady=2)
    
    def atualizar_opcoes_combo(termo=""):
        termo = termo.strip().lower()
        if termo == "":
            filtrar = list(mapa_beneficiarios_relatorio.keys())
        else:
            filtrar = [n for n in mapa_beneficiarios_relatorio.keys() if termo in n.lower()]
        valores_combo = ["-- Todos os Beneficiários --"] + filtrar
        combo_beneficiarios.configure(values=valores_combo)
        atual = combo_beneficiarios.get()
        if atual not in valores_combo:
            combo_beneficiarios.set("-- Todos os Beneficiários --")
        else:
            combo_beneficiarios.set(atual)
            
    def on_search_var_change(*args):
        atualizar_opcoes_combo(search_var.get())
        
    search_var.trace_add("write", on_search_var_change)

    # --- Seletor de Pasta ---
    ctk.CTkLabel(frame, text="Salvar Relatórios em:").pack(pady=(15, 5))
    entry_caminho_pasta = ctk.CTkEntry(frame, width=300)
    entry_caminho_pasta.pack(pady=2)
    btn_selecionar_pasta = ctk.CTkButton(frame, text="Selecionar Pasta...", command=selecionar_pasta, width=150)
    btn_selecionar_pasta.pack(pady=5)

    entry_data_inicial.bind("<KeyRelease>", mascara_data_referencia)
    entry_data_final.bind("<KeyRelease>", mascara_data_referencia)

    ctk.CTkButton(frame, text="Gerar Relatórios", command=gerar, width=150, fg_color="#a1970c", hover_color="#d37b08", text_color="#fff", corner_radius=18).pack(pady=(20, 5))
    ctk.CTkButton(frame, text="Cancelar", command=janela.destroy, fg_color="#6c757d", hover_color="#5a6268", text_color="#fff", corner_radius=18).pack()
#==============================================================================================#

def abrir_gerar_doc_empenho():
    def gerar():
        mes_inicial = entry_data_inicial.get().strip()
        mes_final = entry_data_final.get().strip()
        save_path = entry_caminho_pasta.get().strip()

        # Validações
        if not (re.match(r"^(0[1-9]|1[0-2])/[0-9]{4}$", mes_inicial) and re.match(r"^(0[1-9]|1[0-2])/[0-9]{4}$", mes_final)):
            messagebox.showerror("Erro de Formato", "Formato da data de referência inválido. Use MM/AAAA.", parent=janela)
            return
        
        if not save_path:
            messagebox.showerror("Erro de Validação", "Por favor, selecione uma pasta para salvar o documento.", parent=janela)
            return

        try:
            data_inicial_dt = datetime.strptime(mes_inicial, "%m/%Y")
            data_final_dt = datetime.strptime(mes_final, "%m/%Y")
            if data_final_dt < data_inicial_dt:
                messagebox.showerror("Erro de Validação", "A data final não pode ser anterior à data inicial.", parent=janela)
                return
        except ValueError:
            messagebox.showerror("Erro de Formato", "As datas devem estar no formato MM/AAAA.", parent=janela)
            return

        # Chama a função de geração do documento
        status = gerar_documentos.gerar_documento_empenho(mes_inicial, mes_final, save_path)
        
        if status == "SUCCESS":
            # A mensagem de sucesso já é exibida pela função de geração
            janela.destroy()
        elif status == "NO_DATA":
            # A mensagem de "sem dados" já é exibida
            pass # Não fecha a janela para o usuário tentar outro período
        else: # ERROR
            # A mensagem de erro já é exibida
            pass

    def selecionar_pasta():
        caminho = filedialog.askdirectory(title="Selecione a pasta para salvar o documento", parent=janela)
        if caminho:
            entry_caminho_pasta.delete(0, tk.END)
            entry_caminho_pasta.insert(0, caminho)

    janela = ctk.CTkToplevel()
    janela.title("Gerar Documento de Empenho")
    janela.geometry("450x600")
    janela.wm_attributes("-topmost", True)
    janela.resizable(False, False)

    frame = ctk.CTkFrame(janela, fg_color="transparent")
    frame.pack(expand=True, padx=20, pady=20)

    ctk.CTkLabel(frame, text="Gerar Documento de Empenho", font=('Calibri', 16, 'bold')).pack(pady=(0, 10))
    ctk.CTkLabel(frame, text="Gera um documento PDF formal para empenho\ndos pagamentos do período selecionado.", justify="center").pack(pady=(0, 20))

    ctk.CTkLabel(frame, text="Referência Inicial (MM/AAAA):").pack(pady=5)
    entry_data_inicial = ctk.CTkEntry(frame, width=150, justify="center")
    entry_data_inicial.pack(pady=2)

    ctk.CTkLabel(frame, text="Referência Final (MM/AAAA):").pack(pady=5)
    entry_data_final = ctk.CTkEntry(frame, width=150, justify="center")
    entry_data_final.pack(pady=2)

    data_atual = datetime.now().strftime("%m/%Y")
    entry_data_inicial.insert(0, data_atual)
    entry_data_final.insert(0, data_atual)

    ctk.CTkLabel(frame, text="Salvar Documento em:").pack(pady=(15, 5))
    entry_caminho_pasta = ctk.CTkEntry(frame, width=300)
    entry_caminho_pasta.pack(pady=2)
    btn_selecionar_pasta = ctk.CTkButton(frame, text="Selecionar Pasta...", command=selecionar_pasta, width=150)
    btn_selecionar_pasta.pack(pady=5)

    entry_data_inicial.bind("<KeyRelease>", mascara_data_referencia)
    entry_data_final.bind("<KeyRelease>", mascara_data_referencia)

    ctk.CTkButton(frame, text="Gerar Documento", command=gerar, width=150, fg_color="#a1970c", hover_color="#d37b08", text_color="#fff", corner_radius=18).pack(pady=(20, 5))
    ctk.CTkButton(frame, text="Cancelar", command=janela.destroy, fg_color="#6c757d", hover_color="#5a6268", text_color="#fff", corner_radius=18).pack()

#==============================================================================================#

def abrir_gerar_comprovante_rendimentos():
    """Abre a janela para o usuário selecionar o beneficiário e o ano para gerar o comprovante."""
    
    # Busca a lista de beneficiários para popular o combobox
    try:
        with sqlite3.connect(resource_path('banco.db')) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, nome_completo FROM beneficiarios ORDER BY nome_completo")
            beneficiarios_db = cursor.fetchall()
        
        mapa_beneficiarios = {nome: id for id, nome in beneficiarios_db}
        nomes_beneficiarios = list(mapa_beneficiarios.keys())
        if not nomes_beneficiarios:
            messagebox.showinfo("Informação", "Nenhum beneficiário ativo encontrado para gerar comprovante.")
            return
    except sqlite3.Error as e:
        messagebox.showerror("Erro de Banco de Dados", f"Não foi possível carregar a lista de beneficiários:\n{e}")
        return

    def gerar_comprovante():
        # Coleta os dados da interface
        nome_selecionado = combo_beneficiarios.get()
        ano_selecionado = entry_ano_calendario.get().strip()

        if not nome_selecionado:
            messagebox.showerror("Erro", "Por favor, selecione um beneficiário.", parent=janela)
            return
        if not (ano_selecionado.isdigit() and len(ano_selecionado) == 4):
            messagebox.showerror("Erro", "Por favor, insira um ano válido (ex: 2024).", parent=janela)
            return

        beneficiario_id = mapa_beneficiarios.get(nome_selecionado)
        
        # Chama a função especialista em gerar o documento PDF
        gerar_documentos.gerar_comprovante_rendimentos_pdf(beneficiario_id, ano_selecionado, id_usuario_logado, parent_window=janela)

    janela = ctk.CTkToplevel()
    janela.title("Gerar Comprovante de Rendimentos")
    janela.geometry("400x400")
    janela.transient()
    janela.grab_set()

    frame = ctk.CTkFrame(janela, fg_color="transparent")
    frame.pack(expand=True, padx=20, pady=20)

    ctk.CTkLabel(frame, text="Gerar Comprovante de Rendimentos", font=('Calibri', 16, 'bold')).pack(pady=(0, 10))
    ctk.CTkLabel(frame, text="Selecione o beneficiário e o ano-calendário\npara gerar o documento para o Imposto de Renda.", justify="center").pack(pady=(0, 20))

    ctk.CTkLabel(frame, text="Beneficiário:").pack(pady=5)
    search_var = tk.StringVar()
    entry_search = ctk.CTkEntry(frame, width=150, placeholder_text="Pesquisar beneficiário...", textvariable=search_var)
    entry_search.pack(pady=(0, 4))
    
    combo_beneficiarios = ctk.CTkComboBox(frame, width=300, values=nomes_beneficiarios)
    combo_beneficiarios.pack(pady=2)

    ctk.CTkLabel(frame, text="Ano-Calendário:").pack(pady=(10, 5))
    entry_ano_calendario = ctk.CTkEntry(frame, width=150, justify="center")
    entry_ano_calendario.insert(0, str(datetime.now().year - 1))
    entry_ano_calendario.pack(pady=2)
    
    def atualizar_opcoes_combo(termo=""):
        termo = termo.strip().lower()
        if termo == "":
            filtrar = nomes_beneficiarios
        else:
            filtrar = [n for n in nomes_beneficiarios if termo in n.lower()]
        combo_beneficiarios.configure(values=filtrar)
        atual = combo_beneficiarios.get()
        if atual not in filtrar:
            combo_beneficiarios.set("")
        else:
            combo_beneficiarios.set(atual)
            
    def on_search_var_change(*args):
        atualizar_opcoes_combo(search_var.get())
        
    search_var.trace_add("write", on_search_var_change)


    ctk.CTkButton(frame, text="Gerar Comprovante", command=gerar_comprovante, fg_color="#a1970c", hover_color="#d37b08", text_color="#fff", corner_radius=18).pack(pady=(20, 5))
    ctk.CTkButton(frame, text="Cancelar", command=janela.destroy, fg_color="#6c757d", hover_color="#5a6268", text_color="#fff", corner_radius=18).pack()

usuario_logado = ""
id_usuario_logado = None
perfil_usuario_logado = ""

def verificar_credenciais_no_banco(usuario, senha):
    conn = sqlite3.connect(resource_path('banco.db'))
    cursor = conn.cursor()
    cursor.execute("SELECT id_usuario, senha, perfil FROM users WHERE nome_usuario = ? AND status = 'ATIVO'", (usuario,))
    resultado = cursor.fetchone()
    conn.close()
    
    if resultado:
        id_usuario, senha_hash, perfil = resultado
        if bcrypt.checkpw(senha.encode('utf-8'), senha_hash.encode('utf-8')):
            return id_usuario, perfil
    return None, None


#==============================================================================================#

def janela_gerar_excel_fita_credito():
    import tkinter.filedialog

    def selecionar_txt():
        caminho = tkinter.filedialog.askopenfilename(
            title="Selecione o arquivo TXT da fita de crédito",
            filetypes=[("Arquivo TXT", "*.txt")]
            , parent=janela
        )
        if caminho:
            txt_path.set(caminho)

    def gerar_excel():
        caminho_txt = txt_path.get().strip()
        if not caminho_txt:
            messagebox.showerror("Erro", "Selecione o arquivo TXT primeiro.", parent=janela)
            return
        try:
            excel_path = caminho_txt.replace(".txt", "_relatorio.xlsx")
            gerar_relatorio_fita_credito(caminho_txt, excel_path)
            messagebox.showinfo("Sucesso", f"Excel gerado com sucesso:\n{excel_path}", parent=janela)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao gerar Excel:\n{e}", parent=janela)
        janela.destroy()

    janela = ctk.CTkToplevel()
    janela.title("Gerar Excel da Fita de Crédito")
    janela.geometry("400x400")
    janela.grab_set()

    frame = ctk.CTkFrame(janela, fg_color="transparent")
    frame.pack(expand=True, padx=20, pady=20)

    ctk.CTkLabel(frame, text="Selecione o TXT da fita de crédito", font=('Calibri', 14, 'bold')).pack(pady=(0, 10))
    ctk.CTkLabel(frame, text="Esta ferramenta converte o arquivo TXT da fita de crédito\nem um relatório Excel organizado.", justify="center").pack(pady=(0, 20))
    txt_path = tk.StringVar()
    ctk.CTkButton(frame, text="Selecionar TXT", command=selecionar_txt).pack(pady=5)
    ctk.CTkLabel(frame, textvariable=txt_path, wraplength=300).pack(pady=(0, 10))
    ctk.CTkButton(frame, text="Gerar Excel", command=gerar_excel, fg_color="#a1970c", hover_color="#d37b08", text_color="#fff").pack(pady=10)
    ctk.CTkButton(frame, text="Cancelar", command=janela.destroy, fg_color="#6c757d", hover_color="#5a6268").pack()
    

#==============================================================================================#

def fechar_abrir_folha_pagamento(status):
    
    
    janelafolha = ctk.CTkToplevel()
    janelafolha.title("Fechar/Reabrir Folha de Pagamento")
    janelafolha.geometry("400x400")
    janelafolha.grab_set()
    
    frame = ctk.CTkFrame(janelafolha, fg_color="transparent")
    frame.pack(expand=True, padx=20, pady=20)
    
    ctk.CTkLabel(frame, text="Atenção!", font=('Calibri', 14, 'bold')).pack(pady=(0, 10))
    ctk.CTkLabel(frame, text="Esta ação irá alterar o status da folha de pagamento atual.", justify="center").pack(pady=(0, 20))
    # Campo para informar a referência da folha (MM/AAAA)
    ctk.CTkLabel(frame, text="Mês de Referência (MM/AAAA):").pack(pady=5)
    entry_data_referencia = ctk.CTkEntry(frame, width=150, justify="center")
    entry_data_referencia.pack(pady=2)
    entry_data_referencia.bind("<KeyRelease>", mascara_data_referencia)

    # Mensagem de status
    status_msg_var = tk.StringVar(value="Informe a referência e escolha uma ação")
    ctk.CTkLabel(frame, textvariable=status_msg_var, wraplength=340, text_color="#333333").pack(pady=(10, 8))

    def ensure_folhas_table():
        """Garante que a tabela 'folhas' exista com colunas para auditoria de alteração."""
        try:
            conn = sqlite3.connect(resource_path('banco.db'))
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS folhas (
                    mes_referencia TEXT PRIMARY KEY,
                    status TEXT,
                    fechado_por TEXT,
                    data_fechamento TEXT,
                    alterado_por TEXT,
                    data_alteracao TEXT
                )
            """)
            conn.commit()
            # Se a tabela existir sem as colunas novas, tenta alterá-la (silenciosamente)
            cursor.execute("PRAGMA table_info(folhas)")
            cols = [r[1] for r in cursor.fetchall()]
            if 'alterado_por' not in cols or 'data_alteracao' not in cols:
                try:
                    if 'alterado_por' not in cols:
                        cursor.execute("ALTER TABLE folhas ADD COLUMN alterado_por TEXT")
                    if 'data_alteracao' not in cols:
                        cursor.execute("ALTER TABLE folhas ADD COLUMN data_alteracao TEXT")
                    conn.commit()
                except sqlite3.Error:
                    # Em alguns cenários ALTER TABLE pode falhar (versões antigas), mas a criação inicial já garante compatibilidade
                    pass
        except sqlite3.Error as e:
            messagebox.showerror("Erro de Banco", f"Erro ao garantir tabela de folhas: {e}", parent=janelafolha)
        finally:
            if conn:
                conn.close()

    def atualizar_status_msg():
        mes = entry_data_referencia.get().strip()
        if not re.match(r"^(0[1-9]|1[0-2])/[0-9]{4}$", mes):
            status_msg_var.set("Formato inválido. Use MM/AAAA")
            return
        try:
            conn = sqlite3.connect(resource_path('banco.db'))
            cursor = conn.cursor()
            # Usa TRIM e ordena pelo registro mais recente (data_alteracao ou data_fechamento) para evitar linhas duplicadas antigas
            cursor.execute(
                "SELECT status, fechado_por, data_fechamento, alterado_por, data_alteracao FROM folhas WHERE TRIM(mes_referencia) = ? "
                "ORDER BY COALESCE(data_alteracao, data_fechamento) DESC, id DESC LIMIT 1",
                (mes,)
            )
            r = cursor.fetchone()
            if r:
                # r => (status, fechado_por, data_fechamento, alterado_por, data_alteracao) or subset
                # Ajusta caso a consulta retorne menos colunas em versões antigas
                status_db = r[0]
                fechado_por = r[1] if len(r) > 1 else None
                data_fechamento = r[2] if len(r) > 2 else None
                alterado_por = r[3] if len(r) > 3 else None
                data_alteracao = r[4] if len(r) > 4 else None
                detalhes = []
                if fechado_por:
                    detalhes.append(f"fechada por: {fechado_por} em {data_fechamento or '-'}")
                if alterado_por:
                    detalhes.append(f"alterada por: {alterado_por} em {data_alteracao or '-'}")
                detalhes_txt = ' | '.join(detalhes) if detalhes else '-'
                status_msg_var.set(f"Folha {mes} atualmente: {status_db} ({detalhes_txt})")
            else:
                status_msg_var.set(f"Folha {mes} não encontrada. Será criada ao fechar.")
        except sqlite3.Error as e:
            status_msg_var.set(f"Erro ao consultar o banco: {e}")
        finally:
            if conn:
                conn.close()

    def set_folha_status(novo_status):
        mes = entry_data_referencia.get().strip()
        if not re.match(r"^(0[1-9]|1[0-2])/[0-9]{4}$", mes):
            messagebox.showerror("Erro", "Formato do mês inválido. Use MM/AAAA.", parent=janelafolha)
            return
        confirm_text = "" if novo_status == 'FECHADA' else "" 
        acao = 'fechar' if novo_status == 'FECHADA' else 'reabrir'
        if not messagebox.askyesno("Confirmar", f"Deseja {acao} a folha de referência {mes}?", parent=janelafolha):
            return
        try:
            conn = sqlite3.connect(resource_path('banco.db'))
            cursor = conn.cursor()
            # Insere ou atualiza o registro
            agora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if novo_status == 'FECHADA':
                cursor.execute(
                    "INSERT OR REPLACE INTO folhas (mes_referencia, status, fechado_por, data_fechamento, alterado_por, data_alteracao) VALUES (?, ?, ?, ?, ?, ?)",
                    (mes, 'FECHADA', str(usuario_logado), agora, str(usuario_logado), agora)
                )
            else:
                # Reabrir: marca como ABERTA, limpa campos de fechamento e registra alteração
                cursor.execute(
                    "INSERT OR REPLACE INTO folhas (mes_referencia, status, fechado_por, data_fechamento, alterado_por, data_alteracao) VALUES (?, ?, NULL, NULL, ?, ?)",
                    (mes, 'ABERTA', str(usuario_logado), agora)
                )
            conn.commit()
            messagebox.showinfo("Sucesso", f"Folha {mes} marcada como {novo_status} com sucesso.", parent=janelafolha)
            atualizar_status_msg()
            # Se a folha foi reaberta, oferecer abrir a janela de geração de pagamentos já pré-preenchida
            if novo_status == 'ABERTA':
                try:
                    # Verifica novamente no banco se o status realmente está como 'ABERTA'
                    cursor.execute(
                        "SELECT status FROM folhas WHERE TRIM(mes_referencia) = ? "
                        "ORDER BY COALESCE(data_alteracao, data_fechamento) DESC, id DESC LIMIT 1",
                        (mes,)
                    )
                    rr = cursor.fetchone()
                    status_verify = rr[0] if rr else None
                    # Se por algum motivo o registro ainda indicar FECHADA, avisa o usuário
                    if status_verify is None:
                        messagebox.showwarning("Aviso", f"Aviso: não foi encontrado registro de folha para {mes} após reabrir.", parent=janelafolha)
                    elif str(status_verify).upper() == 'FECHADA':
                        messagebox.showwarning("Aviso", f"A folha {mes} ainda consta como FECHADA no banco. Verifique a operação.", parent=janelafolha)
                except Exception:
                    # Não bloquear a operação principal se algo falhar aqui
                    pass
        except sqlite3.Error as e:
            messagebox.showerror("Erro de Banco", f"Erro ao atualizar o status da folha: {e}", parent=janelafolha)
        finally:
            if conn:
                conn.close()

    # Garantir que a tabela exista
    ensure_folhas_table()

    # Botões
    botoes_frame = ctk.CTkFrame(frame, fg_color="transparent")
    botoes_frame.pack(pady=(10, 4))

    btn_fechar = ctk.CTkButton(botoes_frame, text="Fechar Folha", width=120, fg_color="#a1970c", hover_color="#d37b08", text_color="#fff", command=lambda: set_folha_status('FECHADA'))
    btn_fechar.grid(row=0, column=0, padx=8)

    btn_reabrir = ctk.CTkButton(botoes_frame, text="Reabrir Folha", width=120, fg_color="#6c757d", hover_color="#5a6268", text_color="#fff", command=lambda: set_folha_status('ABERTA'))
    btn_reabrir.grid(row=0, column=1, padx=8)

    # Atualiza o status quando o usuário terminar de digitar
    entry_data_referencia.bind("<FocusOut>", lambda e: atualizar_status_msg())
    entry_data_referencia.bind("<KeyRelease>", lambda e: atualizar_status_msg())

    

#==============================================================================================#

def janela_gerar_txt_fita_credito():
    def gerar_txt():
        mes_ref = entry_data_referencia.get().strip()
        if not re.match(r"^(0[1-9]|1[0-2])/[0-9]{4}$", mes_ref):
            messagebox.showerror("Erro", "Formato do mês inválido. Use MM/AAAA.", parent=janelaFita)
            return
        pasta_saida = filedialog.askdirectory(
            title="Selecione a pasta para salvar a fita de crédito",
            parent=janelaFita
        )
        if not pasta_saida:
            return
        try:
            from gerar_fita_credito import gerar_fita_credito_txt
            gerar_fita_credito_txt(mes_ref, pasta_saida)
            nome_arquivo = f"Fita_Credito_{mes_ref.replace('/', '')}.txt"
            caminho_completo = os.path.join(pasta_saida, nome_arquivo)
            messagebox.showinfo("Sucesso", f"Fita de crédito gerada:\n{caminho_completo}", parent=janelaFita)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao gerar TXT:\n{e}", parent=janelaFita)
        janelaFita.destroy()

    janelaFita = ctk.CTkToplevel()
    janelaFita.title("Gerar Fita de Crédito")
    janelaFita.geometry("400x400")
    janelaFita.grab_set()

    frame = ctk.CTkFrame(janelaFita, fg_color="transparent")
    frame.pack(expand=True, padx=20, pady=20)

    ctk.CTkLabel(frame, text="Indique o Mês de Referência", font=('Calibri', 14, 'bold')).pack(pady=(0, 10))
    ctk.CTkLabel(frame, text="Esta ferramenta gera o arquivo TXT da fita de crédito\ncom base nos pagamentos já existentes no banco.", justify="center").pack(pady=(0, 20))
    ctk.CTkLabel(frame, text="Mês de Referência (MM/AAAA):").pack(pady=5)

    entry_data_referencia = ctk.CTkEntry(frame, width=150, justify="center")
    entry_data_referencia.pack(pady=2)

    ctk.CTkButton(frame, text="Gerar Fita de Crédito", command=gerar_txt, fg_color="#a1970c", hover_color="#d37b08", text_color="#fff").pack(pady=(20, 5))
    ctk.CTkButton(frame, text="Cancelar", command=janelaFita.destroy, fg_color="#6c757d", hover_color="#5a6268", text_color="#fff").pack()

    def mascara_data_referencia(event):
        widget = event.widget
        digits = "".join(filter(str.isdigit, widget.get()))[:6]
        if len(digits) > 2:
            formatted_text = f"{digits[:2]}/{digits[2:]}"
        else:
            formatted_text = digits
        widget.delete(0, tk.END)
        widget.insert(0, formatted_text)
        widget.icursor(tk.END)

    entry_data_referencia.bind("<KeyRelease>", mascara_data_referencia)

#==============================================================================================#



def login():
    def verificar_credenciais():
        global usuario_logado, id_usuario_logado, perfil_usuario_logado
        usuario = entry_usuario.get()
        senha = entry_senha.get()
        id_usuario, perfil_usuario = verificar_credenciais_no_banco(usuario, senha)
        if id_usuario is not None:
            usuario_logado = usuario
            id_usuario_logado = id_usuario
            perfil_usuario_logado = perfil_usuario
            messagebox.showinfo("Sucesso", f"Login realizado com sucesso!\nPerfil: {perfil_usuario_logado}")
            janela_login.destroy()
            exibir_janela_principal()
        else:
            messagebox.showerror("Erro", "Usuário ou senha incorretos!")
            
    def pressionar_enter(event):
        verificar_credenciais()
        
    def fechar_app_login():
        janela_login.destroy()
        sys.exit()
        
    janela_login = ctk.CTk()
    janela_login.title("Login")
    janela_login.geometry("380x340")
    janela_login.resizable(False, False)
    # Paleta personalizada de azul e cinza
    ctk.set_default_color_theme("blue")  # Mantém o tema azul base

    # Frame centralizado para o formulário
    frame_login = ctk.CTkFrame(janela_login, fg_color="#f0f4f8")  # Cinza claro
    frame_login.pack(expand=True, fill="both")

    # Título
    lb_titulo = ctk.CTkLabel(
        frame_login, 
        text="Bem-vindo ao Sistema",
        font=('Calibri', 22, 'bold'),
        text_color="#d37b08"  # Azul escuro
    )
    lb_titulo.pack(pady=(30, 30))

    # Subtítulo
    lb_sub = ctk.CTkLabel(frame_login, text="Informe suas credenciais", font=('Calibri', 14, 'italic'), text_color="#000000")
    lb_sub.pack(pady=(0, 15))

    # icon_usuario = PhotoImage(file="icons_usuario.png")  # Certifique-se de que o caminho está correto
    # icon_usuario = icon_usuario.subsample(2, 2)  # Reduz o tamanho da imagem
    
    # Usuário
    ctk.CTkLabel(frame_login, text="Usuário:", font=('Calibri', 14), text_color="#000000").pack(pady=(0, 3))
    entry_usuario = ctk.CTkEntry(frame_login, width=220, fg_color="#e3eafc", text_color="#222222", border_color="#a1970c")
    entry_usuario.pack(pady=(0, 10))

    # Senha
    ctk.CTkLabel(frame_login, text="Senha:", font=('Calibri', 14), text_color="#000000").pack(pady=(0, 3))
    entry_senha = ctk.CTkEntry(frame_login, show="*", width=220, fg_color="#e3eafc", text_color="#222222", border_color="#a1970c")
    entry_senha.pack(pady=(0, 15))

    
    # Botão Login
    ctk.CTkButton(
        frame_login, 
        text="Entrar", 
        command=verificar_credenciais, 
        width=120, 
        fg_color="#a1970c", 
        hover_color="#d37b08", 
        text_color="#fff", corner_radius=18
    ).pack(pady=(0, 10))

    # Rodapé
    lb_rodape = ctk.CTkLabel(frame_login, text="© 2025 julio.slima - SEEC", font=('Calibri', 10, 'italic'), text_color="#c0a50a")
    lb_rodape.pack(side="bottom", pady=(10, 0))

    janela_login.bind("<Return>", pressionar_enter)
    janela_login.protocol("WM_DELETE_WINDOW", fechar_app_login)
    janela_login.mainloop()

def mascara_data_referencia(event):
    """Função de máscara genérica para ser usada por múltiplas janelas."""
    widget = event.widget
    
    # Pega o texto atual e remove tudo que não for dígito
    digits = "".join(filter(str.isdigit, widget.get()))[:6]
    
    # Formata o texto como MM/AAAA
    if len(digits) > 2:
        formatted_text = f"{digits[:2]}/{digits[2:]}"
    else:
        formatted_text = digits
        
    # Atualiza o campo e move o cursor para o final
    widget.delete(0, tk.END)
    widget.insert(0, formatted_text)
    widget.icursor(tk.END)

def mascara_cpf(event):
    """Aplica máscara de CPF (###.###.###-##) a um widget de entrada."""
    widget = event.widget
    text = "".join(filter(str.isdigit, widget.get()))[:11]
    
    if len(text) > 9:
        formatted_text = f"{text[:3]}.{text[3:6]}.{text[6:9]}-{text[9:]}"
    elif len(text) > 6:
        formatted_text = f"{text[:3]}.{text[3:6]}.{text[6:]}"
    elif len(text) > 3:
        formatted_text = f"{text[:3]}.{text[3:]}"
    else:
        formatted_text = text
        
    widget.delete(0, tk.END)
    widget.insert(0, formatted_text)
    widget.icursor(tk.END)

def mascara_cep(event):
    """Aplica máscara de CEP (#####-###) a um widget de entrada."""
    widget = event.widget
    text = "".join(filter(str.isdigit, widget.get()))[:8]
    
    if len(text) > 5:
        formatted_text = f"{text[:5]}-{text[5:]}"
    else:
        formatted_text = text
        
    widget.delete(0, tk.END)
    widget.insert(0, formatted_text)
    widget.icursor(tk.END)

def mascara_telefone(event):
    """Aplica máscara de telefone ((##) #####-####) a um widget de entrada."""
    widget = event.widget
    text = "".join(filter(str.isdigit, widget.get()))[:11]
    
    if len(text) > 7:
        formatted_text = f"({text[:2]}) {text[2:7]}-{text[7:]}"
    elif len(text) > 2:
        formatted_text = f"({text[:2]}) {text[2:]}"
    elif len(text) > 0:
        formatted_text = f"({text[:2]}"
    else:
        formatted_text = ""
        
    widget.delete(0, tk.END)
    widget.insert(0, formatted_text)
    widget.icursor(tk.END)

def mascara_data_dma(event):
    """Aplica máscara de data (DD/MM/AAAA) a um widget de entrada."""
    widget = event.widget
    text = "".join(filter(str.isdigit, widget.get()))[:8]
    
    if len(text) > 4:
        formatted_text = f"{text[:2]}/{text[2:4]}/{text[4:]}"
    elif len(text) > 2:
        formatted_text = f"{text[:2]}/{text[2:]}"
    else:
        formatted_text = text
        
    widget.delete(0, tk.END)
    widget.insert(0, formatted_text)
    widget.icursor(tk.END)

def mascara_numero_banco(event):
    """Limita a entrada do número do banco a 3 dígitos."""
    widget = event.widget
    text = "".join(filter(str.isdigit, widget.get()))[:3]
    widget.delete(0, tk.END)
    widget.insert(0, text)
    widget.icursor(tk.END)

def executar_migracao_db():
    """
    Verifica e aplica de forma segura as migrações necessárias no esquema do banco de dados
    usando ALTER TABLE para adicionar colunas faltantes.
    """
    print("Verificando a estrutura do banco de dados...")
    try:
        with sqlite3.connect(resource_path('banco.db'), timeout=10) as conn:
            cursor = conn.cursor()
            
            # --- Tabela 'indice' ---
            cursor.execute("PRAGMA table_info(indice)")
            colunas_indice = {col[1] for col in cursor.fetchall()}
            if 'usuario_id' not in colunas_indice:
                print("MIGRANDO: Adicionando coluna 'usuario_id' à tabela 'indice'...")
                cursor.execute("ALTER TABLE indice ADD COLUMN usuario_id INTEGER REFERENCES users(id_usuario)")
                print("MIGRAÇÃO CONCLUÍDA.")
            if 'status' not in colunas_indice:
                print("MIGRANDO: Adicionando coluna 'status' à tabela 'indice'...")
                # Adiciona a coluna e define 'ATIVO' como padrão para todos os registros existentes
                cursor.execute("ALTER TABLE indice ADD COLUMN status TEXT DEFAULT 'ATIVO'")
                print("MIGRAÇÃO CONCLUÍDA.")


            # --- Tabela 'pagamentos' (parâmetros) ---
            cursor.execute("PRAGMA table_info(pagamentos)")
            colunas_pagamentos = {col[1] for col in cursor.fetchall()}
            if 'data_atualizacao' not in colunas_pagamentos:
                print("MIGRANDO: Adicionando coluna 'data_atualizacao' à tabela 'pagamentos'...")
                cursor.execute("ALTER TABLE pagamentos ADD COLUMN data_atualizacao DATETIME")
                print("MIGRAÇÃO CONCLUÍDA.")
            if 'usuario_id' not in colunas_pagamentos:
                print("MIGRANDO: Adicionando coluna 'usuario_id' à tabela 'pagamentos'...")
                cursor.execute("ALTER TABLE pagamentos ADD COLUMN usuario_id INTEGER REFERENCES users(id_usuario)")
                print("MIGRAÇÃO CONCLUÍDA.")
            if 'status' not in colunas_pagamentos:
                print("MIGRANDO: Adicionando coluna 'status' à tabela 'pagamentos'...")
                # Adiciona a coluna e define 'ATIVO' como padrão para todos os registros existentes
                cursor.execute("ALTER TABLE pagamentos ADD COLUMN status TEXT DEFAULT 'ATIVO'")
                print("MIGRAÇÃO CONCLUÍDA.")

            # --- Tabela 'pagamento_gerados' ---
            cursor.execute("PRAGMA table_info(pagamento_gerados)")
            colunas_pag_gerados = {col[1] for col in cursor.fetchall()}
            if 'observacoes' not in colunas_pag_gerados:
                print("MIGRANDO: Adicionando coluna 'observacoes' à tabela 'pagamento_gerados'...")
                cursor.execute("ALTER TABLE pagamento_gerados ADD COLUMN observacoes TEXT")
                print("MIGRAÇÃO CONCLUÍDA.")
            
            # --- Tabela 'beneficiarios' ---
            cursor.execute("PRAGMA table_info(beneficiarios)")
            colunas_beneficiarios = {col[1] for col in cursor.fetchall()}
            if 'identidade' not in colunas_beneficiarios:
                print("MIGRANDO: Adicionando coluna 'identidade' à tabela 'beneficiarios'...")
                cursor.execute("ALTER TABLE beneficiarios ADD COLUMN identidade TEXT")
                print("MIGRAÇÃO CONCLUÍDA.")
            if 'orgao_emissor' not in colunas_beneficiarios:
                print("MIGRANDO: Adicionando coluna 'orgao_emissor' à tabela 'beneficiarios'...")
                cursor.execute("ALTER TABLE beneficiarios ADD COLUMN orgao_emissor TEXT")
                print("MIGRAÇÃO CONCLUÍDA.")

            # --- Tabela 'representantes_legais' ---
            cursor.execute("PRAGMA table_info(representantes_legais)")
            colunas_rep_legais = {col[1] for col in cursor.fetchall()}
            if 'email' not in colunas_rep_legais:
                print("MIGRANDO: Adicionando coluna 'email' à tabela 'representantes_legais'...")
                cursor.execute("ALTER TABLE representantes_legais ADD COLUMN email TEXT")
                print("MIGRAÇÃO CONCLUÍDA.")
            if 'digitoconta' not in colunas_rep_legais:
                print("MIGRANDO: Adicionando coluna 'digitoconta' à tabela 'representantes_legais'...")
                cursor.execute("ALTER TABLE representantes_legais ADD COLUMN digitoconta TEXT")
                print("MIGRAÇÃO CONCLUÍDA.")
            
            conn.commit()
            print("Verificação do banco de dados concluída.")

    except sqlite3.Error as e:
        print(f"Ocorreu um erro durante a migração do banco de dados: {e}")
        messagebox.showerror("Erro de Migração", f"Não foi possível atualizar a estrutura do banco de dados.\n\nErro: {e}\n\nO programa será encerrado.")
        sys.exit()

executar_migracao_db()
login()
 