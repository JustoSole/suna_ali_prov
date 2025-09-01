#!/usr/bin/env python3
import requests
import json
import re
import argparse
import sys
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
import logging
from collections import defaultdict

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# -------------------------
# Utilidades de parsing numérico
# -------------------------
def parse_int_any(text: str):
    """Convierte '2.506', '2,506', '1.5k', '1,5k', '2M' etc. a int (aprox)."""
    if text is None:
        return None
    t = str(text).strip().lower()

    # k / m
    m = re.search(r'([\d.,]+)\s*([km])\b', t)
    if m:
        base = m.group(1)
        mult = m.group(2)
        # normalizo decimal a punto
        base = base.replace('.', '').replace(',', '.')
        try:
            val = float(base)
            if mult == 'k':
                return int(round(val * 1_000))
            if mult == 'm':
                return int(round(val * 1_000_000))
        except:
            pass

    # Caso general: quito todo lo no-dígito
    digits = re.sub(r'\D', '', t)
    if digits.isdigit():
        try:
            return int(digits)
        except:
            return None
    return None

def extract_first_number(text: str):
    """Devuelve el primer número (float) que aparezca, intentando respetar formatos 1.234,56 / 1,234.56."""
    if not text:
        return None
    # candidatos
    tokens = re.findall(r'[\d.,]+', text)
    for tok in tokens:
        # heurística: si tiene coma y punto, el último separador es decimal
        if ',' in tok and '.' in tok:
            last_comma = tok.rfind(',')
            last_dot = tok.rfind('.')
            if last_comma > last_dot:
                # decimal = coma
                val = tok.replace('.', '').replace(',', '.')
            else:
                # decimal = punto
                val = tok.replace(',', '')
        elif ',' in tok:
            # si hay coma, suele ser decimal o miles. para robustez,
            # si hay 3 dígitos tras coma -> probablemente miles => quito coma
            parts = tok.split(',')
            if len(parts[-1]) == 3:
                val = tok.replace(',', '')
            else:
                val = tok.replace(',', '.')
        else:
            # solo puntos -> normalmente miles en ES => quito todos
            val = tok.replace('.', '')
        try:
            return float(val)
        except:
            continue
    return None

def parse_number_en(s):
    """Convierte un número estilo en-US: quita comas de miles y usa punto como decimal."""
    if s is None:
        return None
    s = str(s).strip()
    s = s.replace(',', '')  # 1,234.56 -> 1234.56
    m = re.search(r'-?\d+(?:\.\d+)?', s)
    return float(m.group(0)) if m else None

def _parse_num_token(token: str):
    """
    Convierte tokens tipo:
      '1,299.50' -> 1299.50
      '1.299,50' -> 1299.50
      '1.200'    -> 1200      (punto = miles)
      '8.5'      -> 8.5       (punto = decimal)
      '12,34'    -> 12.34     (coma = decimal)
    """
    if token is None:
        return None
    t = token.strip()
    # Caso con ambos separadores: decide por el ÚLTIMO separador como decimal
    if ',' in t and '.' in t:
        last_comma = t.rfind(',')
        last_dot = t.rfind('.')
        if last_comma > last_dot:
            # decimal = ',', puntos como miles
            t = t.replace('.', '').replace(',', '.')
        else:
            # decimal = '.', comas como miles
            t = t.replace(',', '')
        try:
            return float(t)
        except:
            return None

    # Solo comas
    if ',' in t:
        parts = t.split(',')
        if len(parts[-1]) == 3 and len(parts) >= 2:
            # '1,200' => miles
            t = t.replace(',', '')
        else:
            # '12,34' => decimal europeo
            t = t.replace(',', '.')
        try:
            return float(t)
        except:
            return None

    # Solo puntos
    if '.' in t:
        parts = t.split('.')
        # Múltiples puntos y el último grupo de 3 => miles
        if len(parts) > 2 and len(parts[-1]) == 3:
            t = t.replace('.', '')
            try:
                return float(t)
            except:
                return None
        # Un solo punto: si el grupo final tiene 3 dígitos, probablemente es miles
        if len(parts) == 2 and len(parts[1]) == 3:
            t = t.replace('.', '')
            try:
                return float(t)
            except:
                return None
        # Si el grupo final tiene 1-2 dígitos, probablemente es decimal
        if len(parts) == 2 and len(parts[1]) in [1, 2]:
            try:
                return float(t)
            except:
                return None
        # En lo demás, trátalo como decimal
        try:
            return float(t)
        except:
            return None

    # Sin separadores
    try:
        return float(t)
    except:
        return None


def extract_price_range_smart(text_or_area: str):
    """
    Extrae TODAS las cifras de precio de una cadena (DOM o areaContent),
    normaliza miles/decimales y devuelve lista ordenada.
    """
    if not text_or_area:
        return []
    nums = []
    # Toma tokens numéricos con posibles separadores
    for tok in re.findall(r'[\d][\d.,]*', text_or_area):
        val = _parse_num_token(tok)
        if val is not None:
            nums.append(val)
    # De-dup + sort
    return sorted(set(nums))

def max_price_from_areacontent(area):
    """
    area: e.g., '$11-13', 'US $1.200-1.350', '$8.5', '€12,34-€15,00'
    Estrategia: usar el nuevo parser inteligente y devolver el máximo.
    """
    prices = extract_price_range_smart(area)
    return max(prices) if prices else None

def extract_alibaba_products_from_cards(html):
    """
    Extrae productos usando el método de tarjetas individuales según la guía.
    Cada tarjeta contiene toda la info de un producto/proveedor sin mezclar datos.
    """
    soup = BeautifulSoup(html, 'html.parser')
    products = []
    
    # Buscar tarjetas de resultados (varios formatos posibles)
    card_selectors = [
        '.fy23-search-card.m-gallery-product-item-v2.J-search-card-wrapper',
        '.m-gallery-product-item-v2',
        '.J-search-card-wrapper',
        '.search-card-wrapper',
        '.searchx-offer-item'
    ]
    
    cards = []
    for selector in card_selectors:
        cards = soup.select(selector)
        if cards:
            logger.info(f"Found {len(cards)} product cards using selector: {selector}")
            break
    
    if not cards:
        logger.warning("No product cards found with any selector")
        return []
    
    for i, card in enumerate(cards):
        try:
            product = extract_product_from_card(card)
            if product:
                products.append(product)
        except Exception as e:
            logger.warning(f"Error extracting product from card {i}: {e}")
            continue
    
    logger.info(f"Successfully extracted {len(products)} products from {len(cards)} cards")
    return products

