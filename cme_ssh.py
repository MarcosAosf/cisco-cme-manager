"""
Cliente SSH especializado em Cisco CME (Communications Manager Express).
Orquestração via Netmiko/Paramiko com leitura por blocos, desativação de paginação (terminal length 0)
e suporte unificado a SIP (voice register) e SCCP (telephony-service).
"""

import logging
import re
import sys
import types
from typing import Any, Dict, List, Optional

# Polyfill para Python 3.13+ onde telnetlib foi removido
if "telnetlib" not in sys.modules:
    class _DummyTelnetlib(types.ModuleType):
        def __getattr__(self, name: str) -> Any:
            return b"\x00"
    sys.modules["telnetlib"] = _DummyTelnetlib("telnetlib")

try:
    from netmiko import ConnectHandler
    from netmiko.exceptions import (
        NetmikoAuthenticationException,
        NetmikoTimeoutException,
        SSHException,
    )
except ImportError:
    ConnectHandler = None
    NetmikoAuthenticationException = Exception
    NetmikoTimeoutException = Exception
    SSHException = Exception

logger = logging.getLogger("CiscoCMEClient")


def processar_dados_cme(saida_show_dn: str, saida_show_pool: str, saida_status_sip: str = "") -> tuple:
    r"""
    Processador de dados do CME (SIP) em três etapas relacionais:
    1. Mapeia todos os DNs (Directory Numbers), capturando ramal e nome/caller-id.
    1.5. Memoriza Status e IP dinâmicos via saída de 'show sip-ua status registrar'.
    2. Segmenta os Pools, extrai Pool ID, MAC e o vínculo estrito com DN ('number 1 dn X').
       Executa o Join relacional direto com o dict_status para definir IP e Status (Registrado/Offline).
    Retorna (quantidade_total_pools, lista_final).
    """
    # ==========================================
    # ETAPA 1: Memorizar os 352+ DNs (O Dicionário)
    # ==========================================
    dicionario_dns: Dict[str, Dict[str, str]] = {}

    blocos_dn = re.split(r'(?:\n|^)(?:voice\s+register\s+)?dn\s+', saida_show_dn, flags=re.IGNORECASE)
    if len(blocos_dn) <= 1:
        blocos_dn = re.split(r'voice\s+register\s+dn\s+', saida_show_dn, flags=re.IGNORECASE)

    for bloco in blocos_dn[1:]:
        # Captura o número do DN logo no início do bloco
        id_match = re.search(r'^(\d+)', bloco.lstrip())
        if not id_match:
            continue
        dn_id = id_match.group(1).strip()

        # Correção 1: Exige apenas dígitos para evitar 'pickup-group', 'name', etc.
        ramal_match = re.search(r'number\s+(\d+)', bloco, re.IGNORECASE)
        # Correção 1: Nome até o fim da linha
        nome_match = re.search(r'name\s+([^\n\r]+)', bloco, re.IGNORECASE)

        raw_name = nome_match.group(1).strip() if nome_match else '-'
        clean_name = re.sub(r'^(?:primary\s+name|name)[:\s]*', '', raw_name, flags=re.IGNORECASE).strip(' \t\r\n"\'')

        dicionario_dns[dn_id] = {
            'ramal': ramal_match.group(1).strip() if ramal_match else '-',
            'nome': clean_name if clean_name else '-'
        }

    # ==========================================
    # ETAPA 1.5: Memorizar Status e IP (SIP-UA)
    # ==========================================
    dict_status: Dict[str, str] = {}
    if saida_status_sip:
        for linha in saida_status_sip.splitlines():
            linha = linha.strip()
            # Ignora cabeçalhos, separadores e linhas que não começam com o dígito do Ramal
            if not linha or not linha[0].isdigit():
                continue

            partes = linha.split()
            if len(partes) >= 4:
                ramal_ativo = partes[0]
                # Extrai todos os IPs da linha e guarda o último (Contact IP)
                ips = re.findall(r'\b\d{1,3}(?:\.\d{1,3}){3}\b', linha)
                if ips:
                    dict_status[ramal_ativo] = ips[-1]

    # ==========================================
    # ETAPA 2: Extrair Pools e Executar o "Join"
    # ==========================================
    lista_final: List[Dict[str, Any]] = []

    blocos_pool = re.split(r'(?:\n|^)(?:voice\s+register\s+)?pool\s+', saida_show_pool, flags=re.IGNORECASE)
    if len(blocos_pool) <= 1:
        blocos_pool = re.split(r'voice\s+register\s+pool\s+', saida_show_pool, flags=re.IGNORECASE)
    lista_pools_validos = blocos_pool[1:] if len(blocos_pool) > 1 else []

    quantidade_total_pools = len(lista_pools_validos)

    for bloco in lista_pools_validos:
        # ID do Pool
        id_match = re.search(r'^(\d+)', bloco.lstrip())
        pool_id = id_match.group(1).strip() if id_match else '?'

        # Captura MAC
        mac_match = re.search(r'(?:(?:id\s+)?mac(?:\-address)?|mac:?)\s*[:\s]*([0-9a-fA-F\.\-]{12,17})', bloco, re.IGNORECASE)
        raw_mac = mac_match.group(1).strip() if mac_match else '-'

        clean_mac = re.sub(r'[^0-9a-fA-F]', '', raw_mac).lower()
        formatted_mac = f"{clean_mac[0:4]}.{clean_mac[4:8]}.{clean_mac[8:12]}" if len(clean_mac) == 12 else raw_mac

        # Vínculo ESTRITO 'number \d+ dn (\d+)'
        # Se não encontrar, dn_id_encontrado é None (Sem DN)
        link_dn_match = re.search(r'number\s+\d+\s+dn\s+(\d+)', bloco, re.IGNORECASE)
        dn_id_encontrado = link_dn_match.group(1).strip() if link_dn_match else None

        # Join Relacional Estrito com DNs
        ramal_final = '-'
        nome_final = '-'
        if dn_id_encontrado and dn_id_encontrado in dicionario_dns:
            ramal_final = dicionario_dns[dn_id_encontrado]['ramal']
            nome_final = dicionario_dns[dn_id_encontrado]['nome']

        dn_display = dn_id_encontrado if dn_id_encontrado else 'Sem DN'

        # Join relacional com o Status SIP-UA Dinâmico
        if ramal_final != '-' and ramal_final in dict_status:
            ip_encontrado = dict_status[ramal_final]
            status_final = 'Registrado'
        else:
            ip_encontrado = '-'
            status_final = 'Offline'

        item_dict = {
            'Pool ID': f'Pool {pool_id}',
            'pool': f'Pool {pool_id}',
            'pool_id': pool_id,
            'DN ID': dn_display,
            'dn_id': dn_display,
            'MAC Address': formatted_mac,
            'mac': formatted_mac,
            'mac_address': formatted_mac,
            'IP do Aparelho': ip_encontrado,
            'ip': ip_encontrado,
            'status': status_final,
            'Status': status_final,
            'Ramal': ramal_final,
            'ramal': ramal_final,
            'Nome / Caller ID': nome_final,
            'nome': nome_final,
        }
        lista_final.append(item_dict)

    return quantidade_total_pools, lista_final


