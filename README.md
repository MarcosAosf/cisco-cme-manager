# Cisco CME Manager (Telefonia IP & Ramais) 📞

Uma aplicação desktop moderna com interface gráfica desenvolvida em **CustomTkinter** e engine de automação de rede com **Netmiko (SSH)**, projetada para administração ágil, inventário dinâmico e resolução de problemas em roteadores de voz **Cisco Communications Manager Express (CME)** suportando telefones **SIP** e **SCCP (Skinny)**.

---

## 🚀 Funcionalidades Principais

- **Conexão SSH Segura:** Autenticação via SSH com compatibilidade para cifras e algoritmos legados e modernos do Cisco IOS (`cisco_ios`).
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

## 📋 Pré-requisitos & Instalação

### Requisitos:
- **Python 3.8+** instalado.
- Conectividade de rede (IP/SSH) até o roteador Cisco de voz.

### Instalação:
1. Clone o repositório:
```bash
git clone https://github.com/MarcosAosf/cisco-cme-manager.git
cd cisco-cme-manager
```

2. Crie e ative um ambiente virtual (recomendado):
```bash
python -m venv venv
# No Windows:
venv\Scripts\activate
# No Linux/macOS:
source venv/bin/activate
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

---

## ⚡ Como Executar

Execute o arquivo principal:
```bash
python main.py
```

1. Informe o **IP do Roteador Cisco CME**, a porta SSH (padrão: `22`), o **usuário** e a **senha**.
2. Clique em **Conectar**.
3. O sistema fará a varredura automática dos ramais e exibirá a tabela interativa.

---

## 🔒 Segurança & Boas Práticas

- **Zero Armazenamento de Senhas:** Esta aplicação segue a política de segurança de memória volátil — senhas não são salvas em arquivos locais ou em disco.
- **Ambientes de Produção:** Nunca compartilhe credenciais, `enable secrets` ou IPs reais de infraestrutura corporativa em commits públicos. Use variáveis de ambiente ou insira credenciais apenas durante a execução interativa.

---

## 📂 Estrutura do Projeto

```text
cisco-cme-manager/
├── cme_ssh.py          # Camada de comunicação SSH com Netmiko (Cisco IOS)
├── templates.py        # Templates certificados de comandos Cisco CME
├── main.py             # Interface gráfica moderna (CustomTkinter)
├── requirements.txt    # Dependências do projeto
├── .gitignore          # Proteção contra versionamento de credenciais e logs
└── README.md           # Documentação técnica da ferramenta
```

---

## 📄 Licença

Distribuído sob a licença **MIT**. Veja o arquivo `LICENSE` para mais detalhes.
