"""
Aplicação Principal — GERENCIADOR CISCO CME (Communications Manager Express)
Interface gráfica moderna em CustomTkinter para administração, auditoria e controle em tempo real
de ramais VoIP e aparelhos SIP / SCCP em roteadores Cisco IOS.
"""

import os
import re
import sys
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import customtkinter as ctk
from tkinter import messagebox

# Importações dos módulos locais da pasta CME
from cme_ssh import CiscoCMEClient
from templates import CiscoCMETemplates

# Configuração visual do CustomTkinter
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Constantes de Cores (Paleta Dark Corporativa)
COR_BG_ESCURO = "#0d1117"
COR_FRAME = "#161b22"
COR_FRAME_BORDA = "#30363d"
COR_DESTAQUE = "#58a6ff"
COR_CINZA = "#8b949e"
COR_VERDE = "#2ea043"
COR_VERMELHO = "#da3633"
COR_AMARELO = "#d29922"
COR_BOTAO_PRIMARIO = "#1f6feb"
COR_BOTAO_HOVER = "#388bfd"

FONTE_TITULO = ("Segoe UI", 15, "bold")
FONTE_LABEL = ("Segoe UI", 11)
FONTE_LABEL_BOLD = ("Segoe UI", 11, "bold")
FONTE_MONO = ("Consolas", 10)


