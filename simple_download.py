#!/usr/bin/env python3
"""
📥 DESCARGA SIMPLE - JSON Crudo API Alibaba
===========================================

Script minimalista para descargar SOLO el JSON crudo
sin análisis ni procesamiento.

Usage:
    python simple_download.py
"""

import json
import requests
from datetime import datetime
from pathlib import Path

def download_raw_json(query="licuadoras"):
    """Descarga JSON crudo para investigar parsing"""
    
    # Credenciales Oxylabs
    username = 'justo_eHMs7'
    password = 'Justo1234567_'
    base_url = "https://realtime.oxylabs.io/v1/queries"
    
    # Payload exacto que usa el scraper
    payload = {
        'source': 'alibaba_search',
        'user_agent_type': 'desktop_chrome',
        'render': 'html',
        'query': query
    }
    
    print(f"🔍 Descargando datos crudos para: {query}")
    
    try:
        # Llamada exacta a la API
        resp = requests.post(
            base_url,
            auth=(username, password),
            json=payload,
            timeout=120
        )
        resp.raise_for_status()
        
        # JSON CRUDO - sin procesar
        raw_data = resp.json()
        
        # Guardar con timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"raw_alibaba_{query.replace(' ', '_')}_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(raw_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ JSON crudo guardado: {filename}")
        print(f"📊 Tamaño: {len(json.dumps(raw_data)):,} caracteres")
        
        # Info básica
        if 'results' in raw_data and raw_data['results']:
            html_len = len(raw_data['results'][0].get('content', ''))
            print(f"📝 HTML content: {html_len:,} caracteres")
        
        return filename
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    # Descargar para query de ejemplo
    queries = ["licuadoras", "hornos electricos"]
    
    print("🚀 DESCARGA SIMPLE - JSON CRUDO")
    print("=" * 40)
    
    for query in queries:
        filename = download_raw_json(query)
        if filename:
            print(f"   {query} → {filename}")
        else:
            print(f"   {query} → ❌ FALLÓ")
        print()
    
    print("🎯 Revisa los archivos .json generados para investigar el problema!")