def extract_product_from_card(card):
    """Extrae todos los datos de un producto desde una tarjeta individual"""
    product = {
        'product_id': None,
        'product_title': None,
        'product_url': None,
        'price_min': None,
        'price_max': None,
        'price': None,
        'currency': None,
        'moq_value': None,
        'moq_unit': None,
        'sold_quantity': None,
        'product_review_avg': None,
        'product_review_count': None,
        'product_certifications': [],
        'product_cert_icon_urls': [],
        'est_delivery_by': None,
        'has_easy_return': False,
        'has_add_to_cart': False,
        'has_chat_now': False,
        'has_add_to_compare': False,
        'has_add_to_favorites': False,
        'supplier_name': None,
        'supplier_profile_url': None,
        'supplier_verified': False,
        'supplier_gold_level': 0,
        'supplier_years': None,
        'supplier_country_code': None,
        'image_link': None
    }
    
    # 1) Enlaces y título del producto
    detail_link = card.select_one('a.search-card-e-detail-wrapper[href]')
    if detail_link:
        href = detail_link.get('href', '')
        if href:
            if href.startswith('//'):
                href = 'https:' + href
            elif href.startswith('/'):
                href = 'https://www.alibaba.com' + href
            product['product_url'] = href
            
        # Extraer product_id de la URL
        if href:
            id_match = re.search(r'(\d{8,})', href)
            if id_match:
                product['product_id'] = id_match.group(1)
    
    # Título del producto
    title_elem = card.select_one('[data-spm="d_title"] a, h2 a, .search-card-e-title a')
    if title_elem:
        title = title_elem.get_text(strip=True)
        title = re.sub(r'<[^>]+>', '', title)  # Limpiar HTML
        product['product_title'] = title
    
    # 2) Precio y moneda - MEJORADO con parser inteligente
    price_elem = card.select_one('.search-card-e-price-main')
    if price_elem:
        price_text = price_elem.get_text(strip=True)
        prices = extract_price_range_smart(price_text)
        if prices:
            if len(prices) == 1:
                product['price'] = prices[0]
                product['price_min'] = prices[0]
                product['price_max'] = prices[0]
            else:
                product['price'] = max(prices)
                product['price_min'] = min(prices)
                product['price_max'] = max(prices)
        
        # Detectar moneda
        if '€' in price_text:
            product['currency'] = 'EUR'
        elif '$' in price_text or 'USD' in price_text.upper():
            product['currency'] = 'USD'
        else:
            product['currency'] = 'USD'  # Por defecto
    
    # 3) MOQ (pedido mínimo)
    moq_elem = card.select_one('[data-aplus-auto-card-mod*="area=moq"]')
    if moq_elem:
        moq_text = moq_elem.get_text(strip=True)
        moq_match = re.search(r'min\.?\s*order:?\s*([\d,\.]+)\s*(\w+)', moq_text, re.IGNORECASE)
        if moq_match:
            moq_val = parse_int_any(moq_match.group(1))
            if moq_val:
                product['moq_value'] = float(moq_val)
                product['moq_unit'] = normalize_unit(moq_match.group(2))
    
    # 4) Cantidad vendida
    sold_elem = card.select_one('[data-aplus-auto-card-mod*="soldQuantity"]')
    if sold_elem:
        area_content = sold_elem.get('data-aplus-auto-card-mod', '')
        content_match = re.search(r'areaContent=(\d+)', area_content)
        if content_match:
            try:
                product['sold_quantity'] = int(content_match.group(1))
            except:
                pass
        else:
            # Fallback: buscar en el texto
            sold_text = sold_elem.get_text(strip=True)
            sold_match = re.search(r'(\d+)\s*sold', sold_text, re.IGNORECASE)
            if sold_match:
                try:
                    product['sold_quantity'] = int(sold_match.group(1))
                except:
                    pass
    
    # 5) Reviews del producto - MEJORADO: solo reviews de producto, no del proveedor
    review_elem = card.select_one('span.search-card-e-review[data-aplus-auto-card-mod*="area=review"]')
    if not review_elem:
        # Fallback con selector más amplio pero dentro del card
        review_elem = card.select_one('[data-aplus-auto-card-mod*="area=review"]')
    
    if review_elem:
        area_content = review_elem.get('data-aplus-auto-card-mod', '')
        content_match = re.search(r'areaContent=([^&]+)', area_content)
        if content_match:
            review_data = content_match.group(1)
            if '@@' in review_data:
                rating_str, count_str = (review_data.split('@@') + [None, None])[:2]
                try:
                    product['product_review_avg'] = float((rating_str or '').replace(',', '.'))
                except:
                    product['product_review_avg'] = None
                try:
                    product['product_review_count'] = int(re.sub(r'\D', '', count_str or '') or 0)
                except:
                    product['product_review_count'] = None
    
    # 6) Certificaciones del producto
    cert_icons = card.select('img.search-card-e-icon__certification')
    if cert_icons:
        certs = []
        cert_urls = []
        for icon in cert_icons:
            alt = icon.get('alt', '').strip()
            src = icon.get('src', '').strip()
            if alt:
                certs.append(alt)
            if src:
                cert_urls.append(src)
        product['product_certifications'] = certs
        product['product_cert_icon_urls'] = cert_urls
    
    # 7) Entrega estimada y características
    delivery_elem = card.select_one('[data-aplus-auto-card-mod*="area=deliveryBy"]')
    if delivery_elem:
        delivery_text = delivery_elem.get_text(strip=True)
        product['est_delivery_by'] = delivery_text
    
    # Características booleanas
    product['has_easy_return'] = bool(card.select_one('[data-aplus-auto-card-mod*="easy_return"]'))
    
    # Usar búsqueda de texto en lugar de :contains deprecated
    card_text = card.get_text()
    product['has_add_to_cart'] = 'Add to cart' in card_text
    product['has_chat_now'] = 'Chat now' in card_text
    product['has_add_to_compare'] = 'Add to compare' in card_text
    product['has_add_to_favorites'] = 'Add to Favorites' in card_text
    
    # 8) Información del proveedor
    supplier_elem = card.select_one('a.search-card-e-company')
    if supplier_elem:
        product['supplier_name'] = supplier_elem.get_text(strip=True)
        href = supplier_elem.get('href', '')
        if href:
            if href.startswith('//'):
                href = 'https:' + href
            elif href.startswith('/'):
                href = 'https://www.alibaba.com' + href
            product['supplier_profile_url'] = href
    
    # 9) Verificación y años del proveedor
    product['supplier_verified'] = bool(card.select_one('.verified-supplier-icon__wrapper img.verified-supplier-icon'))
    
    # Años como proveedor y país
    years_elem = card.select_one('a.search-card-e-supplier__year')
    if years_elem:
        years_text = years_elem.get_text(strip=True)
        years_match = re.search(r'(\d+)\s*yrs?', years_text, re.IGNORECASE)
        if years_match:
            product['supplier_years'] = int(years_match.group(1))
        
        # País (de la bandera)
        flag_img = years_elem.select_one('img[alt]')
        if flag_img:
            product['supplier_country_code'] = flag_img.get('alt', '').strip().upper()
    
    # 10) Diamantes (Gold Supplier level) - selector CSS corregido
    try:
        # Buscar directamente elementos use dentro del área de ggs
        diamond_area = card.select('[data-aplus-auto-card-mod*="area=ggs"]')
        diamond_count = 0
        for area in diamond_area:
            # Buscar elementos use con referencia a diamond-large
            uses = area.find_all('use')
            for use in uses:
                href = use.get('xlink:href', '') or use.get('href', '')
                if '#icon-diamond-large' in href:
                    diamond_count += 1
        product['supplier_gold_level'] = diamond_count
    except Exception as e:
        product['supplier_gold_level'] = 0
    
    # 11) Imagen del producto - MEJORADO CON MÚLTIPLES SELECTORES
    img_elem = None
    img_selectors = [
        'img[src*="product"]',  # Selector original
        '.search-card-e-pic img',  # Selector común para imágenes de producto
        '.search-card-e-gallery img',  # Galería de imágenes
        '.m-gallery-product-item-img img',  # Otro selector común
        '.m-gallery-product-image img',  # Variación del selector
        '.gallery-offer-item__img img',  # Selector alternativo
        'a[href*="product"] img',  # Imagen dentro de link de producto  
        '.search-offer-pic img',  # Selector adicional
        '.search-result-item-pic img',  # Otro selector posible
        'img[alt*="product"]',  # Por atributo alt
        'img[data-src]',  # Imágenes lazy-loaded
        'img[src*="alicdn.com"]',  # Imágenes de Alibaba CDN
        'img'  # Fallback: cualquier imagen en la tarjeta
    ]
    
    for selector in img_selectors:
        img_elem = card.select_one(selector)
        if img_elem:
            src = img_elem.get('src') or img_elem.get('data-src')
            if src and src not in ['', 'null', None]:
                # Limpiar y validar URL
                if src.startswith('//'):
                    src = 'https:' + src
                elif src.startswith('/'):
                    src = 'https://www.alibaba.com' + src
                
                # Validar que sea una URL de imagen válida
                if ('alicdn.com' in src or 'alibaba.com' in src) and any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
                    product['image_link'] = src
                    break
                elif 'http' in src and not 'data:' in src:  # URL válida pero sin extensión específica
                    product['image_link'] = src
                    break
    
    # Solo retornar si tenemos título
    if product['product_title']:
        return product
    
    return None

