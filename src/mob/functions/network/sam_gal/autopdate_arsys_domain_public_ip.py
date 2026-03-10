from __future__ import annotations

from typing import Any, Dict, List, Tuple
import xml.etree.ElementTree as ET
import base64
import httpx

# Configuración de la API de Arsys según el manual
ARSYS_API_URL = "https://api.servidoresdns.net:54321/hosting/api/soap/index.php"


async def get_public_ip() -> str:
    """Obtiene la IP pública actual del host."""
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.ipify.org?format=json")
        return response.json()["ip"]


def get_auth_header(login: str, key: str) -> Dict[str, str]:
    """Genera el encabezado de autenticación Basic."""
    auth_str = f"{login}:{key}"
    encoded = base64.b64encode(auth_str.encode()).decode()
    return {"Authorization": f"Basic {encoded}"}


async def call_arsys_soap(method: str, input_xml: str, environment: Dict[str, Any]) -> str:
    """Realiza una llamada SOAP a la API de Arsys."""
    login = environment.get("arsys_api_login")
    key = environment.get("arsys_api_key")

    headers = get_auth_header(login, key)
    headers["Content-Type"] = "text/xml; charset=utf-8"

    # Construcción del sobre SOAP según ejemplos del manual
    envelope = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ns="{method}">
   <soapenv:Header/>
   <soapenv:Body>
      <ns:{method}>
         <input>{input_xml}</input>
      </ns:{method}>
   </soapenv:Body>
</soapenv:Envelope>"""

    async with httpx.AsyncClient() as client:
        response = await client.post(ARSYS_API_URL, content=envelope, headers=headers, timeout=30.0)
        return response.text


def parse_arsys_dns_response(xml_content: str) -> Tuple[List[Dict[str, str]] | None, List[Dict[str, str]] | None]:
    """
    Parsea el XML de Arsys y devuelve una lista de diccionarios con
    la información de cada entrada DNS (name, type, value) y un listado de los elementos <errorCode> detectados.
    En caso de haber algun error con valor diferente a 0, se imprimirá el error y se devolverá None.
    """
    # Definición de namespaces para el parsing
    namespaces = {
        'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
        'soap-enc': 'http://schemas.xmlsoap.org/soap/encoding/',
        'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
    }

    try:
        root = ET.fromstring(xml_content)
        # Buscamos todos los elementos <item> dentro de la estructura
        # El camino es: Body -> InfoDNSZoneResponse -> return -> res -> data -> item
        items = root.findall(".//item", namespaces)
        # Buscamos todos los elementos <errorCode> con valor diferente a 0 para detectar errores
        error_codes = root.findall(".//errorCode", namespaces)
        for error in error_codes:
            if error.text != "0":
                return None, error.text

        dns_records = []
        for item in items:
            name = item.find("name").text if item.find("name") is not None else ""
            record_type = item.find("type").text if item.find("type") is not None else ""
            value = item.find("value").text if item.find("value") is not None else ""

            dns_records.append({
                "name": name,
                "type": record_type,
                "value": value
            })
        return dns_records, None
    except Exception as e:
        return None, None


async def call_arsys_soap_info_dns_zone(domain_name: str, environment: Dict[str, Any]) -> List[Dict[str, str]] | None:
    """Llama a la función InfoDNSZone de Arsys para obtener las entradas DNS de un dominio."""
    input_xml = f"<domain>{domain_name}</domain>"
    response_xml = await call_arsys_soap("InfoDNSZone", input_xml, environment)
    data, errors = parse_arsys_dns_response(response_xml)
    if errors:
        return None
    return data


async def check(*, environment: Dict[str, Any], payload: Dict[str, Any]) -> bool:
    """
    Verifica si la IP pública coincide con la configurada en Arsys.
    """
    domain = environment.get("domain")
    records_to_update = environment.get("records", [])
    try:
        public_ip = await get_public_ip()

        response_records = await call_arsys_soap_info_dns_zone(domain, environment)
        if response_records is None:
            return False
        for record_name in records_to_update:
            if any(record for record in response_records if record["name"] == record_name and record["type"] == "A" and record["value"] != public_ip):
                return False
        return True

    except Exception as e:
        raise Exception(f"Error al verificar la IP: {str(e)}")


async def run(*, environment: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Actualiza la IP en Arsys cuando el check devuelve False
    """
    domain = environment.get("domain")
    records_to_update = environment.get("records", [])
    try:
        public_ip = await get_public_ip()

        response_records = await call_arsys_soap_info_dns_zone(domain, environment)
        if not response_records:
            return {
                "success": False,
                "message": "No se pudieron obtener las entradas DNS del dominio."
            }
        for record_name in records_to_update:
            current_record = next((record for record in response_records if record["name"] == record_name and record["type"] == "A"), None)
            if not current_record:
                continue  # Si no se encuentra la entrada, se omite
            current_val = current_record["value"]
            input_xml = f"""
                <domain>{domain}</domain>
                <dns>{record_name}</dns>
                <currenttype>A</currenttype>
                <currentvalue>{current_val}</currentvalue>
                <newvalue>{public_ip}</newvalue>
            """
            response_xml = await call_arsys_soap("ModifyDNSEntry", input_xml, environment)
            response_confirmation = parse_arsys_dns_response(response_xml)
            if not response_confirmation:
                continue

        return {
            "success": True,
            "message": f"IPs actualizadas correctamente a {public_ip}."
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error al actualizar la IP: {str(e)}"
        }
