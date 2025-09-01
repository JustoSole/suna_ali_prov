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

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# -------------------------
# PARSERS SIMPLES Y EFICIENTES (según tu propuesta)
# -------------------------

def parse_number_en(txt):
    """Mantener '.' como decimal, remover comas de miles"""
    s = (txt or "").strip().replace(",", "")
    m = re.search(r'\d+(?:\.\d+)?', s)
    return float(m.group()) if m else None

def max_price_from_areacontent(area_content):
    """Ej.: 'US $1,200.50-$1,350.00' -> 1350.00"""
    nums = [parse_number_en(x) for x in re.findall(r'[\d,]+\.\d+|[\d,]+', area_content)]
    nums = [n for n in nums if n is not None]
    return max(nums) if nums else None

def extract_product_reviews_and_price(card):
    """
    QUIRÚRGICO: Extrae link, reviews DE PRODUCTO SOLAMENTE, y precio manteniendo scope de card
    CRÍTICO: Usar selector específico para reviews de PRODUCTO, no proveedor
    """
    # Product link (clave de unión)
    detail_link = card.select_one('a.search-card-e-detail-wrapper[href]')
    if not detail_link:
        return None, None, None, None
        
    href = detail_link.get('href', '')
    if not href:
        return None, None, None, None
        
    # Normalizar URL
    if href.startswith('//'):
        href = 'https:' + href
    elif href.startswith('/'):
        href = 'https://www.alibaba.com' + href
    
    # REVIEWS DE PRODUCTO (MUY ESPECÍFICO - NO PROVEEDOR)
    review_avg = review_count = None
    # Usar selector MÁS ESPECÍFICO para evitar mezclar con reviews de proveedor
    review_elem = card.select_one('span.search-card-e-review[data-aplus-auto-card-mod*="area=review"]')
    if not review_elem:
        # FALLBACK: pero dentro del card y que sea específicamente de reviews de producto
        review_elem = card.select_one('[data-aplus-auto-card-mod*="area=review"][data-aplus-auto-card-mod*="areaContent"]')
    
    if review_elem:
        area_content = review_elem.get('data-aplus-auto-card-mod', '')
        content_match = re.search(r'areaContent=([^&]+)', area_content)
        if content_match:
            review_data = content_match.group(1)
            # Solo procesarlo si tiene formato de review de PRODUCTO (avg@@count)
            if '@@' in review_data:
                parts = review_data.split('@@')
                if len(parts) >= 2:
                    try:
                        review_avg = float(parts[0].replace(',', '.'))
                        review_count = int(parts[1])
                        # Validar que sean números razonables para producto
                        if review_avg < 0 or review_avg > 5 or review_count < 0:
                            review_avg = review_count = None
                    except (ValueError, TypeError):
                        review_avg = review_count = None
    
    # Precio - PRIORITARIO: area=price, FALLBACK: visual
    price_max = None
    price_elem = card.select_one('[data-aplus-auto-card-mod^="area=price"]')
    if price_elem:
        area_content = price_elem.get('data-aplus-auto-card-mod', '')
        content_match = re.search(r'areaContent=([^&]+)', area_content)
        if content_match:
            price_max = max_price_from_areacontent(content_match.group(1))
    
    # FALLBACK: selector visual si no hay area=price
    if price_max is None:
        visual_price = card.select_one('.search-card-e-price-main')
        if visual_price:
            price_text = visual_price.get_text(strip=True)
            if price_text:
                price_max = max_price_from_areacontent(price_text)
    
    return href, review_avg, review_count, price_max

def extract_supplier_data(card):
    """Extrae datos del PROVEEDOR (separado del producto)"""
    supplier_data = {
        'supplier_name': None,
        'supplier_profile_url': None,
        'supplier_verified': False,
        'supplier_gold_level': 0,
        'supplier_years': None,
        'supplier_country_code': None
    }
    
    # Nombre y perfil del proveedor
    company_elem = card.select_one('a.search-card-e-company')
    if company_elem:
        supplier_data['supplier_name'] = company_elem.get_text(strip=True)
        href = company_elem.get('href', '')
        if href:
            if href.startswith('//'):
                href = 'https:' + href
            elif href.startswith('/'):
                href = 'https://www.alibaba.com' + href
            supplier_data['supplier_profile_url'] = href
    
    # Verificado (badge)
    supplier_data['supplier_verified'] = bool(card.select_one('a.verified-supplier-icon__wrapper'))
    
    # Años y país
    years_elem = card.select_one('a.search-card-e-supplier__year')
    if years_elem:
        years_text = years_elem.get_text(strip=True)
        years_match = re.search(r'(\d+)\s*yrs?', years_text, re.IGNORECASE)
        if years_match:
            supplier_data['supplier_years'] = int(years_match.group(1))
        
        # País (bandera)
        flag_img = years_elem.select_one('img[alt]')
        if flag_img:
            supplier_data['supplier_country_code'] = flag_img.get('alt', '').strip().upper()
    
    # Nivel Gold (diamantes)
    ggs_elem = card.select_one('[data-aplus-auto-card-mod*="area=ggs"]')
    if ggs_elem:
        diamond_uses = ggs_elem.find_all('use')
        diamond_count = 0
        for use in diamond_uses:
            href = use.get('xlink:href', '') or use.get('href', '')
            if '#icon-diamond-large' in href:
                diamond_count += 1
        supplier_data['supplier_gold_level'] = diamond_count
    
    return supplier_data

