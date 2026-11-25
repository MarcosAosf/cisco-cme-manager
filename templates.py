"""
Módulo de Templates de Comandos para Cisco CME (Communications Manager Express).
Gera listas de comandos padronizados para automação de roteadores de Voz Cisco (SIP e SCCP).
"""

from typing import List, Union


class CiscoCMETemplates:
    """Templates certificados de comandos Cisco IOS para telefonia CME."""

    @staticmethod
    def get_pool_reset(pool_id: Union[str, int]) -> List[str]:
        """
        Retorna a lista de comandos para forçar o reset de um aparelho VoIP SIP.
        """
        p_id = str(pool_id).strip()
        p_num = "".join(ch for ch in p_id if ch.isdigit()) or p_id
        return [
            f"voice register pool {p_num}",
            "reset",
            "exit",
        ]

    @staticmethod
    def get_ephone_reset(ephone_id: Union[str, int]) -> List[str]:
        """
        Retorna a lista de comandos para forçar o restart de um aparelho VoIP SCCP/Skinny.
        """
        e_id = str(ephone_id).strip()
        e_num = "".join(ch for ch in e_id if ch.isdigit()) or e_id
        return [
            f"ephone {e_num}",
            "restart",
            "exit",
        ]

    @staticmethod
    def get_dn_name_config(dn_id: Union[str, int], novo_nome: str) -> List[str]:
        """
        Retorna a lista de comandos para alterar a descrição / Caller-ID de um ramal SIP.
        """
        d_id = str(dn_id).strip()
        d_num = "".join(ch for ch in d_id if ch.isdigit()) or d_id
        nome_limpo = novo_nome.strip().replace('"', "")
        return [
            f"voice register dn {d_num}",
            f'name "{nome_limpo}"',
            "exit",
        ]

    @staticmethod
    def get_ephone_dn_name_config(dn_id: Union[str, int], novo_nome: str) -> List[str]:
        """
        Retorna a lista de comandos para alterar a descrição / Caller-ID de um ramal SCCP.
        """
        d_id = str(dn_id).strip()
        d_num = "".join(ch for ch in d_id if ch.isdigit()) or d_id
        nome_limpo = novo_nome.strip().replace('"', "")
        return [
            f"ephone-dn {d_num}",
            f'name "{nome_limpo}"',
            "exit",
        ]

    @staticmethod
    def get_bulk_pool_reset(pool_ids: List[Union[str, int]]) -> List[str]:
        """
        Retorna lista de comandos para reset em lote de múltiplos pools SIP.
        """
        cmds: List[str] = []
        for pid in pool_ids:
            cmds.extend(CiscoCMETemplates.get_pool_reset(pid))
        return cmds
