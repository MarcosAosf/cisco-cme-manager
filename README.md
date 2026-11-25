# Cisco CME Manager (Telefonia IP & Ramais) 📞

[![Platform: Windows](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-blue.svg?logo=windows)](https://microsoft.com/windows)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg?logo=python)](https://python.org)
[![UI: CustomTkinter](https://img.shields.io/badge/UI-CustomTkinter%20Modern%20Dark-A855F7.svg)](https://github.com/TomSchimansky/CustomTkinter)
[![License: MIT](https://img.shields.io/badge/License-MIT-orange.svg)](LICENSE)

Uma aplicação desktop nativa para **Windows (10 / 11)** com interface gráfica moderna desenvolvida em **CustomTkinter** e engine de automação de rede com **Netmiko (SSH)**, projetada para administração ágil, inventário dinâmico e resolução de problemas em roteadores de voz **Cisco Communications Manager Express (CME)** suportando telefones **SIP** e **SCCP (Skinny)**.

---

## 🪟 Desenvolvido para Windows

O projeto foi construído e homologado nativamente no **Windows**, contando com:
- **Interface Gráfica Windows Dark Mode:** Janelas fluidas, controles modernos e adaptação DPI nativa do Windows via `CustomTkinter`.
- **Launcher de Execução Direta (`run.bat`):** Permite iniciar a aplicação com um simples **duplo clique**, sem necessidade de abrir o terminal manualmente.
- **Diagnóstico com Ping Nativo do Windows:** Envio de pacotes ICMP adaptados aos parâmetros do comando `ping` do Windows (`-n 1 -w 1000`).

---

## 🚀 Funcionalidades Principais

- **Conexão SSH Segura:** Autenticação via SSH com suporte completo a algoritmos legados e modernos do Cisco IOS (`cisco_ios`).
- **Dashboard de Ramais & Telefones:**
  - Descoberta e parsing dinâmico de `voice register dn` (SIP) e `ephone-dn` (SCCP).
  - Status em tempo real de registro dos aparelhos (`REGISTERED` / `UNREGISTERED`).
  - Mapeamento de IP do telefone, porta de escuta, modelo de hardware e MAC address.
- **Filtros e Busca Instantânea:**
  - Busca rápida por número de ramal, nome de colaborador ou endereço IP.
  - Filtro por status de conectividade (Todos, Registrados ou Não Registrados).
- **Ações Rápidas de Operação:**
  - **Reiniciar Aparelho (Reset/Restart):** Disparo de comando `reset` (SIP pool) ou `restart` (SCCP ephone) para forçar re-registro sem interrupção global.
  - **Editar Nome / Caller-ID:** Alteração da identificação de chamada do ramal diretamente no roteador de voz.
  - **Testes de Conectividade:** Ping direto para o IP do aparelho VoIP para diagnóstico imediato de camada 3.
  - **Terminal / Logs ao Vivo:** Visualização de comandos enviados e respostas em tempo real.

---

## ⚡ Instalação e Execução no Windows (Rápido)

### 1. Pré-requisitos
- Ter o **Python 3.8+** instalado no Windows (baixe em [python.org](https://www.python.org/downloads/)).
  > ⚠️ Durante a instalação do Python, marque obrigatoriamente a opção **"Add Python to PATH"**.

### 2. Clonar ou Baixar o Projeto
```cmd
git clone https://github.com/MarcosAosf/cisco-cme-manager.git
cd cisco-cme-manager
```

### 3. Instalar as Dependências
Abra o Prompt de Comando (CMD) ou PowerShell na pasta do projeto e execute:
```cmd
pip install -r requirements.txt
```

### 4. Executar
Você pode rodar de duas formas no Windows:
- **Opção A (Mais fácil):** Dê um **duplo clique** no arquivo **`run.bat`**.
- **Opção B (Via CMD / PowerShell):**
  ```cmd
  py main.py
  :: ou
  python main.py
  ```

---

## 💻 Como Usar

1. Na barra superior de conexão, informe o **IP do Roteador Cisco CME** (ex.: `192.0.2.1`), a **Porta SSH** (padrão: `22`), o **Usuário** e a **Senha**.
2. Clique no botão **Conectar**.
3. O sistema fará a leitura automática dos telefones registrados e listará todos os ramais na tabela central.
4. Utilize a barra de pesquisa para filtrar ramais ou clique com o botão direito / nos botões de ação para reiniciar aparelhos ou editar descrições.

---

## 🔒 Segurança & Boas Práticas

- **Zero Armazenamento de Senhas:** Esta aplicação segue a política de segurança de memória volátil — senhas não são salvas em arquivos locais ou em disco.
- **Ambientes de Produção:** Nunca compartilhe credenciais, `enable secrets` ou IPs reais de infraestrutura corporativa em commits públicos.

---

## 📂 Estrutura do Projeto

```text
cisco-cme-manager/
├── run.bat             # Launcher rápido para Windows (duplo clique)
├── cme_ssh.py          # Camada de comunicação SSH com Netmiko (Cisco IOS)
├── templates.py        # Templates certificados de comandos Cisco CME
├── main.py             # Interface gráfica moderna em CustomTkinter
├── requirements.txt    # Dependências do projeto
├── .gitignore          # Proteção contra versionamento de credenciais e logs
└── README.md           # Documentação técnica da ferramenta
```

---

## 📄 Licença

Distribuído sob a licença **MIT**. Veja o arquivo `LICENSE` para mais detalhes.
