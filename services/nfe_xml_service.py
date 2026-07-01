"""Leitura simples de XML de NF-e para entrada de estoque.

A ideia aqui é não transformar o ERP em um sistema fiscal completo agora.
Nós extraímos apenas os dados úteis para estoque e financeiro:
fornecedor, número da NF, data de emissão e itens.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from typing import Any, Dict, List


@dataclass
class ItemNFe:
    codigo: str
    descricao: str
    ncm: str
    cfop: str
    unidade: str
    quantidade: float
    valor_unitario: float
    valor_total: float


@dataclass
class DadosNFe:
    numero: str
    serie: str
    chave: str
    data_emissao: str
    fornecedor_nome: str
    fornecedor_cnpj: str
    valor_total: float
    itens: List[ItemNFe]


def _texto_no(elemento: ET.Element | None, caminho: str, ns: Dict[str, str]) -> str:
    if elemento is None:
        return ""
    achado = elemento.find(caminho, ns)
    return (achado.text or "").strip() if achado is not None else ""


def _float_bruto(valor: str) -> float:
    try:
        return float(str(valor or "0").replace(",", "."))
    except Exception:
        return 0.0


def _data_nfe_para_br(data_iso: str) -> str:
    """Converte 2026-06-28T10:00:00-03:00 para 28/06/2026."""
    if not data_iso:
        return ""
    data = data_iso[:10]
    partes = data.split("-")
    if len(partes) == 3:
        return f"{partes[2]}/{partes[1]}/{partes[0]}"
    return data_iso


def ler_xml_nfe(conteudo_xml: bytes | str) -> Dict[str, Any]:
    """Lê um XML de NF-e e retorna dicionário pronto para uso no Streamlit."""
    if isinstance(conteudo_xml, bytes):
        raiz = ET.fromstring(conteudo_xml)
    else:
        raiz = ET.fromstring(conteudo_xml.encode("utf-8"))

    ns = {"nfe": "http://www.portalfiscal.inf.br/nfe"}

    # Alguns XMLs vêm com <nfeProc><NFe><infNFe>...</infNFe></NFe></nfeProc>
    # Outros vêm direto com <NFe><infNFe>...</infNFe></NFe>
    inf = raiz.find(".//nfe:infNFe", ns)
    if inf is None:
        raise ValueError("Não encontrei a tag infNFe. Confirme se o arquivo é um XML de NF-e válido.")

    chave = inf.attrib.get("Id", "").replace("NFe", "")
    ide = inf.find("nfe:ide", ns)
    emit = inf.find("nfe:emit", ns)
    total = inf.find("nfe:total/nfe:ICMSTot", ns)

    itens: List[ItemNFe] = []
    for det in inf.findall("nfe:det", ns):
        prod = det.find("nfe:prod", ns)
        if prod is None:
            continue
        quantidade = _float_bruto(_texto_no(prod, "nfe:qCom", ns))
        valor_total = _float_bruto(_texto_no(prod, "nfe:vProd", ns))
        valor_unitario = _float_bruto(_texto_no(prod, "nfe:vUnCom", ns))
        if valor_unitario == 0 and quantidade:
            valor_unitario = valor_total / quantidade

        itens.append(
            ItemNFe(
                codigo=_texto_no(prod, "nfe:cProd", ns),
                descricao=_texto_no(prod, "nfe:xProd", ns),
                ncm=_texto_no(prod, "nfe:NCM", ns),
                cfop=_texto_no(prod, "nfe:CFOP", ns),
                unidade=_texto_no(prod, "nfe:uCom", ns),
                quantidade=quantidade,
                valor_unitario=valor_unitario,
                valor_total=valor_total,
            )
        )

    dados = DadosNFe(
        numero=_texto_no(ide, "nfe:nNF", ns),
        serie=_texto_no(ide, "nfe:serie", ns),
        chave=chave,
        data_emissao=_data_nfe_para_br(_texto_no(ide, "nfe:dhEmi", ns) or _texto_no(ide, "nfe:dEmi", ns)),
        fornecedor_nome=_texto_no(emit, "nfe:xNome", ns),
        fornecedor_cnpj=_texto_no(emit, "nfe:CNPJ", ns) or _texto_no(emit, "nfe:CPF", ns),
        valor_total=_float_bruto(_texto_no(total, "nfe:vNF", ns)),
        itens=itens,
    )

    return {
        **asdict(dados),
        "itens": [asdict(item) for item in itens],
    }