def extract_moq_data(card):
    """Extrae MOQ (pedido mínimo)"""
    moq_elem = card.select_one('[data-aplus-auto-card-mod^="area=moq"]')
    if moq_elem:
        area_content = moq_elem.get('data-aplus-auto-card-mod', '')
        content_match = re.search(r'areaContent=([^&]+)', area_content)
        if content_match:
            moq_text = content_match.group(1)
            # Parsear "Min. order: 100 pieces"
            moq_match = re.search(r'min\.?\s*order:?\s*([\d,\.]+)\s*(\w+)', moq_text, re.IGNORECASE)
            if moq_match:
                moq_val = parse_number_en(moq_match.group(1))
                if moq_val:
                    return float(moq_val), moq_match.group(2).lower().strip()
    return None, None

def extract_product_certifications(card):
    """Extrae certificaciones del PRODUCTO (no del proveedor)"""
    cert_icons = card.select('img.search-card-e-icon__certification')
    certifications = []
    cert_urls = []
    
    for icon in cert_icons:
        alt = icon.get('alt', '').strip()
        src = icon.get('src', '').strip()
        if alt:
            certifications.append(alt)
        if src:
            # Normalizar URL si es necesario
            if src.startswith('//'):
                src = 'https:' + src
            cert_urls.append(src)
    
    return certifications, cert_urls

def extract_product_image(card):
    """Extrae imagen principal del PRODUCTO"""
    # Buscar imagen del producto (no banner o proveedor)
    img_elem = card.select_one('img[src*="product"]')
    if img_elem:
        src = img_elem.get('src', '')
        if src:
            # Normalizar URL
            if src.startswith('//'):
                src = 'https:' + src
            return src
    
    # FALLBACK: cualquier imagen dentro del card que no sea de proveedor
    img_fallback = card.select_one('a.search-card-e-detail-wrapper img')
    if img_fallback:
        src = img_fallback.get('src', '')
        if src and 'supplier' not in src.lower() and 'company' not in src.lower():
            if src.startswith('//'):
                src = 'https:' + src
            return src
    
    return None

def extract_additional_product_features(card):
    """Extrae características adicionales del producto"""
    features = {
        'est_delivery_by': None,
        'has_easy_return': False,
        'has_add_to_cart': False,
        'has_chat_now': False,
        'has_add_to_compare': False,
        'has_add_to_favorites': False
    }
    
    # Entrega estimada
    delivery_elem = card.select_one('[data-aplus-auto-card-mod*="area=deliveryBy"]')
    if delivery_elem:
        delivery_text = delivery_elem.get_text(strip=True)
        if delivery_text:
            features['est_delivery_by'] = delivery_text
    
    # Características booleanas (buscar en texto del card)
    card_text = card.get_text().lower()
    features['has_easy_return'] = 'easy return' in card_text
    features['has_add_to_cart'] = 'add to cart' in card_text
    features['has_chat_now'] = 'chat now' in card_text
    features['has_add_to_compare'] = 'add to compare' in card_text
    features['has_add_to_favorites'] = 'add to favorites' in card_text
    
    return features

def extract_basic_product_data(card):
    """Extrae datos básicos del producto (título, ID, etc.)"""
    product_data = {}
    
    # Título
    title_elem = card.select_one('[data-spm="d_title"] a, h2 a, .search-card-e-title a')
    if title_elem:
        title = title_elem.get_text(strip=True)
        title = re.sub(r'<[^>]+>', '', title)  # Limpiar HTML
        product_data['product_title'] = title
    
    return product_data

# -------------------------
# SCRAPER PRINCIPAL SIMPLIFICADO
# -------------------------

