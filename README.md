💰 Sistema de Gestão de Pensão Indenizatória

Aplicação desktop em Python + CustomTkinter desenvolvida para automatizar todo o processo de gestão de pensões indenizatórias — desde o cadastro de beneficiários e representantes até a geração de pagamentos, fitas bancárias, relatórios e documentos oficiais em PDF.

🚀 Funcionalidades Principais

Cadastro completo de beneficiários
Com dados pessoais, bancários, processos judiciais e observações.

Gestão de representantes legais
Suporte a menores ou incapazes com vínculo automático entre beneficiário e representante.

Geração automática de pagamentos
Baseado em parâmetros e índices configurados, com cálculo de 13º e 1/3 de férias.

Geração de documentos oficiais

Documento de empenho em PDF (via ReportLab)

Fita de crédito (layout bancário em .txt)

Relatórios analíticos em Excel

Comprovantes de rendimento

Controle de usuários e permissões

Perfis de Administrador e Usuário padrão

Senhas com hash seguro usando bcrypt

Ativação/desativação de contas

Banco de dados SQLite integrado

Scripts para importar, limpar ou restaurar tabelas

Backup automático antes de exclusões em massa

Interface moderna com CustomTkinter

Design responsivo e estilizado

Menus intuitivos e navegação fluida

Geração de arquivos e relatórios direto pela interface

🗂️ Estrutura do Projeto

📦 pensao-indenizatoria-manager/
├── banco.db                         # Banco de dados SQLite
├── sistema.py                        # Interface principal (CustomTkinter)
├── gerar_pagamento.py                # Lógica de geração de pagamentos
├── gerar_documentos.py               # Criação de PDFs (Documentos oficiais)
├── gerar_fita_credito.py             # Geração de TXT bancário (fita crédito)
├── relatório_fita_crédito.py         # Parser e relatório de fitas
├── importar_dado.py                  # Importação em massa de dados
├── limpar_tabelas_especificas.py     # Limpeza segura de tabelas
├── Inserir_indice.py                 # (obsoleto) Inserção manual de índices
├── exportar_excel.py                 # Exportações em formato XLSX
└── README.md

⚙️ Tecnologias Utilizadas

Python 3.10+

CustomTkinter

SQLite3

Pandas

ReportLab

bcrypt

tkcalendar

Unidecode

🖥️ Como Executar

1. Clone o repositório

git clone https://github.com/juliocesardsl/pensao-indenizatoria-manager.git
cd pensao-indenizatoria-manager

2. Crie um ambiente virtual (opcional, mas recomendado)

python -m venv venv
source venv/bin/activate     # Linux/Mac
venv\Scripts\activate        # Windows

3. Instale as dependências

pip install -r requirements.txt

4. Execute o sistema

python sistema.py

🔐 Login e Permissões

O sistema suporta diferentes perfis de usuário:

Administrador: acesso total (cadastro de usuários, exclusões e relatórios)

Usuário padrão: acesso restrito às funções de rotina

As senhas são armazenadas com hash bcrypt para segurança.

🧩 Geração de Arquivos

Tipo	                      Formato	      Módulo responsável
Documento de Empenho	      .pdf	        gerar_documentos.py
Fita de Crédito Bancária	  .txt	        gerar_fita_credito.py
Relatório Analítico	        .xlsx       	relatório_fita_crédito.py
Backup Automático	          .db.backup	  limpar_tabelas_especificas.py

🧠 Autor

Desenvolvido por Júlio Lima (julio.slima)
💼 Secretaria de Estado de Economia — SEEC
📧 contato: [julio.slima.dev@gmail.com]

🏗️ Ideias Futuras

Implementar dashboard de indicadores (Qt ou Tkinter Canvas)

Adicionar logs de auditoria por usuário

Suporte a múltiplas unidades gestoras

Gerador automático de comprovante de rendimentos por CPF

🧾 "Automatizar processos é libertar o tempo para pensar."
— Júlio Lima
