#!/usr/bin/env python3
"""
Sourcing Triads App - Versión Limpia
Solo Google Sheets, código eficiente y limpio
"""

import streamlit as st
import pandas as pd
import json
import sys
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from google_sheets_exporter import export_to_google_sheets
import requests

# Configuración
st.set_page_config(
    page_title="Suna Solutions Proveedores IA",
    page_icon="🏭",
    layout="wide"
)

# SPREADSHEET_ID movido a google_sheets_exporter.py

def normalize_price(price_str) -> float:
    """
    Normalizar precios con diferentes formatos:
    - 1,50 (coma como decimal europeo) -> 1.50
    - 1.500,50 (punto miles, coma decimal europeo) -> 1500.50
    - 1,500.50 (coma miles, punto decimal americano) -> 1500.50
    - 1500 (entero) -> 1500.0
    - USD 1,50 -> 1.50
    - $1.50 -> 1.50
    """
    if not price_str or price_str in ['N/A', '', None, 'None']:
        return 0.0
        
    # Convertir a string y limpiar
    price_str = str(price_str).strip()
    
    # Remover símbolos de moneda y texto común
    import re
    # Remover símbolos de moneda, USD, EUR, etc.
    price_str = re.sub(r'[^\d,.\-]', '', price_str)
    
    # Manejar números negativos
    is_negative = price_str.startswith('-')
    if is_negative:
        price_str = price_str[1:]
    
    # Si está vacío después de limpiar
    if not price_str:
        return 0.0
    
    # Caso 1: Solo dígitos (sin comas ni puntos)
    try:
        if ',' not in price_str and '.' not in price_str:
            result = float(price_str)
            return -result if is_negative else result
    except:
        return 0.0
    
    # Caso 2: Solo un punto - determinar si es decimal o miles
    if ',' not in price_str and price_str.count('.') == 1:
        parts = price_str.split('.')
        if len(parts) == 2:
            # Si tiene exactamente 3 dígitos después del punto, probablemente sean miles (europeo)
            if len(parts[1]) == 3 and parts[1] == '000':
                try:
                    # "10.000" -> 10000 (formato europeo de miles)
                    result = float(parts[0]) * 1000
                    return -result if is_negative else result
                except:
                    pass
            # Si tiene máximo 2 decimales después, formato americano estándar
            elif len(parts[1]) <= 2:
                try:
                    result = float(price_str)
                    return -result if is_negative else result
                except:
                    pass
    
    # Caso 3: Solo una coma y máximo 2 dígitos después (formato europeo)
    if '.' not in price_str and price_str.count(',') == 1:
        parts = price_str.split(',')
        if len(parts) == 2 and len(parts[1]) <= 2:
            try:
                # Formato europeo: "1,50" -> 1.50
                result = float(price_str.replace(',', '.'))
                return -result if is_negative else result
            except:
                pass
        else:
            # Probablemente miles: "1,500" -> 1500
            try:
                result = float(price_str.replace(',', ''))
                return -result if is_negative else result
            except:
                pass
    
    # Caso 4: Ambos punto y coma presentes
    if ',' in price_str and '.' in price_str:
        last_comma_pos = price_str.rfind(',')
        last_dot_pos = price_str.rfind('.')
        
        if last_comma_pos > last_dot_pos:
            # Formato europeo: "1.500,50" (punto para miles, coma para decimal)
            try:
                # Quitar puntos (miles) y convertir coma a punto (decimal)
                clean_price = price_str.replace('.', '').replace(',', '.')
                result = float(clean_price)
                return -result if is_negative else result
            except:
                pass
        else:
            # Formato americano: "1,500.50" (coma para miles, punto para decimal)
            try:
                # Quitar comas (miles), mantener punto (decimal)
                clean_price = price_str.replace(',', '')
                result = float(clean_price)
                return -result if is_negative else result
            except:
                pass
    
    # Caso 5: Múltiples comas o puntos (separadores de miles)
    comma_count = price_str.count(',')
    dot_count = price_str.count('.')
    
    if comma_count > 1:
        # Múltiples comas, probablemente separadores de miles
        # Mantener solo la última si parece decimal
        parts = price_str.split(',')
        if len(parts[-1]) <= 2:
            # La última parte parece decimal
            clean_price = ''.join(parts[:-1]) + '.' + parts[-1]
        else:
            # Todas son separadores de miles
            clean_price = ''.join(parts)
        try:
            result = float(clean_price)
            return -result if is_negative else result
        except:
            pass
    
    if dot_count > 1:
        # Múltiples puntos, probablemente separadores de miles
        # Mantener solo el último si parece decimal
        parts = price_str.split('.')
        if len(parts[-1]) <= 2:
            # La última parte parece decimal
            clean_price = ''.join(parts[:-1]) + '.' + parts[-1]
        else:
            # Todos son separadores de miles
            clean_price = ''.join(parts)
        try:
            result = float(clean_price)
            return -result if is_negative else result
        except:
            pass
    
    # Fallback: intentar conversión directa
    try:
        result = float(price_str.replace(',', '.'))
        return -result if is_negative else result
    except:
        try:
            result = float(price_str.replace(',', ''))
            return -result if is_negative else result
        except:
            print(f"⚠️ No se pudo convertir precio: '{price_str}' -> fallback a 0.0") 
            return 0.0

def fix_alibaba_link(original_url: str) -> str:
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

# Clase GoogleSheetsManager removida - ahora se usa google_sheets_exporter.py