class AppCME(ctk.CTk):
    """Janela principal do Gerenciador Cisco CME."""

    def __init__(self) -> None:
        super().__init__()

        self.title("📞 GERENCIADOR CISCO CME — Telefonia IP & Ramais")
        self.geometry("1300x780")
        self.minsize(1050, 620)
        self.configure(fg_color=COR_BG_ESCURO)

        # Cliente SSH ativo e Cache de Estado
        self.cme_client: Optional[CiscoCMEClient] = None
        self.dados_atuais: List[Dict[str, Any]] = []
        self._cme_ramais: List[Dict[str, Any]] = []
        self._linhas_widgets: List[tuple] = []
        self._debounce_filtro_id: Optional[str] = None

        # Variáveis de Conexão
        self._var_ip = ctk.StringVar()
        self._var_port = ctk.StringVar(value="22")
        self._var_user = ctk.StringVar(value="admin")
        self._var_pass = ctk.StringVar()
        self._var_secret = ctk.StringVar()

        # Variáveis de Filtro
        self._var_busca = ctk.StringVar()
        self._var_filtro_status = ctk.StringVar(value="Todos")

        # Elementos dinâmicos da interface
        self.entry_busca: Optional[ctk.CTkEntry] = None
        self.btn_pesquisar: Optional[ctk.CTkButton] = None
        self.btn_conectar: Optional[ctk.CTkButton] = None
        self.lbl_status_conexao: Optional[ctk.CTkLabel] = None
        self.entry_pass: Optional[ctk.CTkEntry] = None
        self.entry_secret: Optional[ctk.CTkEntry] = None

        # KPI Badges
        self._lbl_kpi_total: Optional[ctk.CTkLabel] = None
        self._lbl_kpi_registrados: Optional[ctk.CTkLabel] = None
        self._lbl_kpi_offline: Optional[ctk.CTkLabel] = None
        self._lbl_kpi_sem_dn: Optional[ctk.CTkLabel] = None

        # Tabela e Logs
        self._frame_tabela: Optional[ctk.CTkScrollableFrame] = None
        self._lbl_total_filtrados: Optional[ctk.CTkLabel] = None
        self._txt_log: Optional[ctk.CTkTextbox] = None

        self._construir_interface()

    # ------------------------------------------------------------------
    # Construção da Interface Gráfica
    # ------------------------------------------------------------------

    def _construir_interface(self) -> None:
        """Monta o cabeçalho, barra de conexão, KPIs, tabela e rodapé de logs."""

        # 1. Cabeçalho Superior
        frame_header = ctk.CTkFrame(self, fg_color=COR_FRAME, corner_radius=0, height=54)
        frame_header.pack(fill="x", padx=0, pady=0)
        frame_header.pack_propagate(False)

        ctk.CTkLabel(
            frame_header,
            text="📞  GERENCIADOR CISCO CME",
            font=FONTE_TITULO,
            text_color=COR_DESTAQUE,
        ).pack(side="left", padx=20, pady=10)

        ctk.CTkLabel(
            frame_header,
            text="Communications Manager Express • Voice over IP Day-1",
            font=FONTE_LABEL,
            text_color=COR_CINZA,
        ).pack(side="left", padx=0, pady=10)

        self.lbl_status_conexao = ctk.CTkLabel(
            frame_header,
            text="● Desconectado",
            font=FONTE_LABEL_BOLD,
            text_color=COR_CINZA,
        )
        self.lbl_status_conexao.pack(side="right", padx=20, pady=10)

        # 2. Painel de Conexão com o Roteador
        frame_conn = ctk.CTkFrame(self, fg_color=COR_FRAME, corner_radius=8, border_width=1, border_color=COR_FRAME_BORDA)
        frame_conn.pack(fill="x", padx=16, pady=(12, 8))

        linha_conn = ctk.CTkFrame(frame_conn, fg_color="transparent")
        linha_conn.pack(fill="x", padx=14, pady=10)

        ctk.CTkLabel(linha_conn, text="IP do Roteador:", font=FONTE_LABEL_BOLD, text_color="#ffffff").pack(side="left", padx=(0, 4))
        entry_ip = ctk.CTkEntry(
            linha_conn,
            textvariable=self._var_ip,
            placeholder_text="ex: 192.0.2.1",
            width=135,
            height=30,
            font=FONTE_LABEL,
            fg_color=COR_BG_ESCURO,
            border_color=COR_FRAME_BORDA,
        )
        entry_ip.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(linha_conn, text="Porta:", font=FONTE_LABEL_BOLD, text_color=COR_CINZA).pack(side="left", padx=(0, 4))
        ctk.CTkEntry(
            linha_conn,
            textvariable=self._var_port,
            width=55,
            height=30,
            font=FONTE_LABEL,
            fg_color=COR_BG_ESCURO,
            border_color=COR_FRAME_BORDA,
        ).pack(side="left", padx=(0, 10))

        ctk.CTkLabel(linha_conn, text="Usuário:", font=FONTE_LABEL_BOLD, text_color=COR_CINZA).pack(side="left", padx=(0, 4))
        ctk.CTkEntry(
            linha_conn,
            textvariable=self._var_user,
            width=110,
            height=30,
            font=FONTE_LABEL,
            fg_color=COR_BG_ESCURO,
            border_color=COR_FRAME_BORDA,
        ).pack(side="left", padx=(0, 10))

        ctk.CTkLabel(linha_conn, text="Senha:", font=FONTE_LABEL_BOLD, text_color=COR_CINZA).pack(side="left", padx=(0, 4))
        self.entry_pass = ctk.CTkEntry(
            linha_conn,
            textvariable=self._var_pass,
            placeholder_text="••••••",
            show="*",
            width=110,
            height=30,
            font=FONTE_LABEL,
            fg_color=COR_BG_ESCURO,
            border_color=COR_FRAME_BORDA,
        )
        self.entry_pass.pack(side="left", padx=(0, 10))
        self.entry_pass.bind("<Return>", lambda e: self._conectar_e_ler())

        ctk.CTkLabel(linha_conn, text="Secret (Enable):", font=FONTE_LABEL_BOLD, text_color=COR_CINZA).pack(side="left", padx=(0, 4))
        self.entry_secret = ctk.CTkEntry(
            linha_conn,
            textvariable=self._var_secret,
            placeholder_text="Opcional",
            show="*",
            width=100,
            height=30,
            font=FONTE_LABEL,
            fg_color=COR_BG_ESCURO,
            border_color=COR_FRAME_BORDA,
        )
        self.entry_secret.pack(side="left", padx=(0, 12))

        self.btn_conectar = ctk.CTkButton(
            linha_conn,
            text="🔌  Conectar e Sincronizar",
            command=self._conectar_e_ler,
            fg_color=COR_BOTAO_PRIMARIO,
            hover_color=COR_BOTAO_HOVER,
            font=FONTE_LABEL_BOLD,
            width=180,
            height=32,
        )
        self.btn_conectar.pack(side="left", padx=(0, 6))

        # 3. Cartões de Métricas (KPI Badges)
        frame_kpis = ctk.CTkFrame(self, fg_color="transparent")
        frame_kpis.pack(fill="x", padx=16, pady=(0, 8))

        self._lbl_kpi_total = self._criar_card_kpi(frame_kpis, "TOTAL RAMAIS", "0", COR_DESTAQUE)
        self._lbl_kpi_registrados = self._criar_card_kpi(frame_kpis, "REGISTRADOS", "0", COR_VERDE)
        self._lbl_kpi_offline = self._criar_card_kpi(frame_kpis, "OFFLINE", "0", COR_VERMELHO)
        self._lbl_kpi_sem_dn = self._criar_card_kpi(frame_kpis, "SEM DN", "0", COR_AMARELO)

        # 4. Barra de Pesquisa e Filtros
        frame_busca = ctk.CTkFrame(self, fg_color=COR_FRAME, corner_radius=8, border_width=1, border_color=COR_FRAME_BORDA)
        frame_busca.pack(fill="x", padx=16, pady=(0, 8))

        linha_b = ctk.CTkFrame(frame_busca, fg_color="transparent")
        linha_b.pack(fill="x", padx=14, pady=8)

        ctk.CTkLabel(linha_b, text="Filtrar:", font=FONTE_LABEL_BOLD, text_color=COR_CINZA).pack(side="left", padx=(0, 6))
        self.entry_busca = ctk.CTkEntry(
            linha_b,
            textvariable=self._var_busca,
            placeholder_text="Digite o Ramal, Nome ou MAC...",
            width=260,
            height=30,
            font=FONTE_LABEL,
            fg_color=COR_BG_ESCURO,
            border_color=COR_FRAME_BORDA,
        )
        self.entry_busca.pack(side="left", padx=(0, 6))
        self.entry_busca.bind("<KeyRelease>", lambda e: self._agendar_filtro())
        self.entry_busca.bind("<Return>", lambda e: self._filtrar_tabela())

        self.btn_pesquisar = ctk.CTkButton(
            linha_b,
            text="🔍  Pesquisar",
            width=105,
            height=30,
            fg_color="#005577",
            hover_color="#0077aa",
            font=FONTE_LABEL_BOLD,
            command=self._filtrar_tabela,
        )
        self.btn_pesquisar.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(linha_b, text="Status:", font=FONTE_LABEL_BOLD, text_color=COR_CINZA).pack(side="left", padx=(0, 4))
        combo_status = ctk.CTkOptionMenu(
            linha_b,
            values=["Todos", "Apenas Registrados", "Apenas Offline", "Apenas Sem DN"],
            variable=self._var_filtro_status,
            command=lambda v: self._filtrar_tabela(),
            width=155,
            height=30,
            font=FONTE_LABEL,
            fg_color="#21262d",
            button_color="#30363d",
        )
        combo_status.pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            linha_b,
            text="🔄  Recarregar",
            command=self._conectar_e_ler,
            fg_color="#21262d",
            hover_color="#30363d",
            font=FONTE_LABEL,
            width=110,
            height=30,
        ).pack(side="left")

        self._lbl_total_filtrados = ctk.CTkLabel(
            linha_b,
            text="0 ramais listados",
            font=FONTE_LABEL,
            text_color=COR_CINZA,
        )
        self._lbl_total_filtrados.pack(side="right", padx=6)

        # 5. Tabela de Ramais e Aparelhos
        frame_tabela_container = ctk.CTkFrame(self, fg_color=COR_FRAME, corner_radius=8, border_width=1, border_color=COR_FRAME_BORDA)
        frame_tabela_container.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        # Cabeçalho da Tabela
        cabec = ctk.CTkFrame(frame_tabela_container, fg_color="#0d1117", height=34, corner_radius=6)
        cabec.pack(fill="x", padx=10, pady=(10, 4))
        cabec.pack_propagate(False)

        ctk.CTkLabel(cabec, text="Ramal", width=80, font=FONTE_LABEL_BOLD, text_color=COR_CINZA, anchor="center").pack(side="left", padx=4)
        ctk.CTkLabel(cabec, text="Nome / Caller ID", width=190, font=FONTE_LABEL_BOLD, text_color=COR_CINZA, anchor="w").pack(side="left", padx=4)
        ctk.CTkLabel(cabec, text="Pool ID", width=75, font=FONTE_LABEL_BOLD, text_color=COR_CINZA, anchor="center").pack(side="left", padx=4)
        ctk.CTkLabel(cabec, text="DN ID", width=75, font=FONTE_LABEL_BOLD, text_color=COR_CINZA, anchor="center").pack(side="left", padx=4)
        ctk.CTkLabel(cabec, text="MAC Address", width=135, font=FONTE_LABEL_BOLD, text_color=COR_CINZA, anchor="w").pack(side="left", padx=4)
        ctk.CTkLabel(cabec, text="IP do Aparelho", width=125, font=FONTE_LABEL_BOLD, text_color=COR_CINZA, anchor="w").pack(side="left", padx=4)
        ctk.CTkLabel(cabec, text="Status", width=110, font=FONTE_LABEL_BOLD, text_color=COR_CINZA, anchor="center").pack(side="left", padx=4)
        ctk.CTkLabel(cabec, text="Ações Rápidas", width=240, font=FONTE_LABEL_BOLD, text_color=COR_CINZA, anchor="center").pack(side="left", padx=(4, 8))

        # Área de Rolagem dos Dados
        self._frame_tabela = ctk.CTkScrollableFrame(frame_tabela_container, fg_color="#0d1117", corner_radius=6)
        self._frame_tabela.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Mensagem inicial
        self._lbl_vazio = ctk.CTkLabel(
            self._frame_tabela,
            text="Nenhum dado de telefonia carregado.\n\nInforme o IP e a Senha do roteador Cisco CME acima e clique em '🔌 Conectar e Sincronizar'.",
            font=("Segoe UI", 12),
            text_color=COR_CINZA,
        )
        self._lbl_vazio.pack(expand=True, pady=60)

        # 6. Painel Inferior de Terminal / Log de Operações
        frame_log = ctk.CTkFrame(self, fg_color=COR_FRAME, corner_radius=8, height=90, border_width=1, border_color=COR_FRAME_BORDA)
        frame_log.pack(fill="x", padx=16, pady=(0, 10))
        frame_log.pack_propagate(False)

        linha_log_header = ctk.CTkFrame(frame_log, fg_color="transparent")
        linha_log_header.pack(fill="x", padx=10, pady=(4, 2))

        ctk.CTkLabel(linha_log_header, text="📝 Log de Operações:", font=FONTE_LABEL_BOLD, text_color=COR_CINZA).pack(side="left")
        ctk.CTkButton(
            linha_log_header,
            text="Limpar Log",
            command=self._limpar_log,
            fg_color="transparent",
            hover_color="#21262d",
            font=("Segoe UI", 9),
            text_color=COR_CINZA,
            width=70,
            height=20,
        ).pack(side="right")

        self._txt_log = ctk.CTkTextbox(frame_log, font=FONTE_MONO, fg_color=COR_BG_ESCURO, text_color="#c9d1d9")
        self._txt_log.pack(fill="both", expand=True, padx=8, pady=(0, 6))
        self._log("Aplicação iniciada com sucesso. Pronto para conectar ao Cisco CME.")

    def _criar_card_kpi(self, pai: ctk.CTkFrame, titulo: str, valor_inicial: str, cor: str) -> ctk.CTkLabel:
        """Gera um mini-card de estatística para o dashboard superior."""
        card = ctk.CTkFrame(pai, fg_color=COR_FRAME, corner_radius=6, border_width=1, border_color=COR_FRAME_BORDA)
        card.pack(side="left", fill="both", expand=True, padx=4)

        ctk.CTkLabel(card, text=titulo, font=("Segoe UI", 9, "bold"), text_color=COR_CINZA).pack(pady=(6, 0))
        lbl_val = ctk.CTkLabel(card, text=valor_inicial, font=("Segoe UI", 18, "bold"), text_color=cor)
        lbl_val.pack(pady=(0, 6))
        return lbl_val

    # ------------------------------------------------------------------
    # Lógica de Conexão e Comunicação SSH
    # ------------------------------------------------------------------

    def _set_status(self, texto: str, cor: str) -> None:
        """Atualiza o badge de status na thread principal."""
        if self.lbl_status_conexao and self.lbl_status_conexao.winfo_exists():
            self.lbl_status_conexao.configure(text=texto, text_color=cor)

    def _log(self, mensagem: str) -> None:
        """Adiciona uma linha no terminal de logs."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        linha = f"[{timestamp}] {mensagem}\n"
        if self._txt_log and self._txt_log.winfo_exists():
            self._txt_log.insert("end", linha)
            self._txt_log.see("end")

    def _limpar_log(self) -> None:
        """Limpa a janela de logs."""
        if self._txt_log and self._txt_log.winfo_exists():
            self._txt_log.delete("1.0", "end")

    def _conectar_e_ler(self) -> None:
        """Valida credenciais e inicia a sincronização assíncrona com o roteador."""
        ip = self._var_ip.get().strip()
        senha = self._var_pass.get()

        if not ip:
            messagebox.showwarning("Aviso", "Por favor, informe o IP do roteador Cisco CME.")
            return
        if not senha:
            messagebox.showwarning("Aviso", "Por favor, digite a senha SSH do roteador.")
            return

        user = self._var_user.get().strip() or "admin"
        port_str = self._var_port.get().strip() or "22"
        secret = self._var_secret.get()
        porta = int(port_str) if port_str.isdigit() else 22

        if self.btn_conectar and self.btn_conectar.winfo_exists():
            self.btn_conectar.configure(state="disabled", text="⏳  Lendo CME...")

        self._set_status("● Conectando...", COR_DESTAQUE)
        self._log(f"Iniciando conexão SSH com {ip}:{porta} como '{user}'...")

        threading.Thread(
            target=self._worker_sincronizar_cme,
            args=(ip, porta, user, senha, secret),
            daemon=True,
        ).start()

    def _worker_sincronizar_cme(self, ip: str, port: int, user: str, senha: str, secret: str) -> None:
        """Thread em segundo plano que executa Netmiko e lê os ramais."""
        try:
            if not self.cme_client or not self.cme_client.conectado:
                self.cme_client = CiscoCMEClient(
                    host=ip,
                    port=port,
                    username=user,
                    password=senha,
                    secret=secret,
                )
                self.cme_client.conectar()

            self.after(0, self._set_status, f"● Conectado ({ip})", COR_VERDE)
            self.after(0, self._log, "Conexão estabelecida. Executando leitura de DNs, Pools e Status...")

            itens = self.cme_client.obter_status_telefonia()
            self.after(0, self._renderizar_tabela, itens)
        except Exception as exc:
            err_msg = str(exc)
            def on_erro():
                if self.btn_conectar and self.btn_conectar.winfo_exists():
                    self.btn_conectar.configure(state="normal", text="🔌  Conectar e Sincronizar")
                self._set_status("● Falha de Conexão", COR_VERMELHO)
                self._log(f"ERRO: {err_msg}")
                messagebox.showerror(
                    "Falha ao Consultar CME",
                    f"Não foi possível obter os dados de telefonia do roteador:\n\n{err_msg}\n\n"
                    "Verifique:\n"
                    "1. Se o IP e porta estão acessíveis.\n"
                    "2. Se as credenciais SSH estão corretas.\n"
                    "3. Se o serviço Cisco CME (SIP ou SCCP) está ativado no roteador.",
                )
            self.after(0, on_erro)

    # ------------------------------------------------------------------
    # Renderização da Tabela, Cache de Estado e Atualização de KPIs
    # ------------------------------------------------------------------

    def _renderizar_tabela(self, itens: List[Dict[str, Any]]) -> None:
        """
        Recebe os dados parseados via Netmiko UMA ÚNICA VEZ e armazena no Cache de Estado.
        Em seguida, constrói os widgets na tabela de forma estática.
        """
        if self.btn_conectar and self.btn_conectar.winfo_exists():
            self.btn_conectar.configure(state="normal", text="🔌  Conectar e Sincronizar")

        # Armazena na variável de estado da classe (Fetch & Cache)
        self.dados_atuais = list(itens)
        self._cme_ramais = self.dados_atuais

        self._atualizar_kpis()
        self.popular_tabela()

        total = len(itens)
        if total > 0:
            self._log(f"Sincronização concluída com sucesso! {total} registros carregados no cache.")
        else:
            self._log("Aviso: Conexão bem-sucedida, porém nenhum ramal cadastrado retornado.")
            messagebox.showinfo(
                "Nenhum Registro Encontrado",
                "Conexão com o roteador estabelecida com sucesso!\n\n"
                "Porém, não foram encontrados ramais (DNs) ou aparelhos (Pools) configurados.",
            )

    def _atualizar_kpis(self) -> None:
        """Calcula os totais a partir do cache de estado e atualiza os cards de KPI."""
        total = len(self.dados_atuais)
        registrados = 0
        offline = 0
        sem_dn = 0

        for it in self.dados_atuais:
            st = str(it.get("status", "")).lower()
            dn = str(it.get("dn_id", "")).lower()
            if st in ("registrado", "registered", "online", "active"):
                registrados += 1
            else:
                offline += 1

            if dn in ("sem dn", "-", ""):
                sem_dn += 1

        if self._lbl_kpi_total: self._lbl_kpi_total.configure(text=str(total))
        if self._lbl_kpi_registrados: self._lbl_kpi_registrados.configure(text=str(registrados))
        if self._lbl_kpi_offline: self._lbl_kpi_offline.configure(text=str(offline))
        if self._lbl_kpi_sem_dn: self._lbl_kpi_sem_dn.configure(text=str(sem_dn))

    def popular_tabela(self) -> None:
        """
        Constrói os widgets (CTkLabels, CTkButtons) para as linhas da tabela UMA ÚNICA VEZ.
        Durante o scroll, NENHUM processamento ou Netmiko é executado; a tabela fica 100% estática.
        """
        if not self._frame_tabela or not self._frame_tabela.winfo_exists():
            return

        for w in self._frame_tabela.winfo_children():
            w.destroy()

        self._linhas_widgets.clear()

        if not self.dados_atuais:
            ctk.CTkLabel(
                self._frame_tabela,
                text="Nenhum ramal carregado. Clique em 'Conectar e Sincronizar'.",
                font=FONTE_LABEL,
                text_color=COR_CINZA,
            ).pack(expand=True, pady=40)
            if self._lbl_total_filtrados and self._lbl_total_filtrados.winfo_exists():
                self._lbl_total_filtrados.configure(text="0 ramais listados")
            return

        # Constrói todas as linhas de uma só vez e armazena a referência para filtro rápido sem recriar
        for item in self.dados_atuais:
            row_frame = self._criar_linha_tabela(self._frame_tabela, item)
            # Guarda campos em minúsculo para filtragem instantânea em memória
            search_blob = " ".join([
                str(item.get("ramal", "")),
                str(item.get("nome", "")),
                str(item.get("pool_id", "") or item.get("pool", "")),
                str(item.get("dn_id", "")),
                str(item.get("mac_address", "") or item.get("mac", "")),
                str(item.get("ip", "")),
                str(item.get("status", "")),
            ]).lower()
            self._linhas_widgets.append((row_frame, item, search_blob))

        if self._lbl_total_filtrados and self._lbl_total_filtrados.winfo_exists():
            self._lbl_total_filtrados.configure(text=f"{len(self.dados_atuais)} de {len(self.dados_atuais)} ramais listados")

    def _agendar_filtro(self) -> None:
        """Aplica debounce de 150ms na digitação para evitar filtragens desnecessárias."""
        if self._debounce_filtro_id:
            try:
                self.after_cancel(self._debounce_filtro_id)
            except Exception:
                pass
        self._debounce_filtro_id = self.after(150, self._filtrar_tabela)

    def _filtrar_tabela(self) -> None:
        """
        Filtra os elementos já construídos em memória sem reconstruir widgets.
        Alterna a visibilidade via pack/pack_forget de forma instantânea e sem lag.
        """
        if not self._linhas_widgets:
            return

        termo = (self._var_busca.get() or "").lower().strip()
        filtro_st = self._var_filtro_status.get()

        visiveis = 0
        for row_frame, item, search_blob in self._linhas_widgets:
            st = str(item.get("status", "")).lower()
            dn = str(item.get("dn_id", "")).lower()
            is_reg = st in ("registrado", "registered", "online", "active")

            # Valida filtro do dropdown
            if filtro_st == "Apenas Registrados" and not is_reg:
                row_frame.pack_forget()
                continue
            if filtro_st == "Apenas Offline" and is_reg:
                row_frame.pack_forget()
                continue
            if filtro_st == "Apenas Sem DN" and dn not in ("sem dn", "-", ""):
                row_frame.pack_forget()
                continue

            # Valida termo de busca
            if termo and termo not in search_blob:
                row_frame.pack_forget()
                continue

            # Item visível
            row_frame.pack(fill="x", pady=2, padx=2)
            visiveis += 1

        if self._lbl_total_filtrados and self._lbl_total_filtrados.winfo_exists():
            self._lbl_total_filtrados.configure(text=f"{visiveis} de {len(self.dados_atuais)} ramais listados")

    def _criar_linha_tabela(self, pai: ctk.CTkFrame, item: Dict[str, Any]) -> ctk.CTkFrame:
        """Renderiza uma linha individual de ramal na tabela e retorna o widget da linha."""
        row = ctk.CTkFrame(pai, fg_color="#121824", corner_radius=6, height=38)
        row.pack(fill="x", pady=2, padx=2)
        row.pack_propagate(False)

        # 1. Ramal
        ctk.CTkLabel(
            row,
            text=str(item.get("ramal", "-")),
            width=80,
            font=("Segoe UI", 12, "bold"),
            text_color=COR_DESTAQUE,
            anchor="center",
        ).pack(side="left", padx=4)

        # 2. Nome / Caller ID
        ctk.CTkLabel(
            row,
            text=str(item.get("nome", "-")),
            width=190,
            font=FONTE_LABEL_BOLD,
            text_color="#ffffff",
            anchor="w",
        ).pack(side="left", padx=4)

        # 3. Pool ID
        raw_pool = str(item.get("pool_id") or item.get("pool", "-"))
        pool_num = "".join(ch for ch in raw_pool if ch.isdigit())
        pool_display = f"Pool {pool_num}" if pool_num else str(item.get("pool", "-"))
        ctk.CTkLabel(
            row,
            text=pool_display,
            width=75,
            font=("Segoe UI", 10, "bold"),
            text_color=COR_CINZA,
            fg_color="#1a263a",
            corner_radius=4,
        ).pack(side="left", padx=4)

        # 4. DN ID
        raw_dn = str(item.get("dn_id", "-")).strip()
        dn_num = "".join(ch for ch in raw_dn if ch.isdigit())
        dn_display = f"DN {dn_num}" if dn_num else "Sem DN"
        dn_cor = COR_DESTAQUE if dn_num else COR_CINZA
        ctk.CTkLabel(
            row,
            text=dn_display,
            width=75,
            font=("Segoe UI", 10, "bold"),
            text_color=dn_cor,
            fg_color="#15202b" if dn_num else "#1a1a1a",
            corner_radius=4,
        ).pack(side="left", padx=4)

        # 5. MAC Address
        mac_str = str(item.get("mac_address") or item.get("mac") or "-")
        ctk.CTkLabel(
            row,
            text=mac_str,
            width=135,
            font=FONTE_MONO,
            text_color="#00e5ff",
            anchor="w",
        ).pack(side="left", padx=4)

        # 6. IP do Aparelho
        ip_str = str(item.get("ip", "-"))
        ctk.CTkLabel(
            row,
            text=ip_str,
            width=125,
            font=FONTE_MONO,
            text_color=COR_CINZA,
            anchor="w",
        ).pack(side="left", padx=4)

        # 7. Status Badge
        st = str(item.get("status", "Offline")).capitalize()
        is_reg = st.lower() in ("registered", "registrado", "online", "active")
        cor_st = COR_VERDE if is_reg else COR_VERMELHO
        txt_st = "● Registrado" if is_reg else "● Offline"

        ctk.CTkLabel(
            row,
            text=txt_st,
            width=110,
            font=("Segoe UI", 10, "bold"),
            text_color=cor_st,
            anchor="center",
        ).pack(side="left", padx=4)

        # 8. Ações Rápidas
        frame_acoes = ctk.CTkFrame(row, fg_color="transparent", width=240)
        frame_acoes.pack(side="left", fill="y", padx=(4, 8))

        btn_reset = ctk.CTkButton(
            frame_acoes,
            text="🔄  Reiniciar (Reset)",
            command=lambda it=item: self._confirmar_reset_pool(it),
            fg_color="#8b3a1a",
            hover_color="#ab4a24",
            font=("Segoe UI", 10, "bold"),
            width=120,
            height=26,
        )
        btn_reset.pack(side="left", padx=3, pady=6)
        if not pool_num:
            btn_reset.configure(state="disabled")

        btn_edit = ctk.CTkButton(
            frame_acoes,
            text="✏️  Editar Nome",
            command=lambda it=item: self._abrir_modal_editar_nome(it),
            fg_color=COR_BOTAO_PRIMARIO,
            hover_color=COR_BOTAO_HOVER,
            font=("Segoe UI", 10, "bold"),
            width=105,
            height=26,
        )
        btn_edit.pack(side="left", padx=3, pady=6)

        return row

    # ------------------------------------------------------------------
    # Ações Rápidas: Reset de Pool e Edição de Nome
    # ------------------------------------------------------------------

    def _confirmar_reset_pool(self, item: Dict[str, Any]) -> None:
        """Confirma e dispara o comando de reset para o telefone VoIP."""
        raw_pool = str(item.get("pool_id") or item.get("pool", "-"))
        pool_id = "".join(ch for ch in raw_pool if ch.isdigit())
        ramal = str(item.get("ramal", "-"))
        mac = str(item.get("mac_address") or item.get("mac") or "-")

        if not pool_id:
            messagebox.showinfo("Aviso", "Este registro não possui um Pool ID numérico.")
            return

        if not messagebox.askyesno(
            "Confirmar Reinicialização (Reset)",
            f"Deseja reiniciar o aparelho VoIP do Pool {pool_id} (Ramal {ramal})?\n\n"
            f"MAC Address: {mac}\n\n"
            f"Comandos executados:\n"
            f"  voice register pool {pool_id}\n"
            f"  reset\n"
            f"  exit",
            icon="warning",
        ):
            return

        comandos = CiscoCMETemplates.get_pool_reset(pool_id)
        threading.Thread(
            target=self._worker_enviar_comandos,
            args=(comandos, f"Reset do Pool {pool_id} (Ramal {ramal})"),
            daemon=True,
        ).start()

    def _abrir_modal_editar_nome(self, item: Dict[str, Any]) -> None:
        """Abre janela modal para alterar a descrição / Caller-ID no CME."""
        ramal = str(item.get("ramal", "-"))
        raw_dn = str(item.get("dn_id", ""))
        dn_num = "".join(ch for ch in raw_dn if ch.isdigit())
        if not dn_num:
            messagebox.showinfo(
                "Aviso — Sem DN Vinculado",
                f"Este aparelho (Pool {item.get('pool_id')}) não possui um Directory Number (DN) vinculado.\n\n"
                "Para alterar o nome do colaborador, associe primeiro um DN ao Pool.",
                parent=self,
            )
            return
        dn_id = dn_num

        nome_atual = str(item.get("nome", ""))
        if nome_atual.startswith("Ramal "):
            nome_atual = ""

        modal = ctk.CTkToplevel(self)
        modal.title(f"✏️ Editar Nome — Ramal {ramal}")
        modal.geometry("450x280")
        modal.minsize(400, 250)
        modal.configure(fg_color=COR_BG_ESCURO)
        modal.transient(self)
        modal.grab_set()

        modal.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - 225
        y = self.winfo_y() + (self.winfo_height() // 2) - 140
        modal.geometry(f"+{max(0, x)}+{max(0, y)}")

        ctk.CTkLabel(
            modal,
            text=f"✏️  Editar Nome / Caller ID — Ramal {ramal}",
            font=FONTE_TITULO,
            text_color=COR_DESTAQUE,
        ).pack(anchor="w", padx=20, pady=(16, 2))

        ctk.CTkLabel(
            modal,
            text=f"Comando executado: voice register dn {dn_id} -> name <novo_nome>",
            font=("Segoe UI", 9),
            text_color=COR_CINZA,
        ).pack(anchor="w", padx=20, pady=(0, 10))

        ctk.CTkFrame(modal, height=1, fg_color=COR_FRAME_BORDA).pack(fill="x", padx=20, pady=(0, 14))

        frame_campos = ctk.CTkFrame(modal, fg_color="transparent")
        frame_campos.pack(fill="x", padx=20, pady=(0, 14))

        ctk.CTkLabel(frame_campos, text="Nome do Colaborador / Descrição:", font=FONTE_LABEL_BOLD, text_color="#ffffff").pack(anchor="w", pady=(0, 4))
        entry_nome = ctk.CTkEntry(
            frame_campos,
            placeholder_text="ex: Ramal Exemplo - Operacoes",
            font=FONTE_LABEL,
            fg_color="#0d1117",
            border_color=COR_FRAME_BORDA,
            height=34,
        )
        entry_nome.pack(fill="x", pady=(0, 8))
        if nome_atual:
            entry_nome.insert(0, nome_atual)

        frame_botoes = ctk.CTkFrame(modal, fg_color="transparent")
        frame_botoes.pack(fill="x", padx=20, pady=(0, 16))

        def salvar():
            novo_nome = entry_nome.get().strip()
            if not novo_nome:
                messagebox.showerror("Campo Obrigatório", "Por favor, informe o novo nome.", parent=modal)
                entry_nome.focus_set()
                return

            modal.destroy()
            comandos = CiscoCMETemplates.get_dn_name_config(dn_id, novo_nome)
            threading.Thread(
                target=self._worker_enviar_comandos,
                args=(comandos, f"Alteração de Nome do Ramal {ramal} para '{novo_nome}'", item, novo_nome),
                daemon=True,
            ).start()

        ctk.CTkButton(
            frame_botoes,
            text="💾 Salvar e Aplicar",
            command=salvar,
            fg_color="#1f6feb",
            hover_color="#388bfd",
            font=FONTE_LABEL_BOLD,
            height=36,
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            frame_botoes,
            text="Cancelar",
            command=modal.destroy,
            fg_color="#3a3a3a",
            hover_color="#555",
            font=FONTE_LABEL,
            height=36,
            width=90,
        ).pack(side="right")

        entry_nome.bind("<Return>", lambda e: salvar())
        entry_nome.focus_set()

    def _worker_enviar_comandos(
        self,
        comandos: List[str],
        descricao: str,
        item_atualizar: Optional[Dict[str, Any]] = None,
        novo_nome: Optional[str] = None,
    ) -> None:
        """Executa comandos de configuração no Cisco CME via SSH."""
        try:
            if not self.cme_client or not self.cme_client.conectado:
                raise RuntimeError("Não há conexão SSH ativa com o roteador CME.")

            self.cme_client.enviar_configuracoes(comandos)

            def on_sucesso():
                if item_atualizar is not None and novo_nome is not None:
                    item_atualizar["nome"] = novo_nome
                    self._filtrar_tabela()

                self._log(f"Comandos de {descricao} aplicados com sucesso.")
                messagebox.showinfo(
                    "Operação Concluída",
                    f"{descricao} concluída com sucesso no roteador Cisco CME!\n\n"
                    f"Comandos aplicados:\n" + "\n".join(f"• {c}" for c in comandos),
                )

            self.after(0, on_sucesso)
        except Exception as exc:
            def on_erro(err_msg=str(exc)):
                self._log(f"Erro em {descricao}: {err_msg}")
                messagebox.showerror("Erro CME", f"Falha ao executar comandos no CME:\n\n{err_msg}")
            self.after(0, on_erro)


# ---------------------------------------------------------------------------
# Ponto de Entrada da Aplicação
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app = AppCME()
    app.mainloop()
