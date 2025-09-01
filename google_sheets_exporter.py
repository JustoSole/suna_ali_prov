#!/usr/bin/env python3
"""
Google Sheets Exporter - Sourcing Triads
Manejo dedicado de exportación a Google Sheets con fórmulas correctas
"""

import gspread
from gspread.exceptions import APIError, SpreadsheetNotFound
from datetime import datetime
from pathlib import Path
import streamlit as st
from typing import Dict, List, Optional
import pandas as pd
import json

try:
    from config import get_google_sheets_spreadsheet_id, get_google_credentials
except ImportError:
    # Fallback para desarrollo local
    def get_google_sheets_spreadsheet_id():
        return "1rXxEqoDyGo5RIIowyvHjuIlKnJ18QjX7ewleY1PfI4w"
    def get_google_credentials():
        return None

class GoogleSheetsExporter:
    def __init__(self):
        self.client = None
        self.spreadsheet = None
        self.initialized = False
        
    def initialize_client(self):
        """Inicializar cliente de Google Sheets con manejo robusto"""
        try:
            # Primero intentar usar credenciales desde Streamlit secrets
            credentials = get_google_credentials()
            if credentials:
                try:
                    # Usar credenciales desde secrets.toml
                    self.client = gspread.service_account_from_dict(credentials)
                    self.initialized = True
                    return True
                except Exception as e:
                    st.error(f"❌ Error con credenciales de Google: {e}")
                    return False
            
            # Fallback: buscar archivos de credenciales locales
            possible_paths = [
                Path("config/google_credentials.json"),
                Path("../amazon_hunt/config/google_credentials.json"),
                Path("./amazon_hunt/config/google_credentials.json"),
                Path("amazon_hunt/config/google_credentials.json"),
                Path(".streamlit/google_credentials.json")
            ]
            
            credentials_path = None
            for path in possible_paths:
                if path.exists():
                    credentials_path = path
                    break
                    
            if credentials_path:
                self.client = gspread.service_account(filename=str(credentials_path))
                self.initialized = True
                return True
            else:
                st.error("⚠️ No se encontraron credenciales de Google (ni en secrets.toml ni archivos locales)")
                return False
        except Exception as e:
            st.error(f"❌ Error inicializando Google Sheets: {e}")
            return False
            
    def get_spreadsheet(self):
        """Obtener spreadsheet específico por ID"""
        try:
            if not self.client:
                return False
            spreadsheet_id = get_google_sheets_spreadsheet_id()
            self.spreadsheet = self.client.open_by_key(spreadsheet_id)
            return True
        except Exception as e:
            st.error(f"❌ Error abriendo spreadsheet: {e}")
            return False
            
    def create_worksheet_safe(self, title: str, rows: int = 100, cols: int = 14):
        """Crear worksheet de manera segura"""
        try:
            # Intentar crear nuevo worksheet
            worksheet = self.spreadsheet.add_worksheet(title=title, rows=rows, cols=cols)
            return worksheet
        except Exception as e:
            st.warning(f"⚠️ No se pudo crear worksheet '{title}': {e}")
            # Usar worksheet existente o crear con nombre único
            try:
                timestamp = datetime.now().strftime("%H%M%S")
                fallback_title = f"{title}_{timestamp}"
                worksheet = self.spreadsheet.add_worksheet(title=fallback_title, rows=rows, cols=cols)
                st.info(f"✅ Creado worksheet alternativo: {fallback_title}")
                return worksheet
            except Exception as fallback_error:
                st.error(f"❌ Error creando worksheet alternativo: {fallback_error}")
                return None

    def add_headers(self, worksheet, headers: List[str]):
        """Agregar headers de manera robusta"""
        try:
            # Método 1: Usar append_row (más confiable)
            worksheet.append_row(headers)
            st.info("📝 Headers agregados con append_row")
            return True
        except Exception as e1:
            try:
                # Método 2: Usar update_cell individual
                st.warning(f"⚠️ append_row falló ({e1}), intentando update_cell...")
                for col, header in enumerate(headers, start=1):
                    worksheet.update_cell(1, col, header)
                st.info("📝 Headers agregados con update_cell")
                return True
            except Exception as e2:
                st.error(f"❌ Error agregando headers: {e2}")
                return False

    def add_data_row(self, worksheet, row_data: List, row_number: int):
        """Agregar fila de datos de manera robusta"""
        try:
            # Método 1: Usar append_row
            worksheet.append_row(row_data)
            return True
        except Exception as e1:
            try:
                # Método 2: Usar update_cell individual
                st.warning(f"⚠️ append_row falló, usando update_cell...")
                for col, value in enumerate(row_data, start=1):
                    if value is not None and value != "":
                        worksheet.update_cell(row_number, col, value)
                return True
            except Exception as e2:
                st.error(f"❌ Error agregando fila {row_number}: {e2}")
                return False

    def add_formula_safe(self, worksheet, row: int, col: int, formula: str):
        """Agregar fórmula de manera segura usando update_cell SIN apóstrofe"""
        try:
            # CRUCIAL: Usar update_cell directamente para evitar apóstrofe automático
            # Este es el método que Google Sheets reconoce como fórmula ejecutable
            worksheet.update_cell(row, col, formula)
            return True
        except Exception as e:
            st.warning(f"⚠️ Error agregando fórmula en fila {row}, columna {col}: {e}")
            # Intentar método alternativo si update_cell falla
            try:
                # Fallback usando update con rango específico
                cell_range = self._get_cell_reference(row, col)
                worksheet.update(cell_range, formula)
                st.info(f"✅ Fórmula insertada con método alternativo en {cell_range}")
                return True
            except Exception as e2:
                st.error(f"❌ Error con método alternativo: {e2}")
                return False

    def _get_cell_reference(self, row: int, col: int) -> str:
        """Convertir números de fila/columna a referencia de celda (ej: 1,1 -> A1)"""
        column_letter = ""
        temp_col = col - 1  # Convertir a base 0
        while temp_col >= 0:
            column_letter = chr(65 + (temp_col % 26)) + column_letter
            temp_col = temp_col // 26 - 1
        return f"{column_letter}{row}"

    def format_headers_safe(self, worksheet, range_str: str):
        """Formatear headers de manera segura"""
        try:
            worksheet.format(range_str, {
                'textFormat': {'bold': True}, 
                'backgroundColor': {'red': 0.2, 'green': 0.7, 'blue': 0.9}
            })
            return True
        except Exception as e:
            st.warning(f"⚠️ No se pudo formatear headers: {e}")
            return False

    def adjust_column_width_safe(self, worksheet, col_start: int, col_end: int, width: int):
        """Ajustar ancho de columnas de manera segura"""
        try:
            # Intentar método moderno primero
            worksheet.columns_auto_resize(col_start, col_end)
            return True
        except Exception as e1:
            try:
                # Método alternativo usando formato
                range_str = f"{chr(64+col_start)}:{chr(64+col_end)}"  # A:B, etc
                worksheet.format(range_str, {"columnWidth": width})
                return True
            except Exception as e2:
                st.warning(f"⚠️ No se pudieron ajustar columnas {col_start}-{col_end}: {e2}")
                return False

    def export_triad_data(self, query_title: str, df_data: pd.DataFrame, triad_data: Dict, estadisticas: Dict = None):
        """Exportar datos de tríada con manejo de errores mejorado"""
        try:
            st.info(f"🔄 Iniciando exportación de '{query_title}' a Google Sheets...")
            
            if not self.initialized:
                st.info("🔐 Inicializando conexión a Google Sheets...")
                if not self.initialize_client():
                    st.error("❌ No se pudo inicializar Google Sheets")
                    return None
                    
            st.info("📊 Conectando con el spreadsheet...")
            if not self.get_spreadsheet():
                st.error("❌ No se pudo acceder al spreadsheet")
                return None
                
            # Crear nombre único para el worksheet
            sheet_name = f"{query_title}_{datetime.now().strftime('%m%d_%H%M')}"
            
            # Crear worksheet
            st.info(f"🔄 Creando hoja: {sheet_name}")
            worksheet = self.create_worksheet_safe(sheet_name, rows=100, cols=14)
            if not worksheet:
                return None
                
            st.success(f"✅ Hoja '{sheet_name}' creada exitosamente")
            
            # Headers profesionales sin emojis
            headers = [
                "IMAGEN", "PRODUCTO", "PROVEEDOR", "VERIFICADO", 
                "PRECIO_USD", "LANDED_USD", "CANTIDAD MINIMA PEDIDO", "RATING_PROVEEDOR", 
                "REVIEWS_PROVEEDOR", "CERTIFICACIONES", "LINK_PROVEEDOR", 
                "LINK_PRODUCTO", "CANTIDAD", "COSTO_TOTAL"
            ]
            
            # Agregar headers
            if not self.add_headers(worksheet, headers):
                return None
                
            # Preparar datos de la tríada
            triad_types = [('cheapest', '💰 MÁS BARATO'), ('best_quality', '⭐ MEJOR CALIDAD'), ('best_value', '💎 MEJOR VALOR')]
            current_row = 2
            
            st.info("📊 Agregando datos de tríada...")
            for key, title in triad_types:
                product = triad_data.get(key)
                if product is not None:
                    # Preparar datos
                    product_url = self._fix_alibaba_link(product.get('productUrl', ''))
                    image_url = product.get('image_link', '')
                    
                    # Certificaciones
                    certifications = product.get('product_certifications', [])
                    if isinstance(certifications, list) and len(certifications) > 0:
                        cert_text = ', '.join(certifications[:3])
                    else:
                        cert_text = "Sin certificaciones"
                    
                    # Link del proveedor
                    supplier_url = product.get('supplier_profile_url', '')
                    if not supplier_url or supplier_url == 'N/A':
                        supplier_url = ""
                    
                    # Fórmula de imagen con formato específico (CORRECTO con punto y coma)
                    if image_url and image_url.startswith('http'):
                        image_formula = f'=IMAGE("{image_url}"; 4; 100; 100)'
                    else:
                        image_formula = "Sin imagen"
                    
                    # Preparar fila de datos SIN la fórmula de imagen (se agregará por separado)
                    row_data = [
                        "",  # A: IMAGEN (se llenará con fórmula por separado)
                        str(product.get('title', ''))[:80] + ('...' if len(str(product.get('title', ''))) > 80 else ''),  # B: PRODUCTO  
                        str(product.get('companyName', ''))[:40] + ('...' if len(str(product.get('companyName', ''))) > 40 else ''),  # C: PROVEEDOR
                        "Sí" if product.get('verified_supplier') else "No",  # D: VERIFICADO
                        product.get('unit_price_norm_usd', 0),   # E: PRECIO_USD
                        product.get('landed_est_usd', 0),        # F: LANDED_USD
                        product.get('moq', 0),                   # G: CANTIDAD MINIMA PEDIDO
                        product.get('supplier_rating', 0),       # H: RATING_PROVEEDOR
                        product.get('supplier_reviews_count', 0), # I: REVIEWS_PROVEEDOR
                        cert_text,                               # J: CERTIFICACIONES
                        supplier_url,                            # K: LINK_PROVEEDOR
                        product_url,                             # L: LINK_PRODUCTO
                        1,                                       # M: CANTIDAD
                        ""  # N: COSTO_TOTAL (se llenará con fórmula)
                    ]
                    
                    # Agregar fila de datos
                    if self.add_data_row(worksheet, row_data, current_row):
                        # Agregar fórmula de imagen por separado (SIN apóstrofe)
                        if image_formula and image_formula != "Sin imagen":
                            self.add_formula_safe(worksheet, current_row, 1, image_formula)  # Columna A = 1
                        else:
                            worksheet.update_cell(current_row, 1, "Sin imagen")
                            
                        # Agregar fórmula de costo total = LANDED_USD * CANTIDAD (SIN apóstrofe)
                        formula_costo = f"=F{current_row}*M{current_row}"  # F = LANDED_USD, M = CANTIDAD
                        self.add_formula_safe(worksheet, current_row, 14, formula_costo)  # Columna N = 14
                        current_row += 1
                    
            # Agregar productos adicionales
            if not df_data.empty:
                st.info("📦 Agregando productos adicionales...")
                products_added = 0
                max_products = min(len(df_data), 15)
                
                for _, row in df_data.head(max_products).iterrows():
                    # Evitar duplicados de la tríada
                    if any(row.get('productUrl') == triad_data.get(key, {}).get('productUrl') 
                           for key in ['cheapest', 'best_quality', 'best_value']):
                        continue
                        
                    # Preparar datos del producto
                    product_url = self._fix_alibaba_link(row.get('productUrl', ''))
                    image_url = row.get('image_link', '')
                    
                    # Certificaciones
                    certifications = row.get('product_certifications', [])
                    if isinstance(certifications, list) and len(certifications) > 0:
                        cert_text = ', '.join(certifications[:3])
                    else:
                        cert_text = "Sin certificaciones"
                    
                    # Link del proveedor
                    supplier_url = row.get('supplier_profile_url', '')
                    if not supplier_url or supplier_url == 'N/A':
                        supplier_url = ""
                    
                    # Fórmula de imagen
                    if image_url and image_url.startswith('http'):
                        image_formula = f'=IMAGE("{image_url}"; 4; 100; 100)'
                    else:
                        image_formula = "Sin imagen"
                    
                    # Preparar fila de datos SIN la fórmula de imagen (se agregará por separado)
                    row_data = [
                        "",  # A: IMAGEN (se llenará con fórmula por separado)
                        str(row.get('title', ''))[:80] + ('...' if len(str(row.get('title', ''))) > 80 else ''),  # B: PRODUCTO
                        str(row.get('companyName', ''))[:40] + ('...' if len(str(row.get('companyName', ''))) > 40 else ''),  # C: PROVEEDOR
                        "Sí" if row.get('verified_supplier') else "No",  # D: VERIFICADO
                        row.get('unit_price_norm_usd', 0),       # E: PRECIO_USD
                        row.get('landed_est_usd', 0),            # F: LANDED_USD
                        row.get('moq', 0),                       # G: CANTIDAD MINIMA PEDIDO
                        row.get('supplier_rating', 0),           # H: RATING_PROVEEDOR
                        row.get('supplier_reviews_count', 0),    # I: REVIEWS_PROVEEDOR
                        cert_text,                               # J: CERTIFICACIONES
                        supplier_url,                            # K: LINK_PROVEEDOR
                        product_url,                             # L: LINK_PRODUCTO
                        1,                                       # M: CANTIDAD
                        ""  # N: COSTO_TOTAL (se llenará con fórmula)
                    ]
                    
                    # Agregar fila de datos
                    if self.add_data_row(worksheet, row_data, current_row):
                        # Agregar fórmula de imagen por separado (SIN apóstrofe)
                        if image_formula and image_formula != "Sin imagen":
                            self.add_formula_safe(worksheet, current_row, 1, image_formula)  # Columna A = 1
                        else:
                            worksheet.update_cell(current_row, 1, "Sin imagen")
                            
                        # Agregar fórmula de costo total = LANDED_USD * CANTIDAD (SIN apóstrofe)
                        formula_costo = f"=F{current_row}*M{current_row}"  # F = LANDED_USD, M = CANTIDAD
                        self.add_formula_safe(worksheet, current_row, 14, formula_costo)
                        current_row += 1
                        products_added += 1
                        
                        # Limitar para no exceder capacidad
                        if current_row >= 95:
                            break
                
                st.info(f"📊 Agregados {products_added} productos adicionales")
            
            # Formatear headers
            st.info("🎨 Aplicando formato...")
            self.format_headers_safe(worksheet, 'A1:N1')
            
            # Ajustar dimensiones de columnas de manera segura
            try:
                st.info("📏 Ajustando dimensiones de columnas...")
                self.adjust_column_width_safe(worksheet, 1, 1, 150)  # Columna A (IMAGEN)
                self.adjust_column_width_safe(worksheet, 2, 2, 300)  # Columna B (PRODUCTO)  
                self.adjust_column_width_safe(worksheet, 3, 3, 200)  # Columna C (PROVEEDOR)
                self.adjust_column_width_safe(worksheet, 7, 7, 200)  # Columna G (CANTIDAD MINIMA PEDIDO)
                self.adjust_column_width_safe(worksheet, 10, 12, 200)  # Columnas J-L (certificaciones y links)
            except Exception as dim_error:
                st.warning(f"⚠️ Algunas dimensiones no se pudieron ajustar: {dim_error}")
            
            st.success(f"✅ Hoja '{sheet_name}' creada exitosamente")
            st.info("🖼️ Imágenes y fórmulas aplicadas correctamente")
            
            # Obtener URL del spreadsheet completo
            spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{get_google_sheets_spreadsheet_id()}"
            return spreadsheet_url
            
        except Exception as e:
            st.error(f"❌ Error en exportación: {e}")
            # Mostrar error específico sin traceback completo para no romper la UI
            st.error(f"Detalles del error: {str(e)}")
            return None

    def _fix_alibaba_link(self, original_url: str) -> str:
        """Arreglar links para que funcionen en formato Alibaba correcto"""
        if not original_url or original_url == 'N/A':
            return "Link no disponible"
            
        # Si ya es el formato correcto, devolverlo
        if "alibaba.com/product-detail/" in original_url and ".html" in original_url:
            return original_url
            
        # Intentar extraer el product ID del link original
        import re
        product_id_match = re.search(r'(\d{10,})', original_url)
        
        if product_id_match:
            product_id = product_id_match.group(1)
            # Crear URL en el formato correcto
            fixed_url = f"https://www.alibaba.com/product-detail/Product_{product_id}.html?s=p"
            return fixed_url
        
        # Si no se puede arreglar, devolver el original
        return original_url

# Función de conveniencia para usar desde el script principal
def export_to_google_sheets(query_title: str, df_data: pd.DataFrame, triad_data: Dict, estadisticas: Dict = None):
    """Función de conveniencia para exportar a Google Sheets"""
    exporter = GoogleSheetsExporter()
    return exporter.export_triad_data(query_title, df_data, triad_data, estadisticas)

if __name__ == "__main__":
    print("🧪 Google Sheets Exporter - Prueba")
    print("Este script debe ser importado desde el script principal")