class SourcingAnalyzer:
    def __init__(self):
        self.data_path = Path("data")
        self.out_path = Path("out")
        # Crear directorios automáticamente
        self.data_path.mkdir(exist_ok=True)
        self.out_path.mkdir(exist_ok=True)
        
        # Importar scraper si está disponible
        try:
            # Primero intentar el scraper local (mejorado)
            from alibaba_scraper import AlibabaProductScraper
            self.scraper = AlibabaProductScraper()
            print("✅ Usando scraper mejorado local (alibaba_scraper.py)")
        except ImportError:
            try:
                # Fallback al scraper remoto
                sys.path.append('../amazon_hunt')
                from alibaba_scraper_clean import AlibabaProductScraper
                self.scraper = AlibabaProductScraper()
                print("⚠️ Usando scraper remoto (alibaba_scraper_clean.py)")
            except ImportError:
                self.scraper = None
                print("❌ No se pudo cargar ningún scraper")
        
    def load_scraper_data(self, query: str) -> Optional[List[Dict]]:
        """Cargar datos desde JSON o CSV"""
        json_file = self.data_path / f"{query}.json"
        csv_file = self.data_path / f"{query}.csv"
        
        if json_file.exists():
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                st.error(f"Error leyendo JSON: {e}")
                
        if csv_file.exists():
            try:
                df = pd.read_csv(csv_file, encoding='utf-8')
                # Si hay columnas de precios, normalizarlas
                price_columns = ['price', 'unit_price', 'unit_price_norm_usd', 'precio']
                for col in price_columns:
                    if col in df.columns:
                        st.info(f"🔧 Normalizando precios en columna: {col}")
                        df[col] = df[col].apply(lambda x: normalize_price(x) if not pd.isna(x) else 0.0)
                return df.to_dict('records')
            except Exception as e:
                st.error(f"Error leyendo CSV: {e}")
                
        return None
        
    def search_products_direct(self, query: str) -> Optional[List[Dict]]:
        """Buscar productos directamente usando el scraper"""
        if not self.scraper:
            st.error("❌ Scraper no disponible")
            return None
            
        st.info(f"🔍 Buscando '{query}' en Alibaba...")
        with st.spinner("Scrapeando productos..."):
            try:
                products = self.scraper.search_products(query)
                if products:
                    # Guardar datos en caché
                    try:
                        filename = self.data_path / f"{query}.json"
                        with open(filename, 'w', encoding='utf-8') as f:
                            json.dump(products, f, indent=2, ensure_ascii=False)
                        st.success(f"✅ Encontrados {len(products)} productos (guardado en caché)")
                    except Exception as e:
                        st.warning(f"⚠️ No se pudo guardar caché: {e}")
                        st.success(f"✅ Encontrados {len(products)} productos")
                    return products
            except Exception as e:
                st.error(f"❌ Error durante scraping: {e}")
        return None
        
    def _extract_product_image(self, product: Dict) -> str:
        """Extraer imagen del producto desde diferentes fuentes posibles - MEJORADO"""
        # Intentar desde diferentes campos de imagen
        image_sources = [
            'image_link', 'product_image', 'image_url', 'thumb_url', 'main_image',
            'first_image', 'thumbnail', 'preview_image'
        ]
        
        for source in image_sources:
            img_url = product.get(source)
            if img_url and img_url != 'null' and isinstance(img_url, str):
                # Limpiar y validar URL
                img_url = img_url.strip()
                if img_url.startswith('//'):
                    img_url = 'https:' + img_url
                elif img_url.startswith('/'):
                    img_url = 'https://www.alibaba.com' + img_url
                
                # Validar que sea una URL de imagen válida
                if img_url.startswith('http') and not 'placeholder' in img_url.lower() and not 'data:' in img_url:
                    return img_url
        
        # MÉTODO MEJORADO: Construir URL desde product_id con múltiples patrones
        product_id = product.get('product_id')
        if product_id:
            # Probar diferentes patrones de URL de Alibaba
            url_patterns = [
                f"https://s.alicdn.com/@sc04/kf/H{product_id}_220x220.jpg",
                f"https://s.alicdn.com/@sc01/kf/H{product_id}.jpg",
                f"https://sc01.alicdn.com/kf/H{product_id}.jpg",
                f"https://sc04.alicdn.com/kf/H{product_id}_220x220.jpg"
            ]
            # Devolver el primer patrón (el más común)
            return url_patterns[0]
        
        # NUEVO: Intentar construir desde título del producto
        title = product.get('product_title', '')
        if title:
            # Hash simple del título para generar URL consistente
            import hashlib
            title_hash = hashlib.md5(title.encode()).hexdigest()[:8]
            return f"https://s.alicdn.com/@sc04/kf/H{title_hash}_220x220.jpg"
        
        return ''  # Sin imagen

    def normalize_data(self, raw_products: List[Dict], fx_usd_ars: float = 0) -> pd.DataFrame:
        """Normalizar datos del scraper mejorado con nuevos campos"""
        normalized = []
        
        for product in raw_products:
            # Normalizar precio - usar nuevos campos si están disponibles
            raw_price = (product.get('price_max') or product.get('price') or 0)
            normalized_price = normalize_price(raw_price)
            
            # Mapear campos usando nuevos campos del scraper mejorado - DEFENSIVO
            mapped = {
                'title': product.get('product_title') or product.get('title', ''),
                'productUrl': product.get('product_url') or product.get('product_link', ''),
                'companyName': product.get('supplier_name') or product.get('seller_name', ''),
                'unit_price_norm_usd': normalized_price,
                'currency': product.get('currency', 'USD'),
                'moq': product.get('moq_value') or product.get('minimum_order', 1),
                'verified_supplier': product.get('supplier_verified') or product.get('is_supplier_verified', False),
                'supplier_rating': product.get('product_review_avg') or product.get('review_average', 0),  # RATING DEL PROVEEDOR
                'supplier_reviews_count': product.get('product_review_count') or product.get('amount_of_reviews', 0),  # REVIEWS DEL PROVEEDOR
                'image_link': self._extract_product_image(product),  # EXTRAER IMAGEN CORRECTAMENTE
                'amount_sold': product.get('sold_quantity') or product.get('amount_sold', 0),
                # Nuevos campos adicionales - DEFENSIVOS
                'price_min': product.get('price_min', normalized_price),
                'price_max': product.get('price_max', normalized_price),
                'moq_unit': product.get('moq_unit', 'piece'),
                'supplier_gold_level': product.get('supplier_gold_level', 0),
                'supplier_years': product.get('supplier_years', 0),
                'supplier_country': product.get('supplier_country_code', ''),
                'product_certifications': product.get('product_certifications', []),
                'est_delivery': product.get('est_delivery_by', ''),
                # CAMPOS ADICIONALES QUE PUEDEN EXISTIR O NO
                'supplier_profile_url': product.get('supplier_profile_url') or product.get('seller_link', ''),
            }
            normalized.append(mapped)
            
        df = pd.DataFrame(normalized)
        
        # Filtrar válidos
        df = df.dropna(subset=['unit_price_norm_usd'])  # Solo filtrar por precio, no por URL
        df = df[df['unit_price_norm_usd'] > 0]
        
        # Llenar valores faltantes
        df['moq'] = df['moq'].fillna(1)
        df['supplier_rating'] = df['supplier_rating'].fillna(0)  # Rating real del proveedor (0-5)
        df['supplier_reviews_count'] = df['supplier_reviews_count'].fillna(0)  # Reviews del proveedor
        df['productUrl'] = df['productUrl'].fillna('')  # Manejar URLs faltantes
        df['image_link'] = df['image_link'].fillna('')  # Manejar imágenes faltantes
        
        return df
        
    def calculate_landed_price(self, df: pd.DataFrame, multiplier: float = 3.0, fx_usd_ars: float = 0) -> pd.DataFrame:
        """Calcular precios landed"""
        df = df.copy()
        df['landed_est_usd'] = df['unit_price_norm_usd'] * multiplier
        
        if fx_usd_ars > 0:
            df['landed_est_ars'] = df['landed_est_usd'] * fx_usd_ars
            
        return df
        
    def calculate_triad(self, df: pd.DataFrame, min_reviews: int = 5) -> Dict:
        """Calcular tríada: Cheapest, Best Quality, Best Value - MEJORADO CON EVALUACIÓN DE PROVEEDOR"""
        if len(df) == 0:
            return {'cheapest': None, 'best_quality': None, 'best_value': None}
            
        used_indices = set()
        
        # CHEAPEST (sin cambios)
        cheapest_candidates = df.nsmallest(len(df), 'unit_price_norm_usd')
        cheapest = None
        for _, candidate in cheapest_candidates.iterrows():
            if candidate.name not in used_indices:
                cheapest = candidate
                used_indices.add(candidate.name)
                break
                
        # BEST QUALITY - MEJORADO: Evaluar calidad del proveedor, no solo reviews del producto
        df_quality = df.copy()
        
        # Score de calidad del proveedor - USANDO RATING REAL DEL PROVEEDOR
        supplier_scores = df_quality['verified_supplier'].astype(int) * 0.2  # Verificación
        supplier_scores += (df_quality['supplier_rating'].fillna(0) / 5.0) * 0.5  # RATING REAL DEL PROVEEDOR (0-5)
        
        # Reviews del proveedor (cantidad)
        if df_quality['supplier_reviews_count'].max() > 0:
            supplier_scores += (df_quality['supplier_reviews_count'].fillna(0) / df_quality['supplier_reviews_count'].max()) * 0.3
        
        # Agregar años de experiencia si está disponible
        if 'supplier_years' in df_quality.columns:
            supplier_scores += (df_quality['supplier_years'].fillna(0) / 20.0).clip(0, 1) * 0.2
            
        # Agregar cantidad vendida si está disponible  
        if 'amount_sold' in df_quality.columns and df_quality['amount_sold'].max() > 0:
            supplier_scores += (df_quality['amount_sold'].fillna(0) / df_quality['amount_sold'].max()) * 0.1
            
        df_quality['supplier_score'] = supplier_scores
        
        # Score del producto - SOLO CERTIFICACIONES (no hay reviews del producto, solo del proveedor)
        df_quality['product_score'] = 0.0  # Inicializar en 0
        
        # Score de certificaciones - DEFENSIVO
        if 'product_certifications' in df_quality.columns:
            df_quality['cert_score'] = df_quality['product_certifications'].apply(
                lambda x: min(len(x) / 3.0, 1.0) if isinstance(x, list) else 0
            )
        else:
            df_quality['cert_score'] = 0.0
        
        # Score total de calidad: Proveedor (60%) + Producto (30%) + Certificaciones (10%)
        df_quality['total_quality_score'] = (
            0.6 * df_quality['supplier_score'] +
            0.3 * df_quality['product_score'] +
            0.1 * df_quality['cert_score']
        )
        
        quality_candidates = df_quality.nlargest(len(df_quality), 'total_quality_score')
        best_quality = None
        for _, candidate in quality_candidates.iterrows():
            if candidate.name not in used_indices:
                best_quality = candidate
                used_indices.add(candidate.name)
                break
                
        # BEST VALUE - MEJORADO: Incluir calidad del proveedor
        df_value = df.copy()
        
        # Score de precio (invertido - menor precio = mejor score)
        if df_value['unit_price_norm_usd'].max() > df_value['unit_price_norm_usd'].min():
            price_range = df_value['unit_price_norm_usd'].max() - df_value['unit_price_norm_usd'].min()
            df_value['price_score'] = 1 - (
                (df_value['unit_price_norm_usd'] - df_value['unit_price_norm_usd'].min()) / price_range
            )
        else:
            df_value['price_score'] = 1.0
        
        # RATING REAL DEL PROVEEDOR para BEST VALUE
        supplier_scores_value = df_value['verified_supplier'].astype(int) * 0.2  # Verificación
        supplier_scores_value += (df_value['supplier_rating'].fillna(0) / 5.0) * 0.5  # RATING REAL DEL PROVEEDOR (0-5)
        
        # Reviews del proveedor
        if df_value['supplier_reviews_count'].max() > 0:
            supplier_scores_value += (df_value['supplier_reviews_count'].fillna(0) / df_value['supplier_reviews_count'].max()) * 0.3
        
        # Agregar campos opcionales si están disponibles
        if 'supplier_years' in df_value.columns:
            supplier_scores_value += (df_value['supplier_years'].fillna(0) / 20.0).clip(0, 1) * 0.2
        if 'amount_sold' in df_value.columns and df_value['amount_sold'].max() > 0:
            supplier_scores_value += (df_value['amount_sold'].fillna(0) / df_value['amount_sold'].max()) * 0.1
            
        df_value['supplier_score'] = supplier_scores_value
        
        df_value['product_quality_score'] = 0.0  # Sin reviews del producto, solo del proveedor
        
        if 'product_certifications' in df_value.columns:
            df_value['cert_score'] = df_value['product_certifications'].apply(
                lambda x: min(len(x) / 3.0, 1.0) if isinstance(x, list) else 0
            )
        else:
            df_value['cert_score'] = 0.0
        
        # Score de valor total: Precio (50%) + Proveedor (30%) + Producto (15%) + Certificaciones (5%)
        df_value['value_score'] = (
            0.5 * df_value['price_score'] +
            0.3 * df_value['supplier_score'] +
            0.15 * df_value['product_quality_score'] +
            0.05 * df_value['cert_score']
        )
        
        value_candidates = df_value.nlargest(len(df_value), 'value_score')
        best_value = None
        for _, candidate in value_candidates.iterrows():
            if candidate.name not in used_indices:
                best_value = candidate
                break
                
        return {
            'cheapest': cheapest,
            'best_quality': best_quality,
            'best_value': best_value
        }