def extrair_dns_cme(dn_output: str) -> Dict[str, Dict[str, str]]:
    """
    Extrai Directory Numbers (DN) do Cisco CME dividindo por blocos:
    - SIP: 'voice register dn <ID>' ou 'DN <ID>'
    - SCCP: 'ephone-dn <ID>'

    Retorna um dicionário mapeando dn_id -> {'dn_id': ..., 'ramal': ..., 'nome': ...}.
    """
    dict_dns: Dict[str, Dict[str, str]] = {}
    if not dn_output:
        return dict_dns

    # 1. Divisão por blocos baseada no início de linha com DN ou ephone-dn
    texto_dns_ajustado = "\n" + dn_output
    blocos_dn = re.split(r"\n(?:(?:voice\s+register\s+)?dn|ephone-dn)\s+", texto_dns_ajustado, flags=re.IGNORECASE)
    if len(blocos_dn) <= 1:
        blocos_dn = re.split(r"voice\s+register\s+dn\s+", dn_output, flags=re.IGNORECASE)

    lista_de_dns_validos = blocos_dn[1:] if len(blocos_dn) > 1 else []

    for bloco in lista_de_dns_validos:
        id_match = re.search(r"^(\d+)", bloco.lstrip())
        if not id_match:
            continue
        dn_id = id_match.group(1).strip()
        m_num = re.search(r"\b(?:number|num)\s+(\d+)", bloco, re.IGNORECASE)
        m_name = re.search(r"\b(?:name|description)\s+([^\r\n]+)", bloco, re.IGNORECASE)
        num = m_num.group(1).strip() if m_num else "-"
        raw_name = m_name.group(1).strip() if m_name else "-"
        clean_name = re.sub(r"^(?:primary\s+name|name)[:\s]*", "", raw_name, flags=re.IGNORECASE).strip(' \t\r\n"\'')
        dict_dns[dn_id] = {
            "dn_id": dn_id,
            "ramal": num,
            "nome": clean_name if clean_name else (f"Ramal {num}" if num != "-" else "-"),
        }

    # 2. Fallback / Complemento: linhas tabulares (ex: saídas de show voice register dn brief/summary)
    for line in dn_output.splitlines():
        line_c = line.strip()
        if not line_c or line_c.startswith(("-", "=", "#")) or "% Invalid" in line_c:
            continue
        if re.match(r"^(?:DN|TAG|EPHONE-DN)\s+[A-Za-z#_-]", line_c, re.IGNORECASE):
            continue
        m = re.match(
            r"^\s*(?:(?:voice\s+register\s+)?dn\s+|ephone-dn\s+)?(\d+)(?:\s+(?:tag\s+)?\d+)?(?:\s+|\s*\(\s*)(\d{2,8})\)?\s*(.*?)(?:\s+(IDLE|BUSY|REGISTERED|UNREGISTERED|ACTIVE|OFFLINE))?$",
            line_c,
            re.IGNORECASE,
        )
        if m:
            dn_id = m.group(1).strip()
            if dn_id not in dict_dns or dict_dns[dn_id].get("ramal") == "-":
                num = m.group(2).strip()
                raw_name = (m.group(3) or "").strip()
                clean_name = re.sub(r"^(?:primary\s+name|name)[:\s]*", "", raw_name, flags=re.IGNORECASE).strip(' \t\r\n"\'')
                dict_dns[dn_id] = {
                    "dn_id": dn_id,
                    "ramal": num,
                    "nome": clean_name if clean_name else f"Ramal {num}",
                }

    return dict_dns