class SimpleAlibabaProductScraper:
    def __init__(self, username='justo_eHMs7', password='Justo1234567_'):
        self.username = username
        self.password = password
        self.base_url = "https://realtime.oxylabs.io/v1/queries"

    def search_products(self, query):
        logger.info(f"🔍 Starting SIMPLE search for: '{query}'")
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
            products = self.extract_from_html(response_data['results'][0]['content'])
            logger.info(f"✅ Successfully extracted {len(products)} products")
            return products
        except Exception as e:
            logger.error(f"❌ Error during scraping: {e}")
            return []

    def extract_from_html(self, html_content):
        """SIMPLIFICADO: Solo card-based extraction quirúrgico"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Buscar cards
        card_selectors = [
            '.fy23-search-card.m-gallery-product-item-v2.J-search-card-wrapper',
            '.m-gallery-product-item-v2',
            '.J-search-card-wrapper',
            '.search-card-wrapper'
        ]
        
        cards = []
        for selector in card_selectors:
            cards = soup.select(selector)
            if cards:
                logger.info(f"🎯 Found {len(cards)} cards with: {selector}")
                break
        
        if not cards:
            logger.warning("⚠️ No product cards found")
            return []
        
        products = []
        for i, card in enumerate(cards):
            try:
                product = self.extract_product_from_card_simple(card)
                if product:
                    products.append(product)
            except Exception as e:
                logger.warning(f"⚠️ Error in card {i}: {e}")
                continue
        
        logger.info(f"✅ Extracted {len(products)} products from {len(cards)} cards")
        return products

    def extract_product_from_card_simple(self, card):
        """EXTRACCIÓN QUIRÚRGICA siguiendo tu propuesta"""
        
        # 1) PRODUCTO: Link, reviews, precio (quirúrgico)
        href, review_avg, review_count, price_max = extract_product_reviews_and_price(card)
        if not href:
            return None  # Sin link = no producto válido
        
        # 2) PRODUCTO: Datos básicos
        basic_data = extract_basic_product_data(card)
        if not basic_data.get('product_title'):
            return None  # Sin título = no producto válido
        
        # 3) PRODUCTO: MOQ
        moq_value, moq_unit = extract_moq_data(card)
        
        # 4) PRODUCTO: Certificaciones e imagen
        certifications, cert_urls = extract_product_certifications(card)
        image_link = extract_product_image(card)
        
        # 5) PRODUCTO: Características adicionales
        additional_features = extract_additional_product_features(card)
        
        # 6) PROVEEDOR: Datos separados (no mezclar con producto)
        supplier_data = extract_supplier_data(card)
        
        # 7) CONSTRUIR PRODUCTO FINAL COMPLETO
        product = {
            # PRODUCTO PRINCIPAL
            'product_id': self.extract_product_id_from_url(href),
            'product_title': basic_data['product_title'],
            'product_url': href,
            'price': price_max,
            'price_min': price_max,  # Simplificado: usar el máximo para ambos
            'price_max': price_max,
            'currency': self.detect_currency_from_card(card),
            
            # REVIEWS DE PRODUCTO (NO PROVEEDOR)
            'product_review_avg': review_avg,
            'product_review_count': review_count,
            
            # MOQ
            'moq_value': moq_value,
            'moq_unit': moq_unit,
            
            # CERTIFICACIONES Y MULTIMEDIA
            'product_certifications': certifications,
            'product_cert_icon_urls': cert_urls,
            'image_link': image_link,
            
            # CARACTERÍSTICAS ADICIONALES
            **additional_features,
            
            # PROVEEDOR (COMPLETAMENTE SEPARADO)
            **supplier_data,
            
            # COMPATIBILIDAD (mapeo simple)
            'title': basic_data['product_title'],
            'product_link': href,
            'review_average': review_avg,
            'amount_of_reviews': review_count,
            'minimum_order': moq_value,
            'seller_name': supplier_data['supplier_name'],
            'seller_link': supplier_data['supplier_profile_url'],
            'is_supplier_verified': supplier_data['supplier_verified']
        }
        
        return product

    def extract_product_id_from_url(self, url):
        """Extrae ID del producto de la URL"""
        if not url:
            return None
        id_match = re.search(r'(\d{8,})', url)
        return id_match.group(1) if id_match else None

    def detect_currency_from_card(self, card):
        """Detecta moneda simple"""
        price_text = ''
        price_elem = card.select_one('.search-card-e-price-main')
        if price_elem:
            price_text = price_elem.get_text(strip=True)
        
        if '€' in price_text:
            return 'EUR'
        elif '$' in price_text or 'USD' in price_text.upper():
            return 'USD'
        else:
            return 'USD'  # Por defecto

    def save_results(self, products, filename=None, format='json'):
        """Guardar resultados (JSON por defecto)"""
        if not products:
            logger.warning("⚠️ No products to save")
            return None
        
        if not filename:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"alibaba_simple_{ts}.{format}"
        
        try:
            if format.lower() == 'json':
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(products, f, indent=2, ensure_ascii=False)
            elif format.lower() == 'csv':
                df = pd.DataFrame(products)
                df.to_csv(filename, index=False, encoding='utf-8-sig')
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            logger.info(f"💾 Results saved to: {filename}")
            return filename
        except Exception as e:
            logger.error(f"❌ Error saving results: {e}")
            return None

    def print_simple_summary(self, products):
        """Resumen simple y claro"""
        if not products:
            print("❌ No products found")
            return
        
        print(f"\n{'='*50}")
        print(f"🎯 SIMPLE ALIBABA SCRAPER RESULTS")
        print(f"{'='*50}")
        print(f"📊 Total products: {len(products)}")
        
        # Estadísticas rápidas MEJORADAS
        with_prices = [p for p in products if p.get('price')]
        with_reviews = [p for p in products if p.get('product_review_count')]
        with_certifications = [p for p in products if p.get('product_certifications') and len(p.get('product_certifications', [])) > 0]
        with_images = [p for p in products if p.get('image_link')]
        verified_suppliers = [p for p in products if p.get('supplier_verified')]
        
        print(f"💰 With prices: {len(with_prices)}/{len(products)} ({len(with_prices)/len(products)*100:.1f}%)")
        print(f"⭐ With reviews: {len(with_reviews)}/{len(products)} ({len(with_reviews)/len(products)*100:.1f}%)")
        print(f"📜 With certifications: {len(with_certifications)}/{len(products)} ({len(with_certifications)/len(products)*100:.1f}%)")
        print(f"🖼️ With images: {len(with_images)}/{len(products)} ({len(with_images)/len(products)*100:.1f}%)")
        print(f"✅ Verified suppliers: {len(verified_suppliers)}/{len(products)} ({len(verified_suppliers)/len(products)*100:.1f}%)")
        
        # Certificaciones más comunes
        if with_certifications:
            all_certs = []
            for p in with_certifications:
                all_certs.extend(p.get('product_certifications', []))
            from collections import Counter
            cert_counts = Counter(all_certs)
            print(f"📋 Top certifications: {', '.join([f'{c}({n})' for c, n in cert_counts.most_common(3)])}")
        
        if with_prices:
            prices = [p['price'] for p in with_prices]
            print(f"💵 Price range: ${min(prices):.2f} - ${max(prices):.2f}")
            print(f"💵 Average price: ${sum(prices)/len(prices):.2f}")
        
        if with_reviews:
            reviews = [p['product_review_count'] for p in with_reviews]
            ratings = [p['product_review_avg'] for p in with_reviews if p.get('product_review_avg')]
            print(f"🌟 Reviews range: {min(reviews)} - {max(reviews)}")
            if ratings:
                print(f"🌟 Average rating: {sum(ratings)/len(ratings):.1f}/5.0")
        
        print(f"{'='*50}\n")

def main():
    parser = argparse.ArgumentParser(description='SIMPLE Alibaba Product Scraper')
    parser.add_argument('query', help='Search query for Alibaba products')
    parser.add_argument('--output', '-o', help='Output filename')
    parser.add_argument('--format', '-f', choices=['csv', 'json'], default='json')
    parser.add_argument('--show-sample', '-s', type=int, default=3, help='Show N sample products')
    args = parser.parse_args()

    scraper = SimpleAlibabaProductScraper()
    products = scraper.search_products(args.query)
    
    if not products:
        print("❌ No products found or error occurred.")
        sys.exit(1)

    scraper.print_simple_summary(products)
    
    if args.show_sample > 0:
        print(f"📋 Sample products (showing first {min(args.show_sample, len(products))}):")
        for i, p in enumerate(products[:args.show_sample], 1):
            print(f"\n--- Product {i} ---")
            print(f"  📦 {p.get('product_title', 'N/A')[:80]}...")
            print(f"  💰 ${p.get('price', 0):.2f}")
            print(f"  ⭐ {p.get('product_review_avg', 0):.1f}/5.0 ({p.get('product_review_count', 0)} reviews)")
            
            # Certificaciones
            certs = p.get('product_certifications', [])
            if certs:
                print(f"  📜 Certifications: {', '.join(certs[:3])}{'...' if len(certs) > 3 else ''}")
            
            # Imagen
            if p.get('image_link'):
                print(f"  🖼️ Image: Yes")
            
            print(f"  🏭 {p.get('supplier_name', 'N/A')}")
            print(f"  ✅ Verified: {p.get('supplier_verified', False)}")
            print(f"  📦 MOQ: {p.get('moq_value', 0)} {p.get('moq_unit', 'pieces')}")
            
            # Características adicionales
            if p.get('est_delivery_by'):
                print(f"  🚚 Delivery: {p.get('est_delivery_by')}")
            if p.get('has_easy_return'):
                print(f"  🔄 Easy return available")

    filename = scraper.save_results(products, args.output, args.format)
    if filename:
        print(f"\n💾 Results saved to: {filename}")
    
    print(f"\n🎉 Simple scraping completed successfully!")

if __name__ == "__main__":
    main()