def extract_price_range_from_text(price_text):
    """Extrae números de precio del texto: $6.80-9.90 -> [6.80, 9.90]"""
    # Usar regex para números con punto decimal
    numbers = []
    for match in re.finditer(r'(\d+(?:\.\d+)?)', price_text.replace(',', '')):
        try:
            numbers.append(float(match.group(1)))
        except ValueError:
            continue
    return sorted(set(numbers)) if numbers else None

def normalize_unit(unit_str):
    """Normaliza unidades: pieces -> piece, sets -> set, etc."""
    unit = unit_str.lower().strip()
    if unit.startswith('piece'):
        return 'piece'
    elif unit.startswith('set'):
        return 'set'
    elif unit.startswith('box'):
        return 'box'
    elif unit.startswith('carton'):
        return 'carton'
    elif unit.startswith('pair'):
        return 'pair'
    elif unit.startswith('pack'):
        return 'pack'
    else:
        return unit or 'piece'

# Selectores de tarjetas para mejorar card scoping
CARD_SELECTORS = [
    '.fy23-search-card.m-gallery-product-item-v2.J-search-card-wrapper',
    '.m-gallery-product-item-v2',
    '.J-search-card-wrapper',
    '.search-card-wrapper',
    '.searchx-offer-item'
]

def _closest_card(node):
    """Encuentra la tarjeta más cercana que contenga el nodo dado"""
    cur = node
    while cur and cur.name not in ('html', 'body'):
        # ¿este nodo coincide con algún selector de card?
        cls = ' '.join(cur.get('class', []))
        if any(sel.split('.')[-1] in cls for sel in CARD_SELECTORS):
            return cur
        cur = cur.parent
    return None

# MÉTODO ANTERIOR - MANTENIDO COMO FALLBACK CON MEJOR CARD SCOPING
def extract_alibaba_reviews_prices(html):
    """Extrae reviews y precios usando data-aplus-auto-card-mod (método robusto) - FALLBACK METHOD"""
    soup = BeautifulSoup(html, 'html.parser')

    # Índice por product link (href del detalle)
    products = defaultdict(lambda: {
        'product_link': None,
        'rating_avg': None,
        'rating_count': None,
        'price_max': None
    })

    # 1) Link del producto (clave para unir)
    for a in soup.select('a.search-card-e-detail-wrapper[href]'):
        href = a.get('href')
        if href and not href.startswith('http'):
            href = 'https:' + href if href.startswith('//') else href
        products[href]['product_link'] = href

    # 2) Reviews desde HTML (area=review & areaContent="<avg>@@<count>")
    for rev in soup.select('[data-aplus-auto-card-mod^="area=review"]'):
        area = rev.get('data-aplus-auto-card-mod', '')
        m = re.search(r'areaContent=([^&]+)', area)
        if not m: 
            continue
        content = m.group(1)  # ejemplo: 4.6@@36
        parts = content.split('@@')
        avg = parse_number_en(parts[0]) if parts else None
        count = parse_number_en(parts[1]) if len(parts) > 1 else None

        # Ubicar el anchor de detalle usando card scoping mejorado
        card = _closest_card(rev)
        if not card:
            continue
        link_tag = card.select_one('a.search-card-e-detail-wrapper[href]')
        if link_tag and link_tag.get('href'):
            href = link_tag['href']
            if not href.startswith('http'):
                href = 'https:' + href if href.startswith('//') else href
            products[href]['product_link'] = href
            if avg is not None:
                products[href]['rating_avg'] = avg
            if count is not None:
                products[href]['rating_count'] = count

    # 3) Precio desde HTML (area=price & areaContent="<rango>")
    for price in soup.select('[data-aplus-auto-card-mod^="area=price"]'):
        area = price.get('data-aplus-auto-card-mod', '')
        m = re.search(r'areaContent=([^&]+)', area)
        if not m:
            continue
        pmax = max_price_from_areacontent(m.group(1))
        # Usar card scoping mejorado
        card = _closest_card(price)
        if not card:
            continue
        link_tag = card.select_one('a.search-card-e-detail-wrapper[href]')
        if link_tag and link_tag.get('href'):
            href = link_tag['href']
            if not href.startswith('http'):
                href = 'https:' + href if href.startswith('//') else href
            products[href]['product_link'] = href
            if pmax is not None:
                # Guarda el máximo del rango (o único)
                products[href]['price_max'] = pmax

    # 4) Fallback: raspar del JSON embebido reviewCount/reviewScore cuando falten
    if any(v['rating_avg'] is None or v['rating_count'] is None for v in products.values()):
        text = soup.get_text(' ', strip=False)
        # Busca pares reviewCount/reviewScore cercanos
        for m in re.finditer(r'"reviewCount"\s*:\s*(\d+)\s*,\s*"reviewScore"\s*:\s*"([\d.]+)"', text):
            count = parse_number_en(m.group(1))
            avg = parse_number_en(m.group(2))
            # No tenemos el link aquí; si hay solo un producto sin reviews HTML, rellena "alguno"
            for k, v in products.items():
                if v['rating_avg'] is None and avg is not None:
                    v['rating_avg'] = avg
                    v['rating_count'] = count
                    break

    # Limpia entradas sin link
    out = [v for v in products.values() if v['product_link']]
    return out