def extrair_pools_cme(
    pool_output: str,
    pool_status_output: str = "",
    dict_dns: Optional[Dict[str, Dict[str, str]]] = None,
) -> List[Dict[str, Any]]:
    """
    Extrai e cruza aparelhos/pools SIP e SCCP:
    - Corta o texto exatamente onde começa uma nova linha com "Pool <ID>" ou "voice register pool <ID>"
    - Determina a quantidade_total_pools a partir da contagem de blocos válidos
    - Dentro de cada bloco, extrai o Pool ID, MAC, IP e o link com o DN associado ('number 1 dn <ID>')
    - Cruza com a tabela de IP e Status (brief / summary)
    - Cruza com o dicionário de DNs (dict_dns) para associar Ramal e Nome
    """
    if dict_dns is None:
        dict_dns = {}

    # 1. Mapa de IP e Status a partir de show voice register pool brief / summary
    status_map: Dict[str, Dict[str, str]] = {}
    texto_status = f"{pool_output}\n{pool_status_output}"

    for line in texto_status.splitlines():
        line_c = line.strip()
        if not line_c or line_c.startswith(("-", "=", "#")) or "% Invalid" in line_c:
            continue
        if re.match(r"^(?:POOL|DEVICE|EPHONE|MAC)\s+[A-Za-z#_-]", line_c, re.IGNORECASE):
            continue

        pm = re.match(r"^\s*(?:(?:voice\s+register\s+)?pool\s+|ephone[-_\s]*)?(\d+)", line_c, re.IGNORECASE)
        ip_m = re.search(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b", line_c)
        mac_m = re.search(
            r"(?:SEP|Mac:)?([0-9a-fA-F]{4}\.[0-9a-fA-F]{4}\.[0-9a-fA-F]{4}|[0-9a-fA-F]{12})",
            line_c,
            re.IGNORECASE,
        )
        st_m = re.search(r"\b(REGISTERED|UNREGISTERED|OFFLINE|ONLINE|DE-REGISTERED|ACTIVE)\b", line_c, re.IGNORECASE)

        ip_val = ip_m.group(1).strip() if ip_m else "-"
        raw_mac = mac_m.group(1).strip() if mac_m else "-"
        st_val = st_m.group(1).strip() if st_m else "Unregistered"

        if pm:
            p_id = pm.group(1).strip()
            if p_id not in status_map:
                status_map[p_id] = {"ip": ip_val, "mac": raw_mac, "status": st_val}
            else:
                if ip_val != "-":
                    status_map[p_id]["ip"] = ip_val
                if raw_mac != "-":
                    status_map[p_id]["mac"] = raw_mac
                if st_val != "Unregistered":
                    status_map[p_id]["status"] = st_val

        if raw_mac != "-":
            c_mac = re.sub(r"[^0-9a-fA-F]", "", raw_mac).lower()
            if len(c_mac) == 12:
                norm_mac = f"{c_mac[0:4]}.{c_mac[4:8]}.{c_mac[8:12]}"
                status_map[norm_mac] = {"ip": ip_val, "status": st_val}

    # 2. Divisão da saída detalhada em blocos por Pool (\nPool ou \nvoice register pool)
    pools_encontrados: Dict[str, Dict[str, Any]] = {}
    texto_pools_ajustado = "\n" + pool_output
    blocos_pool = re.split(r"\n(?:(?:voice\s+register\s+)?pool|ephone)\s+", texto_pools_ajustado, flags=re.IGNORECASE)
    lista_de_pools_validos = blocos_pool[1:] if len(blocos_pool) > 1 else []
    quantidade_total_pools = len(lista_de_pools_validos)
    logger.info("CME: Total de blocos de pools detectados no roteador: %d", quantidade_total_pools)

    for bloco in lista_de_pools_validos:
        # Extrai pools em blocos (voice register pool <ID>)
        blocos_pool = re.split(r"\n(?:(?:voice\s+register\s+)?pool|ephone)\s+", texto_pools_ajustado, flags=re.IGNORECASE)
        # Fallback: caso a saída não comece com quebra de linha estrita antes de voice register pool
        if len(blocos_pool) <= 1:
            blocos_pool = re.split(r"voice\s+register\s+pool\s+", pool_output, flags=re.IGNORECASE)

        lista_de_pools_validos = blocos_pool[1:] if len(blocos_pool) > 1 else []
        quantidade_total_pools = len(lista_de_pools_validos)
        logger.info("CME: Total de blocos de pools detectados no roteador: %d", quantidade_total_pools)

        for bloco in lista_de_pools_validos:
            id_match = re.search(r"^(\d+)", bloco.lstrip())
            pool_id = id_match.group(1).strip() if id_match else "?"

            # Captura MAC (ex: "id mac 00B8.B33A.E9B8" ou "mac-address ...")
            mac_match = re.search(r"(?:(?:id\s+)?mac(?:\-address)?|mac:?)\s*[:\s]*([0-9a-fA-F\.\-]{12,17})", bloco, re.IGNORECASE)
            raw_mac = mac_match.group(1).strip() if mac_match else "-"

            # Captura IP
            ip_match = re.search(r"\b(?:ip(?:\s+address)?|ip:)\s*(\d{1,3}(?:\.\d{1,3}){3})", bloco, re.IGNORECASE)
            ip_val = ip_match.group(1).strip() if ip_match else "-"

            # Captura Status
            st_match = re.search(r"\b(REGISTERED|UNREGISTERED|OFFLINE|ONLINE|DE-REGISTERED|ACTIVE)\b", bloco, re.IGNORECASE)
            st_val = st_match.group(1).strip() if st_match else "Unregistered"

            # Captura associação com DN: SIP 'number 1 dn 2' e SCCP 'button 1:2'
            dn_match = re.search(r"(?:number\s+\d+\s+dn|button\s+\d+\s*:\s*|dn\s+)(\d+)", bloco, re.IGNORECASE)
            dn_id_vinculado = dn_match.group(1).strip() if dn_match else "-"

        if pool_id != "?":
            pools_encontrados[pool_id] = {
                "pool_id": pool_id,
                "mac": raw_mac,
                "ip": ip_val,
                "status": st_val,
                "dn_id": dn_id_vinculado,
            }

    # Complementa pools presentes no status_map caso a saída de blocos tenha omitido algum
    for p_id, st_info in status_map.items():
        if p_id.isdigit() and p_id not in pools_encontrados:
            pools_encontrados[p_id] = {
                "pool_id": p_id,
                "mac": st_info.get("mac", "-"),
                "ip": st_info.get("ip", "-"),
                "status": st_info.get("status", "Unregistered"),
                "dn_id": "-",
            }

    # 3. Cruzamento e montagem final da lista de ramais
    resultado: List[Dict[str, Any]] = []
    sorted_pools = sorted(
        pools_encontrados.values(),
        key=lambda x: int(x["pool_id"]) if str(x["pool_id"]).isdigit() else str(x["pool_id"]),
    )

    for p in sorted_pools:
        p_id = p["pool_id"]
        dn_id = p.get("dn_id", "-")

        # MAC Address
        raw_mac = p["mac"]
        if raw_mac == "-" and p_id in status_map:
            raw_mac = status_map[p_id].get("mac", "-")

        clean_mac = re.sub(r"[^0-9a-fA-F]", "", raw_mac).lower()
        formatted_mac = f"{clean_mac[0:4]}.{clean_mac[4:8]}.{clean_mac[8:12]}" if len(clean_mac) == 12 else raw_mac

        # IP e Status
        ip_val = p["ip"]
        st_val = p["status"]

        if (ip_val == "-" or st_val == "Unregistered") and p_id in status_map:
            if ip_val == "-":
                ip_val = status_map[p_id].get("ip", "-")
            if st_val == "Unregistered":
                st_val = status_map[p_id].get("status", "Unregistered")

        if (ip_val == "-" or st_val == "Unregistered") and formatted_mac != "-" and formatted_mac in status_map:
            if ip_val == "-":
                ip_val = status_map[formatted_mac].get("ip", "-")
            if st_val == "Unregistered":
                st_val = status_map[formatted_mac].get("status", "Unregistered")

        st_upper = st_val.upper()
        status_final = "Registrado" if st_upper in ("REGISTERED", "ONLINE", "ACTIVE") else "Offline"

        # Cruzamento estrito com dict_dns usando dn_id_vinculado
        # NUNCA deduzir dn_id = p_id! Se não tiver vínculo, fica "Sem DN"
        dn_info = {}
        if dn_id != "-" and dn_id in dict_dns:
            dn_info = dict_dns[dn_id]
        else:
            dn_id = "Sem DN"

        ramal_val = dn_info.get("ramal", "-")
        nome_val = dn_info.get("nome", "-")

        resultado.append({
            "pool": f"Pool {p_id}",
            "pool_id": p_id,
            "dn_id": dn_id,
            "mac": formatted_mac,
            "mac_address": formatted_mac,
            "ip": ip_val,
            "status": status_final,
            "ramal": ramal_val,
            "nome": nome_val,
        })

    # Caso não haja pools mas haja DNs cadastrados, lista os DNs
    if not resultado and dict_dns:
        for d_id, dn in sorted(dict_dns.items(), key=lambda x: int(x[0]) if str(x[0]).isdigit() else str(x[0])):
            resultado.append({
                "pool": "-",
                "pool_id": "-",
                "dn_id": d_id,
                "mac": "-",
                "mac_address": "-",
                "ip": "-",
                "status": "Offline",
                "ramal": dn.get("ramal", "-"),
                "nome": dn.get("nome", "-"),
            })

    return resultado


class CiscoCMEClient:
    """Cliente SSH para orquestração e gerenciamento de roteadores Cisco CME."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        secret: str = "",
        port: int = 22,
        timeout: int = 20,
    ) -> None:
        self.host = host.strip()
        self.username = username.strip()
        self.password = password
        self.secret = secret or password
        self.port = port
        self.timeout = timeout
        self.connection = None
        self.conectado = False

    def conectar(self) -> None:
        """Estabelece a sessão SSH com o roteador Cisco CME."""
        if ConnectHandler is None:
            raise RuntimeError("Netmiko não está instalado no ambiente.")

        device_params = {
            "device_type": "cisco_ios",
            "host": self.host,
            "username": self.username,
            "password": self.password,
            "secret": self.secret,
            "port": self.port,
            "timeout": self.timeout,
            "session_timeout": 60,
        }

        try:
            self.connection = ConnectHandler(**device_params)
            # Elevação para Privileged Exec (nível 15)
            try:
                self.connection.enable()
            except Exception as e_enable:
                logger.warning("Aviso ao tentar enable(): %s. Continuando com privilégio atual...", e_enable)
            self.conectado = True
            logger.info("Conexão SSH estabelecida com o roteador CME %s", self.host)
        except NetmikoAuthenticationException as e:
            self.conectado = False
            raise RuntimeError(f"Falha de autenticação no roteador CME: {e}") from e
        except NetmikoTimeoutException as e:
            self.conectado = False
            raise RuntimeError(f"Timeout ao conectar no IP {self.host}:{self.port}: {e}") from e
        except Exception as e:
            self.conectado = False
            raise RuntimeError(f"Erro ao conectar via SSH: {e}") from e

    def desconectar(self) -> None:
        """Encerra a conexão SSH de forma limpa."""
        if self.connection:
            try:
                self.connection.disconnect()
            except Exception:
                pass
        self.connection = None
        self.conectado = False
        logger.info("Conexão SSH com CME encerrada.")

    def obter_status_telefonia(self) -> List[Dict[str, Any]]:
        """
        Executa os comandos de diagnóstico para extrair todos os ramais e pools.
        Desativa a paginação com 'terminal length 0' para ler 100+ ramais sem truncamento.
        """
        if not self.conectado or not self.connection:
            raise RuntimeError("Não há conexão SSH ativa com o roteador CME.")

        # Desativa paginação para despejo contínuo sem prompt --More--
        try:
            self.connection.send_command("terminal length 0")
        except Exception as e:
            logger.warning("Falha ao configurar terminal length 0 no CME: %s", e)

        try:
            # 1. Tenta protocolo SIP (voice register)
            saida_show_dn = ""
            saida_show_pool = ""
            saida_status_sip = ""
            pool_operacional_output = ""
            pool_status_output = ""

            # Coleta de DNs (Configuração)
            comandos_dn = [
                "show run | section voice register dn",
                "show voice register dn",
                "show voice register dn brief",
            ]
            for cmd in comandos_dn:
                try:
                    res = self.connection.send_command(cmd, read_timeout=90)
                    if res and "% Invalid" not in res and "% Authorization" not in res and "% Incomplete" not in res and len(res.strip()) > 10:
                        saida_show_dn = res
                        break
                except Exception as e:
                    logger.warning("Erro no comando DN '%s': %s", cmd, e)

            # Coleta de Pools (Configuração: contém 'id mac' e 'number 1 dn X')
            comandos_pool_cfg = [
                "show run | section voice register pool",
                "show voice register pool",
                "show voice register all",
            ]
            for cmd in comandos_pool_cfg:
                try:
                    res = self.connection.send_command(cmd, read_timeout=90)
                    if res and "% Invalid" not in res and "% Authorization" not in res and "% Incomplete" not in res and len(res.strip()) > 10:
                        saida_show_pool = res
                        break
                except Exception as e:
                    logger.warning("Erro no comando Pool '%s': %s", cmd, e)

            # Coleta do Status Dinâmico SIP-UA (Ramal -> Contact IP): 'show sip-ua status registrar'
            try:
                raw_sip_ua = self.connection.send_command("show sip-ua status registrar", read_timeout=90)
                if "% Invalid" not in raw_sip_ua and "% Incomplete" not in raw_sip_ua:
                    saida_status_sip = raw_sip_ua
            except Exception as e:
                logger.warning("Falha ao executar show sip-ua status registrar: %s", e)

            # Coleta Operacional Secundária: 'show voice register pool'
            try:
                raw_op = self.connection.send_command("show voice register pool", read_timeout=90)
                if "% Invalid" not in raw_op and "% Incomplete" not in raw_op:
                    pool_operacional_output = raw_op
            except Exception as e:
                logger.warning("Falha ao executar show voice register pool operacional: %s", e)

            # ============================================================
            # DEPURAÇÃO REQUERIDA: Injeção de print raw antes do processamento
            # ============================================================
            print("DEBUG RAW DN:", repr(saida_show_dn))
            print("DEBUG RAW POOL (CFG):", repr(saida_show_pool))
            print("DEBUG RAW SIP-UA REGISTRAR:", repr(saida_status_sip))

            # Processamento SIP em 3 etapas relacionais: DNs, SIP-UA Status e Pools com Join
            qtd_pools, lista_sip = processar_dados_cme(saida_show_dn, saida_show_pool, saida_status_sip)

            if lista_sip:
                logger.info("CME: %d registro(s) SIP processados via processar_dados_cme com SIP-UA.", len(lista_sip))
                return lista_sip

            # 2. Fallback transparente para SCCP/Skinny (ephone) caso seja roteador SCCP
            ephone_dn = ""
            ephone_out = ""
            ephone_status = ""

            try:
                ephone_dn = self.connection.send_command("show run | section ephone-dn", read_timeout=90)
                if "% Invalid" in ephone_dn or "% Authorization" in ephone_dn or len(ephone_dn.strip()) < 10:
                    ephone_dn = self.connection.send_command("show ephone-dn", read_timeout=90)
            except Exception:
                ephone_dn = ""

            try:
                ephone_out = self.connection.send_command("show run | section ephone", read_timeout=90)
                if "% Invalid" in ephone_out or "% Authorization" in ephone_out or len(ephone_out.strip()) < 10:
                    ephone_out = self.connection.send_command("show ephone", read_timeout=90)
            except Exception:
                ephone_out = ""

            try:
                ephone_status = self.connection.send_command("show ephone summary", read_timeout=90)
                if "% Invalid" in ephone_status or not ephone_status.strip():
                    ephone_status = self.connection.send_command("show ephone brief", read_timeout=90)
            except Exception:
                ephone_status = ""

            print("DEBUG RAW EPHONE-DN:", repr(ephone_dn))
            print("DEBUG RAW EPHONE:", repr(ephone_out))

            dict_dns_sccp = extrair_dns_cme(ephone_dn)
            itens_sccp = extrair_pools_cme(ephone_out, ephone_status, dict_dns_sccp)
            if itens_sccp:
                logger.info("CME: %d registro(s) SCCP identificado(s).", len(itens_sccp))
                return itens_sccp

            return []
        finally:
            try:
                self.connection.send_command("terminal length 24")
            except Exception:
                pass

    def enviar_configuracoes(self, comandos: List[str]) -> str:
        """Aplica comandos de configuração no Cisco CME e salva na NVRAM."""
        if not self.conectado or not self.connection:
            raise RuntimeError("Não há conexão SSH ativa com o roteador CME.")

        if not comandos:
            return "Nenhum comando a aplicar."

        resultado = self.connection.send_config_set(comandos)
        try:
            self.connection.save_config()
        except Exception:
            pass
        return resultado