def main_streamlit():
    
    analyzer = SourcingAnalyzer()
    # sheets_manager reemplazado por google_sheets_exporter.py
    
    # Sidebar profesional
    with st.sidebar:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea, #764ba2); 
                    padding: 1rem; border-radius: 10px; margin-bottom: 1rem;">
            <h2 style="color: white; text-align: center; margin: 0;">
                ⚙️ Panel de Control
            </h2>
        </div>
        """, unsafe_allow_html=True)
        
        # Solo búsqueda directa disponible
        search_mode = "🌐 Búsqueda directa"
        st.markdown("🔍 **Modo:** Búsqueda directa en Alibaba en tiempo real")
        
        # Input de queries - CON PERSISTENCIA
        if 'queries_input' not in st.session_state:
            st.session_state.queries_input = "licuadoras, hornos electricos"
            
        queries_input = st.text_area(
            "Búsquedas (separadas por coma)",
            value=st.session_state.queries_input,
            help="Ej: licuadoras, hornos electricos",
            key="queries_textarea"
        )
        
        # Actualizar session_state cuando cambie
        if queries_input != st.session_state.queries_input:
            st.session_state.queries_input = queries_input
        
        # Parámetros
        top_n = st.slider("Top N candidatos", 5, 50, 20)
        landed_multiplier = st.slider("Multiplicador Landed", 1.5, 5.0, 3.0, 0.1)
        fx_usd_ars = st.number_input("FX USD→ARS (opcional)", 0.0, 2000.0, 0.0)
        
        # NUEVOS FILTROS MEJORADOS
        st.subheader("🎯 Filtros de Calidad")
        require_verified = st.checkbox("Solo proveedores verificados", True, 
                                       help="Filtrar solo Gold Suppliers y proveedores autenticados")
        min_reviews_filter = st.slider("Mín. reviews requeridas", 0, 20, 1,
                                       help="Productos con menos reviews serán filtrados (0 = sin filtro)")
        
        # NUEVO: Filtro de certificaciones
        require_certifications = st.checkbox("Solo productos con certificaciones", False,
                                            help="Filtrar solo productos que tengan certificaciones (CE, CB, FCC, etc.)")
        
        if require_certifications:
            st.info("📋 Se mostrarán solo productos con certificaciones como CE, CB, FCC, RoHS, etc.")
        
        # Parámetros de tríada
        st.subheader("⚙️ Parámetros Tríada")
        min_reviews_quality = st.slider("Mín. reviews para Best Quality", 1, 50, 5,
                                        help="Mínimo de reviews para considerar en Best Quality")
        
        # Verificar Google Sheets (modo simplificado)
        try:
            # Verificar si existe archivo de credenciales
            from google_sheets_exporter import GoogleSheetsExporter
            test_exporter = GoogleSheetsExporter()
            sheets_enabled = test_exporter.initialize_client()
            
            if sheets_enabled:
                st.success("✅ Google Sheets conectado correctamente")
            else:
                st.warning("⚠️ Google Sheets no configurado - funcionando en modo solo lectura")
        except Exception as e:
            st.error(f"❌ Error Google Sheets: {e}")
            sheets_enabled = False
        
        st.subheader("📊 Información")
        st.info("🔍 **Búsqueda directa en Alibaba** - Scraping en tiempo real con Oxylabs")
        st.info("📋 **Exportación automática** a Google Sheets con fórmulas profesionales")
        st.info("🎯 **Filtros de calidad** - Proveedores verificados y certificaciones")
        
        # Mostrar datos persistidos
        if st.session_state.search_results:
            st.success(f"💾 **Datos guardados:** {', '.join(st.session_state.search_results.keys())}")
            if st.button("🗑️ Limpiar caché de búsquedas", help="Elimina todos los datos guardados"):
                st.session_state.clear()
                st.rerun()
        
    # Procesar queries
    queries = [q.strip() for q in queries_input.split(',') if q.strip()]
    
    if not queries:
        st.warning("⚠️ Por favor ingresa al menos una búsqueda")
        return
        
    st.header("📊 Resultados de Análisis")
    
    # Procesar cada query
    for query in queries:
        with st.expander(f"🔍 **{query.title()}**", expanded=True):
            
            # Búsqueda directa en Alibaba - CON PERSISTENCIA
            if st.button(f"🔍 Buscar '{query}' en Alibaba", key=f"search_{query}"):
                with st.spinner(f"🔍 Buscando '{query}' en Alibaba..."):
                    raw_data = analyzer.search_products_direct(query)
                    if raw_data:
                        # Guardar en session_state para persistir
                        st.session_state.search_results[query] = raw_data
                        st.success(f"✅ Encontrados {len(raw_data)} productos")
            
            # Verificar si hay datos en session_state
            if query in st.session_state.search_results:
                raw_data = st.session_state.search_results[query]
            else:
                raw_data = None
                        
            if not raw_data:
                st.info(f"👆 Haz click en el botón para buscar productos de '{query}'")
                continue
                
            st.info(f"📊 Analizando {len(raw_data)} productos de '{query}'...")
            
            # Normalizar datos - CACHEAR RESULTADOS
            cache_key = f"{query}_normalized"
            if cache_key not in st.session_state or len(raw_data) != st.session_state.get(f"{query}_raw_count", 0):
                st.info("🔧 Normalizando formatos de precios y extrayendo imágenes...")
                df = analyzer.normalize_data(raw_data, fx_usd_ars=fx_usd_ars)
                # Guardar en cache
                st.session_state[cache_key] = df
                st.session_state[f"{query}_raw_count"] = len(raw_data)
            else:
                df = st.session_state[cache_key]
            
            if len(df) == 0:
                st.error("❌ No hay productos válidos")
                continue
                
            # APLICAR FILTROS MEJORADOS
            original_count = len(df)
            df_filtered = df.copy()
            
            # Filtro por proveedores verificados
            if require_verified:
                df_verified = df_filtered[df_filtered['verified_supplier'] == True]
                verified_removed = len(df_filtered) - len(df_verified)
                if len(df_verified) > 0:
                    df_filtered = df_verified
                    if verified_removed > 0:
                        st.info(f"🔍 Filtrados {verified_removed} productos de proveedores no verificados")
                else:
                    st.warning("⚠️ No hay proveedores verificados. Mostrando todos.")
            
            # Filtro por reviews mínimas (del proveedor)
            if min_reviews_filter > 0:
                df_with_reviews = df_filtered[
                    (df_filtered['supplier_reviews_count'].notna()) & 
                    (df_filtered['supplier_reviews_count'] >= min_reviews_filter)
                ]
                reviews_removed = len(df_filtered) - len(df_with_reviews)
                if len(df_with_reviews) > 0:
                    df_filtered = df_with_reviews
                    if reviews_removed > 0:
                        st.info(f"🔍 Filtrados {reviews_removed} productos con proveedores con menos de {min_reviews_filter} reviews")
                else:
                    st.warning(f"⚠️ No hay productos con proveedores con {min_reviews_filter}+ reviews. Mostrando todos.")
            
            # NUEVO: Filtro por certificaciones - DEFENSIVO
            if require_certifications and 'product_certifications' in df_filtered.columns:
                df_with_certs = df_filtered[
                    df_filtered['product_certifications'].notna() & 
                    (df_filtered['product_certifications'].apply(lambda x: isinstance(x, list) and len(x) > 0))
                ]
                certs_removed = len(df_filtered) - len(df_with_certs)
                if len(df_with_certs) > 0:
                    df_filtered = df_with_certs
                    if certs_removed > 0:
                        # Mostrar estadísticas de certificaciones
                        all_certs = []
                        for cert_list in df_with_certs['product_certifications'].dropna():
                            if isinstance(cert_list, list):
                                all_certs.extend(cert_list)
                        unique_certs = list(set(all_certs))
                        st.info(f"🔍 Filtrados {certs_removed} productos sin certificaciones. "
                               f"Certificaciones encontradas: {', '.join(unique_certs[:5])}")
                else:
                    st.warning("⚠️ No hay productos con certificaciones. Mostrando todos.")
            elif require_certifications and 'product_certifications' not in df_filtered.columns:
                st.warning("⚠️ Los datos actuales no incluyen información de certificaciones.")
            
            # Mostrar estadísticas de filtrado
            if len(df_filtered) < original_count:
                filtered_count = len(df_filtered)
                st.success(f"✅ **{filtered_count}/{original_count} productos** pasaron los filtros de calidad "
                          f"({filtered_count/original_count*100:.1f}%)")
            else:
                st.info("📋 No se aplicaron filtros - mostrando todos los productos")
                
            # Calcular precios landed - CACHEAR CON PARÁMETROS
            landed_cache_key = f"{query}_landed_{landed_multiplier}_{fx_usd_ars}_{len(df_filtered)}"
            if landed_cache_key not in st.session_state:
                df_final = analyzer.calculate_landed_price(df_filtered, landed_multiplier, fx_usd_ars)
                st.session_state[landed_cache_key] = df_final
            else:
                df_final = st.session_state[landed_cache_key]
            
            # Top-N para análisis - CACHEAR
            topn_cache_key = f"{query}_topn_{top_n}_{len(df_final)}"
            if topn_cache_key not in st.session_state:
                df_top_n = df_final.nsmallest(top_n, 'unit_price_norm_usd')
                st.session_state[topn_cache_key] = df_top_n
            else:
                df_top_n = st.session_state[topn_cache_key]
            
            # Calcular tríada - CACHEAR
            triad_cache_key = f"{query}_triad_{min_reviews_quality}_{len(df_top_n)}"
            if triad_cache_key not in st.session_state:
                triad = analyzer.calculate_triad(df_top_n, min_reviews_quality)
                st.session_state[triad_cache_key] = triad
            else:
                triad = st.session_state[triad_cache_key]
            
            # Calcular estadísticas simples - CON RATING REAL DEL PROVEEDOR
            precio_promedio = df_final['unit_price_norm_usd'].mean()
            moq_promedio = df_final['moq'].mean()
            proveedores_verificados = df_final['verified_supplier'].sum()
            total_productos = len(df_final)
            proveedores_con_reviews = df_final[df_final['supplier_reviews_count'] > 0].shape[0]
            
            # Mostrar estadísticas simples - CORREGIDAS
            st.subheader("📊 Estadísticas de la Búsqueda")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("💰 Precio Promedio", f"${precio_promedio:,.2f}")
            with col2:
                st.metric("📦 MOQ Promedio", f"{moq_promedio:,.0f} pcs")
            with col3:
                rating_prov_promedio = df_final['supplier_rating'].mean()
                st.metric("⭐ Rating Proveedor", f"{rating_prov_promedio:.1f}/5")
            with col4:
                st.metric("📝 Con Reviews", f"{proveedores_con_reviews}/{total_productos}")
            
            # HEADER SIMPLIFICADO DE LA TRÍADA
            st.markdown("""
            <div style="text-align: center; margin: 1.5rem 0;">
                <h3 style="color: #333; margin-bottom: 0.5rem;">🏆 Top 3 Productos Recomendados</h3>
                <p style="color: #666; font-size: 0.9rem; margin: 0;">Selección automática basada en precio, calidad del proveedor y valor</p>
            </div>
            """, unsafe_allow_html=True)
            
            cols = st.columns(3)
            triad_types = [
                ('cheapest', '💰 MÁS BARATO', '#28a745', 'Precio más bajo del mercado'),
                ('best_quality', '⭐ MEJOR CALIDAD', '#007bff', 'Mejor proveedor por rating (gold level)'), 
                ('best_value', '💎 MEJOR VALOR', '#fd7e14', 'Mejor equilibrio precio-rating proveedor')
            ]
            
            for i, (key, title, color, description) in enumerate(triad_types):
                with cols[i]:
                    product = triad[key]
                    if product is not None:
                        # TARJETA SIMPLIFICADA Y MEJORADA
                        st.markdown(f"""
                        <div style="border: 2px solid {color}; border-radius: 10px; padding: 1rem; 
                                    background: white; margin-bottom: 1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                            <h3 style="color: {color}; text-align: center; margin: 0 0 0.5rem 0; font-size: 1.2rem;">
                                {title}
                            </h3>
                            <p style="color: #666; text-align: center; font-size: 0.85rem; margin: 0 0 1rem 0;">
                                {description}
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # IMÁGENES - SISTEMA MEJORADO CON FALLBACKS
                        img_url = product.get('image_link', '')
                        image_displayed = False
                        
                        if img_url and isinstance(img_url, str) and img_url.startswith('http'):
                            try:
                                st.image(img_url, width=180, caption="Imagen del producto")
                                image_displayed = True
                            except Exception as e:
                                # Intentar construir URL alternativa desde product_id
                                product_id = product.get('product_id')
                                if product_id:
                                    alt_url = f"https://s.alicdn.com/@sc04/kf/H{product_id}_220x220.jpg"
                                    try:
                                        st.image(alt_url, width=180, caption="Imagen del producto")
                                        image_displayed = True
                                    except:
                                        pass
                        
                        if not image_displayed:
                            # Mostrar placeholder informativo
                            st.markdown("""
                            <div style="width: 180px; height: 180px; border: 2px dashed #ccc; 
                                        display: flex; align-items: center; justify-content: center; 
                                        background: #f8f9fa; border-radius: 8px; margin: 0 auto;">
                                <span style="color: #666; text-align: center; font-size: 0.9rem;">
                                    📷<br/>Imagen no<br/>disponible
                                </span>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        # INFO SIMPLIFICADA Y CLARA
                        price_usd = product.get('unit_price_norm_usd', 0)
                        landed_usd = product.get('landed_est_usd', 0)
                        
                        # Cantidad simple
                        quantity = st.number_input(
                            f"Cantidad", 
                            min_value=1, 
                            value=max(1, int(product.get('moq', 1))), 
                            key=f"qty_{query}_{key}"
                        )
                        
                        total_cost = quantity * landed_usd
                        
                        # INFORMACIÓN CLAVE - LIMPIA Y CLARA
                        st.markdown(f"""
                        <div style="background: #f8f9fa; padding: 0.8rem; border-radius: 5px; margin: 0.5rem 0;">
                            <div style="margin-bottom: 0.3rem;"><strong>🏭 Proveedor:</strong><br/>{product.get('companyName', 'N/A')[:35]}</div>
                            <div style="margin-bottom: 0.3rem;"><strong>💵 Precio:</strong> <span style="color: {color}; font-weight: bold;">${price_usd:,.2f}</span></div>
                            <div style="margin-bottom: 0.3rem;"><strong>🚢 Landed:</strong> <span style="color: #dc3545; font-weight: bold;">${landed_usd:,.2f}</span></div>
                            <div style="margin-bottom: 0.3rem;"><strong>💰 Total:</strong> <span style="color: #28a745; font-weight: bold;">${total_cost:,.2f}</span></div>
                            <div style="margin-bottom: 0.3rem;"><strong>📦 MOQ:</strong> {int(product.get('moq', 0)):,} pcs</div>
                            <div style="margin-bottom: 0.3rem;"><strong>⭐ Rating Proveedor:</strong> {product.get('supplier_rating', 0):.1f}/5</div>
                            <div style="margin-bottom: 0.3rem;"><strong>📝 Reviews Proveedor:</strong> {int(product.get('supplier_reviews_count', 0)):,} reviews</div>
                        """, unsafe_allow_html=True)
                        
                        # INFO DEL PROVEEDOR ELIMINADA POR SOLICITUD DEL USUARIO
                        
                        # Certificaciones si existen
                        certifications = product.get('product_certifications', [])
                        if isinstance(certifications, list) and len(certifications) > 0:
                            cert_text = ', '.join(certifications[:3])
                            st.markdown(f"""
                            <div style="margin-bottom: 0.3rem;"><strong>🏷️ Certificaciones:</strong> {cert_text}</div>
                            """, unsafe_allow_html=True)
                        
                        st.markdown("</div>", unsafe_allow_html=True)
                        
                        # BOTÓN SIMPLIFICADO
                        product_url = fix_alibaba_link(product.get('productUrl', ''))
                        if product_url and "Link no disponible" not in product_url:
                            st.link_button(
                                "🔗 Ver en Alibaba", 
                                product_url,
                                use_container_width=True,
                                type="primary" if key == "cheapest" else "secondary"
                            )
                            
                    else:
                        st.markdown(f"""
                        <div style="border: 2px dashed #ccc; border-radius: 10px; padding: 1.5rem; 
                                    text-align: center; background: #f8f9fa;">
                            <h4 style="color: #666; margin: 0;">{title}</h4>
                            <p style="color: #999; margin: 0.5rem 0 0 0; font-size: 0.9rem;">No disponible</p>
                        </div>
                        """, unsafe_allow_html=True)
            
            # Tabla de productos con imágenes - TÍTULOS COMPLETOS
            st.subheader(f"📋 Top {len(df_top_n)} Productos")
            
            # TABLA CON RATING Y REVIEWS DEL PROVEEDOR
            required_cols = ['image_link', 'title', 'companyName', 'unit_price_norm_usd', 'landed_est_usd', 
                           'moq', 'supplier_rating', 'supplier_reviews_count', 'verified_supplier', 'productUrl']
            optional_cols = ['product_certifications', 'supplier_profile_url']
            
            # Solo usar columnas que realmente existen
            available_cols = required_cols.copy()
            for col in optional_cols:
                if col in df_top_n.columns:
                    available_cols.append(col)
                    
            display_df = df_top_n[available_cols].copy()
            
            # Agregar columnas faltantes como vacías si no existen
            if 'product_certifications' not in display_df.columns:
                display_df['product_certifications'] = [[] for _ in range(len(display_df))]
            if 'supplier_profile_url' not in display_df.columns:
                display_df['supplier_profile_url'] = ''
            if 'supplier_reviews_count' not in display_df.columns:
                display_df['supplier_reviews_count'] = 0
            
            # MANEJO DE IMÁGENES - MEJORADO PARA MOSTRAR DISPONIBLES
            def fix_image_url(row):
                img_url = row.get('image_link', '')
                if img_url and isinstance(img_url, str) and img_url.startswith('http') and 'placeholder' not in img_url.lower():
                    return img_url
                else:
                    return "https://via.placeholder.com/100x100?text=Sin+Imagen"  # Placeholder visible
            
            display_df['image_link'] = display_df.apply(fix_image_url, axis=1)
            
            # Crear títulos COMPLETOS sin truncar
            def create_full_title(row):
                title = str(row['title'])  # TÍTULO COMPLETO SIN TRUNCAR - ARREGLADO POR SOLICITUD DEL USUARIO
                return title
                
            display_df['📦 Producto'] = display_df.apply(create_full_title, axis=1)
            display_df['🏭 Proveedor'] = display_df['companyName'].str[:30] + '...'
            display_df['💰 Precio USD'] = display_df['unit_price_norm_usd'].apply(lambda x: f"${x:,.2f}")
            display_df['🚢 Landed USD'] = display_df['landed_est_usd'].apply(lambda x: f"${x:,.2f}")
            display_df['📦 MOQ'] = display_df['moq'].astype(int).apply(lambda x: f"{x:,}")
            display_df['⭐ Rating Proveedor'] = display_df['supplier_rating'].apply(lambda x: f"{x:.1f}/5" if x > 0 else "Sin rating")
            display_df['📝 Reviews Proveedor'] = display_df['supplier_reviews_count'].astype(int).apply(lambda x: f"{x:,} reviews" if x > 0 else "Sin reviews")
            display_df['✅ Verificado'] = display_df['verified_supplier'].map({True: '✅ Sí', False: '❌ No'})
            
            # Crear columna de certificaciones
            def format_certifications(row):
                certs = row.get('product_certifications', [])
                if isinstance(certs, list) and len(certs) > 0:
                    return ', '.join(certs[:3])  # Mostrar máximo 3 certificaciones
                return "Sin certificaciones"
            
            display_df['🏷️ Certificaciones'] = display_df.apply(format_certifications, axis=1)
            
            # Crear columna de link del proveedor
            def create_supplier_link_column(row):
                url = row.get('supplier_profile_url', '')
                if url and url != 'N/A':
                    return url
                return ""
                
            display_df['🏭 Link Proveedor'] = display_df.apply(create_supplier_link_column, axis=1)
            
            # Crear columna de link del producto
            def create_link_column(row):
                # Usar el campo correcto de URL del producto
                url = row.get('productUrl') or row.get('product_url') or row.get('product_link', '')
                url = fix_alibaba_link(url)
                if url and "Link no disponible" not in url:
                    return url  # Devolver solo la URL, no markdown
                return ""  # String vacío para links no disponibles
                
            display_df['🔗 Link Producto'] = display_df.apply(create_link_column, axis=1)
            
            # DataFrame final - CON RATING Y REVIEWS DEL PROVEEDOR CORRECTO
            final_df = display_df[[
                'image_link', '📦 Producto', '🏭 Proveedor', '✅ Verificado',
                '💰 Precio USD', '🚢 Landed USD', '📦 MOQ', 
                '⭐ Rating Proveedor', '📝 Reviews Proveedor', '🏷️ Certificaciones',
                '🏭 Link Proveedor', '🔗 Link Producto'
            ]].copy()
            final_df = final_df.rename(columns={'image_link': '📷 Imagen'})
            
            # Mostrar tabla - SIMPLIFICADA Y CLARIFICADA
            st.dataframe(
                final_df, 
                use_container_width=True,
                height=450,
                column_config={
                    "📷 Imagen": st.column_config.ImageColumn(
                        "📷 Imagen",
                        help="Imagen del producto extraída automáticamente",
                        width="small"
                    ),
                    "📦 Producto": st.column_config.TextColumn(
                        "📦 Producto",
                        help="Nombre completo del producto",
                        width="large"
                    ),
                    "⭐ Rating Proveedor": st.column_config.TextColumn(
                        "⭐ Rating Proveedor",
                        help="Rating real del proveedor (0-5 estrellas)",
                        width="small"
                    ),
                    "📝 Reviews Proveedor": st.column_config.TextColumn(
                        "📝 Reviews Proveedor",
                        help="Cantidad de reviews del proveedor",
                        width="small"
                    ),
                    "🏷️ Certificaciones": st.column_config.TextColumn(
                        "🏷️ Certificaciones",
                        help="Certificaciones del producto (CE, CB, FCC, etc.)",
                        width="medium"
                    ),
                    "🏭 Link Proveedor": st.column_config.LinkColumn(
                        "🏭 Link Proveedor",
                        help="Perfil del proveedor en Alibaba",
                        width="small"
                    ),
                    "🔗 Link Producto": st.column_config.LinkColumn(
                        "🔗 Link Producto",
                        help="Página del producto en Alibaba",
                        width="small"
                    )
                }
            )
            

            # Botón profesional para Google Sheets
            st.markdown("<div style='margin: 2rem 0; text-align: center;'>", unsafe_allow_html=True)
            if sheets_enabled:
                export_button = st.button(f"📋 Exportar '{query}' a Google Sheets", key=f"sheets_{query}", 
                                        help="Crear hoja profesional con análisis completo",
                                        type="primary")
                
                if export_button:
                    try:
                        with st.spinner("🔄 Creando análisis profesional en Google Sheets..."):
                            # Estadísticas básicas para Google Sheets
                            estadisticas_sheets = {
                                'precio_promedio': precio_promedio,
                                'moq_promedio': moq_promedio,
                                'rating_proveedor_promedio': rating_prov_promedio,
                                'proveedores_con_reviews': proveedores_con_reviews,
                                'proveedores_verificados': proveedores_verificados,
                                'total_productos': total_productos
                            }
                            
                            # Llamar función de exportación
                            from google_sheets_exporter import export_to_google_sheets
                            url = export_to_google_sheets(query, df_top_n, triad, estadisticas_sheets)
                            
                            if url:
                                st.balloons()
                                st.success("✅ ¡Datos exportados exitosamente a Google Sheets!")
                                st.markdown(f"🔗 **[Ver hoja creada]({url})**", unsafe_allow_html=True)
                                st.info(f"📊 Precio promedio: ${precio_promedio:,.2f} | 📦 MOQ promedio: {moq_promedio:,.0f} pcs | ⭐ Rating proveedor: {rating_prov_promedio:.1f}/5")
                            else:
                                st.error("❌ Error durante la exportación a Google Sheets")
                                
                    except Exception as e:
                        st.error(f"❌ Error exportando a Google Sheets: {str(e)}")
                        
            else:
                st.markdown("""
                <div style="background: #f8d7da; border: 1px solid #f5c6cb; 
                            border-radius: 8px; padding: 1rem; margin: 1rem 0;">
                    <p style="margin: 0; text-align: center;">
                        <strong>⚠️ Google Sheets no configurado</strong><br>
                        Configure las credenciales para habilitar la exportación profesional
                    </p>
                </div>
                """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
    
if __name__ == "__main__":
    main_streamlit()