class AlibabaProductScraper:
    def __init__(self, username='justo_eHMs7', password='Justo1234567_'):
        self.username = username
        self.password = password
        self.base_url = "https://realtime.oxylabs.io/v1/queries"
        self.alibaba_base = "https://www.alibaba.com"

    def search_products(self, query):
        logger.info(f"Starting search for: '{query}'")
        payload = {
            'source': 'alibaba_search',
            'user_agent_type': 'desktop_chrome',
            'render': 'html',
            'query': query
        }
        try:
            resp = requests.post(
                self.base_url,
                auth=(self.username, self.password),
                json=payload,
                timeout=120
            )
            resp.raise_for_status()
            response_data = resp.json()
            products = self.parse_response(response_data)
            logger.info(f"Successfully extracted {len(products)} products")
            return products
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            return []

    def parse_response(self, response_data):
        if not isinstance(response_data, dict) or 'results' not in response_data:
            logger.error("Invalid response format")
            return []
        results = response_data['results']
        if not results:
            logger.error("No results in response")
            return []
        html_content = results[0].get('content', '')
        if not html_content:
            logger.error("No HTML content found")
            return []
        return self.extract_from_html(html_content)

    def extract_from_html(self, html_content):
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # MÉTODO NUEVO: Extracción directa desde tarjetas HTML (prioritario)
            logger.info("🆕 Using new card-based extraction method")
            products = extract_alibaba_products_from_cards(html_content)
            
            if products:
                logger.info(f"✅ Card extraction successful: {len(products)} products")
                # Agregar campos de compatibilidad para productos extraídos de tarjetas
                products = self.add_compatibility_fields(products)
                return products
            
            # FALLBACK: Método anterior con JSON + HTML robusto
            logger.warning("🔄 Card extraction failed, falling back to JSON + HTML method")
            # 1) Primero intento JSON embebido (nombres/links/precio/etc.)
            products = self.extract_from_json(soup) or []
            
            # 2) Usar método robusto para reviews y precios desde data-aplus-auto-card-mod
            robust_data = extract_alibaba_reviews_prices(html_content)
            
            # 3) Enriquecer productos JSON con datos robustos de HTML
            products = self.enrich_with_robust_data(products, robust_data)
            
            # 4) Enriquecer con HTML de las tarjetas (MOQ y vendidos)
            if products:
                products = self.enrich_with_html_by_product_id(soup, products)
                # Fallback global (por si aún faltan campos)
                products = self.enhance_with_global_html_search(soup, products)
                return products
            logger.warning("All extraction methods failed")
            return []
        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")
            return []

    # -------------------------
    # Enriquecimiento por tarjeta HTML (match por productId)
    # -------------------------
    def build_container_index(self, soup):
        """
        Indexa contenedores de tarjeta por productId, leyendo:
        - data-ctrdot (cuando viene)
        - productId dentro de data-aplus-auto-offer
        """
        index = {}
        for card in soup.select('div.searchx-offer-item'):
            pid = card.get('data-ctrdot')
            if not pid:
                ap = card.get('data-aplus-auto-offer', '')
                m = re.search(r'productId=(\d+)', ap)
                if m:
                    pid = m.group(1)
            if pid:
                index[str(pid)] = card
        return index

    def enrich_with_html_by_product_id(self, soup, products):
        containers = self.build_container_index(soup)
        if not containers:
            logger.warning("No HTML product containers found to enrich")
            return products

        enriched_moq, enriched_sold = 0, 0
        for p in products:
            pid = str(p.get('product_id') or '') or self.try_guess_pid_from_url(p.get('product_link'))
            if not pid:
                continue
            card = containers.get(pid)
            if not card:
                continue

            # MOQ
            if p.get('minimum_order') in [None, 0]:
                moq_text = self.get_text(card, '.price-area-center .searchx-moq, .searchx-moq')
                moq_val = parse_int_any(moq_text)
                if moq_val is not None:
                    p['minimum_order'] = float(moq_val)
                    enriched_moq += 1

            # Vendidos
            if p.get('amount_sold') in [None, 0]:
                sold_text = self.get_text(card, '.price-area-center .searchx-sold-order, .searchx-sold-order')
                sold_val = parse_int_any(sold_text)
                if sold_val is not None:
                    p['amount_sold'] = float(sold_val)
                    enriched_sold += 1

        logger.info(f"HTML enrich: MOQ={enriched_moq}, Sold={enriched_sold}")
        return products

    def try_guess_pid_from_url(self, url):
        if not url:
            return None
        # agarro el último bloque de dígitos largo
        m = re.search(r'(\d{8,})', url)
        return m.group(1) if m else None

    def get_text(self, node, css):
        el = node.select_one(css)
        return el.get_text(strip=True) if el else None

    # -------------------------
    # Fallback global: buscar patrones en TODO el HTML
    # -------------------------
    def enhance_with_global_html_search(self, soup, products):
        try:
            html_text = soup.get_text(" ")
            # Recojo muchos posibles matches (no fiables 1:1)
            moq_matches = re.findall(r'(?:Pedido\s*m[ií]n:|MOQ:|Minimum\s*Order:|Pedido\s*m[ií]nimo:)\s*([\d\.,]+)', html_text, flags=re.IGNORECASE)
            sold_matches = re.findall(r'([\d\.,]+)\s*(?:vendidos|sold|orders|pedidos|units\s*sold)', html_text, flags=re.IGNORECASE)

            # asigno solo si el producto aún está vacío y hay material
            i, j = 0, 0
            for p in products:
                if (p.get('minimum_order') in [None, 0]) and i < len(moq_matches):
                    val = parse_int_any(moq_matches[i])
                    if val is not None:
                        p['minimum_order'] = float(val)
                        i += 1
                if (p.get('amount_sold') in [None, 0]) and j < len(sold_matches):
                    val = parse_int_any(sold_matches[j])
                    if val is not None:
                        p['amount_sold'] = float(val)
                        j += 1
            return products
        except Exception as e:
            logger.warning(f"Error in global HTML search: {e}")
            return products

    # -------------------------
    # JSON embebido
    # -------------------------
    def extract_from_json(self, soup):
        products = []
        scripts = soup.find_all('script')
        for script in scripts:
            content = script.string or ""
            if "_offer_list" not in content or len(content) < 5000:
                continue
            try:
                m = re.search(
                    r'window\.__page__data[^=]*\._offer_list\s*=\s*({.*?});?\s*(?:window\.|$)',
                    content, re.DOTALL
                )
                if not m:
                    continue
                json_str = self.clean_json_string(m.group(1))
                data = json.loads(json_str)
                offers = data.get('offerResultData', {}).get('offers', [])
                for offer in offers:
                    prod = self.parse_offer(offer)
                    if prod:
                        products.append(prod)
                if products:
                    return products
            except Exception as e:
                logger.warning(f"extract_from_json: {e}")
        return products

    def clean_json_string(self, s):
        s = re.sub(r',\s*}', '}', s)
        s = re.sub(r',\s*]', ']', s)
        s = s.replace('undefined', 'null')
        return s

    def parse_offer(self, offer):
        try:
            product = {
                'product_id': None,
                'product_title': None,
                'product_url': None,
                'price_min': None,
                'price_max': None,
                'price': None,  # Mantener para compatibilidad
                'currency': None,
                'moq_value': None,
                'moq_unit': None,
                'minimum_order': None,  # Mantener para compatibilidad
                'sold_quantity': None,
                'amount_sold': None,  # Mantener para compatibilidad
                'product_review_avg': None,
                'product_review_count': None,
                'review_average': None,  # Mantener para compatibilidad
                'amount_of_reviews': None,  # Mantener para compatibilidad
                'product_certifications': [],
                'product_cert_icon_urls': [],
                'est_delivery_by': None,
                'has_easy_return': False,
                'has_add_to_cart': False,
                'has_chat_now': False,
                'has_add_to_compare': False,
                'has_add_to_favorites': False,
                'supplier_name': None,
                'supplier_profile_url': None,
                'supplier_verified': False,
                'supplier_gold_level': 0,
                'supplier_years': None,
                'supplier_country_code': None,
                'seller_name': None,  # Mantener para compatibilidad
                'seller_link': None,  # Mantener para compatibilidad
                'product_link': None,  # Mantener para compatibilidad
                'image_link': None,
                'is_supplier_verified': False  # Mantener para compatibilidad
            }

            # product_id: varios nombres posibles
            pid = (offer.get('productId') or offer.get('offerId') or
                   offer.get('id') or offer.get('dataId') or offer.get('offerid'))
            if pid:
                product['product_id'] = str(pid)

            # título - PRIORIZAR enPureTitle que está limpio
            title = offer.get('enPureTitle') or offer.get('title') or ''
            if not title:
                title = ''
            # Limpiar HTML tags si los hay
            title = re.sub(r'<[^>]+>', '', str(title)).strip()
            product['product_title'] = title or None
            product['title'] = title or None  # Mantener compatibilidad

            # precio → manejo de rangos y moneda (mejorado con parser inteligente)
            price = offer.get('price') or offer.get('priceV2')
            if price:
                price_str = str(price)
                prices = extract_price_range_smart(price_str)
                if prices:
                    if len(prices) == 1:
                        product['price'] = prices[0]
                        product['price_min'] = prices[0]
                        product['price_max'] = prices[0]
                    else:
                        product['price'] = max(prices)  # Compatibilidad
                        product['price_min'] = min(prices)
                        product['price_max'] = max(prices)
                    
                    # Detectar moneda (asumimos USD por defecto en Alibaba)
                    if '€' in price_str or 'EUR' in price_str.upper():
                        product['currency'] = 'EUR'
                    elif '$' in price_str or 'USD' in price_str.upper():
                        product['currency'] = 'USD'
                    else:
                        product['currency'] = 'USD'  # Por defecto

            # seller/supplier info
            company_name = (offer.get('companyName') or '').strip()
            product['supplier_name'] = company_name or None
            product['seller_name'] = company_name or None  # Compatibilidad

            # links
            supplier_href = offer.get('supplierHref', '')
            if supplier_href:
                product['supplier_profile_url'] = self.clean_url(supplier_href)
                product['seller_link'] = self.clean_url(supplier_href)  # Compatibilidad

            product_url = offer.get('productUrl', '')
            if product_url:
                product['product_url'] = self.clean_url(product_url)
                product['product_link'] = self.clean_url(product_url)  # Compatibilidad
                if not product['product_id']:
                    # intento extraer pid de la URL
                    guessed = self.try_guess_pid_from_url(product['product_url'])
                    if guessed:
                        product['product_id'] = guessed

            main_image = offer.get('mainImage', '')
            if main_image:
                product['image_link'] = self.clean_url(main_image)

            # MOQ desde JSON - MEJORADO: Extraer valor y unidad
            moq_value = None
            moq_unit = None
            
            # Método 1: halfTrustMoq (numérico directo)
            if offer.get('halfTrustMoq') is not None:
                try:
                    moq_value = float(offer.get('halfTrustMoq'))
                except (ValueError, TypeError):
                    pass
            
            # Método 2: moqV2 (string descriptivo) - extraer valor y unidad
            if moq_value is None and offer.get('moqV2'):
                moq_str = str(offer.get('moqV2'))
                moq_match = re.search(r'([\d,\.]+)\s*(\w+)', moq_str, re.IGNORECASE)
                if moq_match:
                    moq_val = parse_int_any(moq_match.group(1))
                    if moq_val is not None:
                        moq_value = float(moq_val)
                        moq_unit = self.normalize_moq_unit(moq_match.group(2))
                else:
                    moq_val = parse_int_any(moq_str)
                    if moq_val is not None:
                        moq_value = float(moq_val)
            
            # Método 3: moq tradicional
            if moq_value is None and offer.get('moq'):
                moq_str = str(offer.get('moq'))
                moq_match = re.search(r'([\d,\.]+)\s*(\w+)', moq_str, re.IGNORECASE)
                if moq_match:
                    moq_val = parse_int_any(moq_match.group(1))
                    if moq_val is not None:
                        moq_value = float(moq_val)
                        moq_unit = self.normalize_moq_unit(moq_match.group(2))
                else:
                    moq_val = parse_int_any(moq_str)
                    if moq_val is not None:
                        moq_value = float(moq_val)
                        
            if moq_value and moq_value > 0:
                product['moq_value'] = moq_value
                product['moq_unit'] = moq_unit or 'piece'
                product['minimum_order'] = moq_value  # Compatibilidad

            # Verificación del proveedor y nivel Gold
            is_verified = False
            gold_level = 0
            supplier_years = None
            
            # Verificar indicadores directos
            if any([
                offer.get('goldSupplierIcon'),
                offer.get('goldSupplierYears'),
                offer.get('companyAuthProvider'),
                offer.get('companyAuthTagList')
            ]):
                is_verified = True
            
            # Extraer años como proveedor
            years_data = offer.get('goldSupplierYears')
            if years_data:
                years_match = re.search(r'(\d+)', str(years_data))
                if years_match:
                    supplier_years = int(years_match.group(1))
            
            # También buscar en estructura anidada
            if not is_verified or not supplier_years:
                iui_info = offer.get('iuiInfo', {})
                if isinstance(iui_info, dict):
                    data_source = iui_info.get('dataSource', {})
                    if isinstance(data_source, dict):
                        company_info = data_source.get('companyInfo', {})
                        if isinstance(company_info, dict):
                            if not is_verified and any([
                                company_info.get('goldSupplierIcon'),
                                company_info.get('goldSupplierYears'),
                                company_info.get('companyAuthProvider'),
                                company_info.get('companyAuthTagList')
                            ]):
                                is_verified = True
                            
                            if not supplier_years:
                                years_data = company_info.get('goldSupplierYears')
                                if years_data:
                                    years_match = re.search(r'(\d+)', str(years_data))
                                    if years_match:
                                        supplier_years = int(years_match.group(1))
            
            product['supplier_verified'] = is_verified
            product['supplier_gold_level'] = gold_level  # Se actualizará en HTML parsing
            product['supplier_years'] = supplier_years
            product['is_supplier_verified'] = is_verified  # Compatibilidad

            # REVIEWS - SEPARACIÓN ESTRICTA: Producto vs Proveedor
            # SOLO reviews de PRODUCTO (nunca mezclar con supplier)
            product_review_count = 0
            product_review_score = 0.0
            
            # Método 1: reviewCount y reviewScore directos (SOLO PRODUCTO)
            if offer.get('reviewCount') is not None:
                try:
                    product_review_count = int(offer.get('reviewCount', 0))
                except (ValueError, TypeError):
                    product_review_count = 0
                    
            if offer.get('reviewScore') is not None:
                try:
                    product_review_score = float(str(offer.get('reviewScore')).replace(',', '.'))
                except (ValueError, TypeError):
                    product_review_score = 0.0
            
            # Establecer campos de reviews de PRODUCTO SOLAMENTE
            if product_review_count > 0:
                product['product_review_count'] = product_review_count
                product['amount_of_reviews'] = product_review_count  # Compatibilidad
            if product_review_score > 0:
                product['product_review_avg'] = product_review_score
                product['review_average'] = product_review_score  # Compatibilidad
            
            # REVIEWS DE PROVEEDOR - Guardar por separado (NUNCA mezclar con producto)
            supplier_review_count = None
            supplier_review_avg = None
            
            iui_info = offer.get('iuiInfo') or {}
            if isinstance(iui_info, dict):
                data_source = iui_info.get('dataSource')
                if isinstance(data_source, dict):
                    company_info = data_source.get('companyInfo')
                    if isinstance(company_info, dict):
                        try:
                            supplier_review_count = int(company_info.get('reviewCount')) if company_info.get('reviewCount') is not None else None
                        except (ValueError, TypeError):
                            pass
                        try:
                            supplier_review_avg = float(str(company_info.get('reviewScore')).replace(',', '.')) if company_info.get('reviewScore') is not None else None
                        except (ValueError, TypeError):
                            pass
            
            # Campos separados para reviews de proveedor
            product['supplier_review_count'] = supplier_review_count
            product['supplier_review_avg'] = supplier_review_avg

            # vendidos / órdenes
            sold_value = None
            if offer.get('soldCount') is not None:
                try:
                    sold_value = float(offer.get('soldCount') or 0)
                except:
                    pass
            elif offer.get('orderCount') is not None:
                try:
                    sold_value = float(offer.get('orderCount') or 0)
                except:
                    pass
                    
            if sold_value is not None and sold_value > 0:
                product['sold_quantity'] = int(sold_value)
                product['amount_sold'] = sold_value  # Compatibilidad

            if product['product_title']:
                return product
        except Exception as e:
            logger.warning(f"Error parsing offer: {e}")
        return None

    def extract_highest_price(self, price_str):
        # Busca todos los números, normaliza y devuelve el mayor
        nums = []
        for tok in re.findall(r'[\d.,]+', price_str):
            val = extract_first_number(tok)
            if val is not None:
                nums.append(val)
        return max(nums) if nums else None
    
    def extract_price_range(self, price_str):
        """Extrae rango de precios: $6.80-9.90 -> [6.80, 9.90], $24 -> [24]"""
        # Buscar números con punto decimal (formato USD estándar)
        numbers = []
        for match in re.finditer(r'(\d+(?:\.\d+)?)', price_str.replace(',', '')):
            try:
                numbers.append(float(match.group(1)))
            except ValueError:
                continue
        return sorted(set(numbers)) if numbers else None
    
    def normalize_moq_unit(self, unit_str):
        """Normaliza unidades de MOQ"""
        unit = unit_str.lower().strip()
        if unit.startswith('piece'):
            return 'piece'
        elif unit.startswith('set'):
            return 'set'
        elif unit.startswith('box'):
            return 'box'
        elif unit.startswith('carton'):
            return 'carton'
        elif unit.startswith('pair'):
            return 'pair'
        elif unit.startswith('pack'):
            return 'pack'
        else:
            return unit or 'piece'
    
    def add_compatibility_fields(self, products):
        """Agrega campos de compatibilidad para productos extraídos con el nuevo método
        IMPORTANTE: NUNCA mapear supplier_review_* a campos de producto
        """
        for product in products:
            # Campos de compatibilidad con el sistema anterior
            if not product.get('title') and product.get('product_title'):
                product['title'] = product['product_title']
            if not product.get('product_link') and product.get('product_url'):
                product['product_link'] = product['product_url']
            if not product.get('seller_name') and product.get('supplier_name'):
                product['seller_name'] = product['supplier_name']
            if not product.get('seller_link') and product.get('supplier_profile_url'):
                product['seller_link'] = product['supplier_profile_url']
            if not product.get('minimum_order') and product.get('moq_value'):
                product['minimum_order'] = product['moq_value']
            if not product.get('amount_sold') and product.get('sold_quantity'):
                product['amount_sold'] = float(product['sold_quantity'])
            
            # REVIEWS - SOLO mapear si existen reviews de PRODUCTO (nunca de supplier)
            if not product.get('amount_of_reviews') and product.get('product_review_count'):
                product['amount_of_reviews'] = product['product_review_count']
            if not product.get('review_average') and product.get('product_review_avg'):
                product['review_average'] = product['product_review_avg']
            
            # Verificación del proveedor
            if not product.get('is_supplier_verified') and product.get('supplier_verified'):
                product['is_supplier_verified'] = product['supplier_verified']
                
        return products
    
    def enrich_with_robust_data(self, products, robust_data):
        """Enriquecer productos del JSON con datos robustos del HTML"""
        if not robust_data:
            logger.info("No robust HTML data found")
            return products
        
        # Crear índice por product_link para matching rápido
        robust_index = {item['product_link']: item for item in robust_data if item.get('product_link')}
        
        enriched_price, enriched_reviews = 0, 0
        
        for product in products:
            product_link = product.get('product_link')
            if not product_link:
                continue
                
            # Buscar datos robustos para este producto
            robust_item = robust_index.get(product_link)
            if not robust_item:
                continue
            
            # Enriquecer precio si está vacío o es None
            if (not product.get('price') or product.get('price') == 0) and robust_item.get('price_max'):
                product['price'] = robust_item['price_max']
                enriched_price += 1
                
            # Enriquecer reviews si están vacíos o son None
            if (not product.get('amount_of_reviews') or product.get('amount_of_reviews') == 0) and robust_item.get('rating_count'):
                product['amount_of_reviews'] = int(robust_item['rating_count'])
                enriched_reviews += 1
                
            if (not product.get('review_average') or product.get('review_average') == 0) and robust_item.get('rating_avg'):
                product['review_average'] = float(robust_item['rating_avg'])
        
        logger.info(f"Robust HTML enrich: Price={enriched_price}, Reviews={enriched_reviews}")
        return products

    def clean_url(self, url):
        if not url:
            return None
        if url.startswith('//'):
            url = 'https:' + url
        elif url.startswith('/'):
            url = urljoin(self.alibaba_base, url)
        return url

    # -------------------------
    # Filtering helpers
    # -------------------------
    def filter_products(self, products, min_reviews=1, require_verified=True, verbose=True):
        """
        Filtrar productos basándose en reviews y verificación de proveedores
        """
        if not products:
            return []
        
        original_count = len(products)
        filtered = []
        
        for product in products:
            # Filtro por reviews
            if min_reviews > 0:
                reviews = product.get('amount_of_reviews')
                if not reviews or reviews < min_reviews:
                    if verbose:
                        logger.debug(f"Filtered out - insufficient reviews: {product.get('title', 'Unknown')[:50]}... (reviews: {reviews})")
                    continue
            
            # Filtro por verificación
            if require_verified:
                if not product.get('is_supplier_verified', False):
                    if verbose:
                        logger.debug(f"Filtered out - not verified: {product.get('title', 'Unknown')[:50]}...")
                    continue
            
            filtered.append(product)
        
        filtered_count = len(filtered)
        if verbose:
            logger.info(f"🔍 FILTROS APLICADOS:")
            logger.info(f"  📊 Productos originales: {original_count}")
            logger.info(f"  ⭐ Mín. reviews requeridas: {min_reviews}")
            logger.info(f"  ✅ Solo proveedores verificados: {require_verified}")
            logger.info(f"  📈 Productos que pasaron filtros: {filtered_count}")
            if original_count > 0:
                logger.info(f"  📊 Tasa de aprobación: {filtered_count/original_count*100:.1f}%")
        
        return filtered
    
    # -------------------------
    # Output helpers
    # -------------------------
    def save_results(self, products, filename=None, format='csv'):
        if not products:
            logger.warning("No products to save")
            return None
        if not filename:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"alibaba_products_{ts}.{format}"
        try:
            if format.lower() == 'json':
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(products, f, indent=2, ensure_ascii=False)
            elif format.lower() == 'csv':
                df = pd.DataFrame(products)
                df.to_csv(filename, index=False, encoding='utf-8-sig')
            else:
                raise ValueError(f"Unsupported format: {format}")
            logger.info(f"Results saved to: {filename}")
            return filename
        except Exception as e:
            logger.error(f"Error saving results: {e}")
            return None

    def print_summary(self, products):
        if not products:
            print("No products found")
            return
        print(f"\n{'='*60}\nALIBABA SCRAPING RESULTS\n{'='*60}")
        print(f"Total products found: {len(products)}")

        fields = [
            'title','price','seller_name','seller_link','product_link','image_link',
            'minimum_order','is_supplier_verified','amount_of_reviews','review_average','amount_sold'
        ]
        print(f"\nField extraction rates:")
        for f in fields:
            count = sum(1 for p in products if p.get(f) not in [None, '', 0, False])
            pct = (count/len(products))*100 if products else 0
            print(f"  {f:<20}: {count:>3}/{len(products)} ({pct:>5.1f}%)")

        # Estadísticas detalladas de precios (estilo MercadoLibre)
        prices = [p.get('price') for p in products if p.get('price') is not None]
        if prices:
            prices_sorted = sorted(prices)
            n = len(prices)
            median = prices_sorted[n//2] if n % 2 == 1 else (prices_sorted[n//2-1] + prices_sorted[n//2]) / 2
            
            # Percentiles
            p25 = prices_sorted[int(n * 0.25)]
            p75 = prices_sorted[int(n * 0.75)]
            
            # Categorías de precio
            low_price = [p for p in prices if p <= p25]
            mid_price = [p for p in prices if p25 < p <= p75]
            high_price = [p for p in prices if p > p75]
            
            print(f"\n🏷️  PRICE STATISTICS (MercadoLibre Style):")
            print(f"  Range: ${min(prices):.2f} - ${max(prices):.2f}")
            print(f"  Average: ${sum(prices)/len(prices):.2f}")
            print(f"  Median: ${median:.2f}")
            print(f"  25th Percentile: ${p25:.2f}")
            print(f"  75th Percentile: ${p75:.2f}")
            print(f"\n💰 Price Categories:")
            print(f"  Low Price (≤${p25:.2f}): {len(low_price)} products ({len(low_price)/n*100:.1f}%)")
            print(f"  Mid Price (${p25:.2f}-${p75:.2f}): {len(mid_price)} products ({len(mid_price)/n*100:.1f}%)")
            print(f"  High Price (>${p75:.2f}): {len(high_price)} products ({len(high_price)/n*100:.1f}%)")

        moqs = [p.get('minimum_order') for p in products if p.get('minimum_order') is not None]
        if moqs:
            print(f"\n📦 Minimum Order analysis:")
            print(f"  Range: {min(moqs):.0f} - {max(moqs):.0f} pieces")
            print(f"  Average: {sum(moqs)/len(moqs):.0f} pieces")

        revs = [p.get('amount_of_reviews') for p in products if p.get('amount_of_reviews') and p.get('amount_of_reviews') > 0]
        if revs:
            print(f"\n⭐ Reviews analysis:")
            print(f"  Range: {min(revs):.0f} - {max(revs):.0f} reviews")
            print(f"  Average: {sum(revs)/len(revs):.1f} reviews")

        solds = [p.get('amount_sold') for p in products if p.get('amount_sold') is not None]
        if solds:
            print(f"\n📊 Sold Quantity analysis:")
            print(f"  Range: {min(solds):.0f} - {max(solds):.0f} units")
            print(f"  Average: {sum(solds)/len(solds):.0f} units")

        verified_count = sum(1 for p in products if p.get('is_supplier_verified'))
        print(f"\n✅ Supplier verification: {verified_count}/{len(products)} ({verified_count/len(products)*100:.1f}%)")
        
        # Mejores productos por reseñas de proveedores verificados
        self.print_best_products(products)
        
        print(f"{'='*60}")
    
    def print_best_products(self, products):
        """
        Encuentra y muestra los mejores productos basados en reseñas de proveedores verificados
        """
        # Filtrar solo proveedores verificados con reseñas
        verified_with_reviews = [
            p for p in products 
            if p.get('is_supplier_verified') and 
               p.get('amount_of_reviews') and p.get('amount_of_reviews') > 0 and
               p.get('review_average') and p.get('review_average') > 0
        ]
        
        if not verified_with_reviews:
            print(f"\n🏆 No verified suppliers with reviews found")
            return
        
        print(f"\n🏆 BEST PRODUCTS (Verified Suppliers Only):")
        
        # Producto con más reseñas
        most_reviewed = max(verified_with_reviews, key=lambda x: x.get('amount_of_reviews', 0))
        
        # Producto con mejor calificación (mínimo 5 reseñas para ser confiable)
        reliable_reviews = [p for p in verified_with_reviews if p.get('amount_of_reviews', 0) >= 5]
        best_rated = None
        if reliable_reviews:
            best_rated = max(reliable_reviews, key=lambda x: x.get('review_average', 0))
        
        # Producto más vendido
        most_sold = None
        verified_with_sales = [p for p in verified_with_reviews if p.get('amount_sold')]
        if verified_with_sales:
            most_sold = max(verified_with_sales, key=lambda x: x.get('amount_sold', 0))
        
        # Mejor relación calidad-precio (rating alto + precio bajo)
        best_value = None
        if reliable_reviews:
            # Score = (rating/5) * (1/log(price+1)) para balancear calidad y precio
            import math
            scored_products = []
            for p in reliable_reviews:
                if p.get('price'):
                    rating_score = p.get('review_average', 0) / 5.0
                    price_score = 1 / math.log(p.get('price', 1) + 1)
                    combined_score = rating_score * 0.7 + price_score * 0.3
                    scored_products.append((p, combined_score))
            
            if scored_products:
                best_value = max(scored_products, key=lambda x: x[1])[0]
        
        # Mostrar resultados
        if most_reviewed:
            print(f"\n📈 MOST REVIEWED (Verified Supplier):")
            self.print_product_highlight(most_reviewed)
        
        if best_rated:
            print(f"\n⭐ HIGHEST RATED (Verified Supplier, 5+ reviews):")
            self.print_product_highlight(best_rated)
        
        if most_sold:
            print(f"\n🔥 BEST SELLER (Verified Supplier):")
            self.print_product_highlight(most_sold)
        
        if best_value:
            print(f"\n💎 BEST VALUE (Quality + Price, Verified Supplier):")
            self.print_product_highlight(best_value)
    
    def print_product_highlight(self, product):
        """
        Imprime los detalles destacados de un producto
        """
        title = product.get('title', 'N/A')
        if len(title) > 80:
            title = title[:77] + "..."
        
        print(f"  📦 {title}")
        print(f"  💰 Price: ${product.get('price', 0):.2f}")
        print(f"  🏭 Seller: {product.get('seller_name', 'N/A')}")
        
        if product.get('amount_of_reviews'):
            print(f"  ⭐ Reviews: {product.get('amount_of_reviews', 0):.0f} ({product.get('review_average', 0):.1f}/5.0)")
        
        if product.get('amount_sold'):
            print(f"  📊 Sold: {product.get('amount_sold', 0):.0f} units")
        
        if product.get('minimum_order'):
            print(f"  📦 MOQ: {product.get('minimum_order', 0):.0f} pieces")
        
        print(f"  🔗 Link: {product.get('product_link', 'N/A')}")

def main():
    parser = argparse.ArgumentParser(description='Scrape Alibaba product data')
    parser.add_argument('query', help='Search query for Alibaba products')
    parser.add_argument('--output', '-o', help='Output filename')
    parser.add_argument('--format', '-f', choices=['csv', 'json'], default='json')
    parser.add_argument('--show-sample', '-s', type=int, default=3, help='Show N sample products')
    parser.add_argument('--min-reviews', '-r', type=int, default=1, help='Minimum reviews required (0 to disable)')
    parser.add_argument('--allow-unverified', action='store_true', help='Allow non-verified suppliers')
    parser.add_argument('--no-filter', action='store_true', help='Skip all filtering (show all products)')
    args = parser.parse_args()

    scraper = AlibabaProductScraper()
    products = scraper.search_products(args.query)
    if not products:
        print("No products found or error occurred.")
        sys.exit(1)

    # Mostrar resumen de productos sin filtrar
    print(f"\n🔍 PRODUCTOS SIN FILTRAR:")
    scraper.print_summary(products)
    
    # Aplicar filtros si no están deshabilitados
    if not args.no_filter:
        min_reviews = args.min_reviews
        require_verified = not args.allow_unverified
        
        filtered_products = scraper.filter_products(
            products, 
            min_reviews=min_reviews, 
            require_verified=require_verified,
            verbose=True
        )
        
        if filtered_products:
            print(f"\n🎯 PRODUCTOS FILTRADOS:")
            scraper.print_summary(filtered_products)
            products = filtered_products  # Use filtered products for output
        else:
            print("\n⚠️  Ningún producto pasó los filtros. Usando productos originales.")
    else:
        print("\n📋 Filtros deshabilitados - mostrando todos los productos")

    if args.show_sample > 0:
        print(f"\nSample products (showing first {min(args.show_sample, len(products))}):")
        for i, p in enumerate(products[:args.show_sample], 1):
            print(f"\n--- Product {i} ---")
            for k, v in p.items():
                if v not in [None, '', False]:
                    if isinstance(v, float):
                        if k == 'price':
                            print(f"  {k}: ${v:.2f}")
                        elif k in ['minimum_order','amount_of_reviews','amount_sold']:
                            print(f"  {k}: {v:.0f}")
                        elif k == 'review_average':
                            print(f"  {k}: {v:.1f}")
                        else:
                            print(f"  {k}: {v}")
                    else:
                        print(f"  {k}: {v}")

    filename = scraper.save_results(products, args.output, args.format)
    if filename:
        print(f"\nResults saved to: {filename}")
    print("\nScraping completed successfully!")

if __name__ == "__main__":
    main()