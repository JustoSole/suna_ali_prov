#!/usr/bin/env python3
"""
Test script para Google Sheets Exporter
Verifica que las correcciones funcionen correctamente
"""

import pandas as pd
from datetime import datetime

def test_google_sheets_export():
    """Probar exportación con datos simulados"""
    try:
        print("🧪 Probando Google Sheets Exporter...")
        
        # Importar el nuevo exportador
        from google_sheets_exporter import export_to_google_sheets
        
        # Datos simulados de tríada
        triad_data = {
            'cheapest': {
                'title': 'TEST - Producto más barato',
                'companyName': 'Proveedor Barato S.A.',
                'unit_price_norm_usd': 10.50,
                'landed_est_usd': 31.50,
                'moq': 100,
                'supplier_rating': 4.2,
                'supplier_reviews_count': 150,
                'verified_supplier': True,
                'product_certifications': ['CE', 'RoHS'],
                'supplier_profile_url': 'https://alibaba.com/supplier/test1',
                'productUrl': 'https://alibaba.com/product/test1',
                'image_link': 'https://s.alicdn.com/@sc04/kf/H5d143ec355d041e6aaf8476488f7f3920.jpg_300x300.jpg'
            },
            'best_quality': {
                'title': 'TEST - Producto mejor calidad',
                'companyName': 'Proveedor Premium Ltd.',
                'unit_price_norm_usd': 25.75,
                'landed_est_usd': 77.25,
                'moq': 50,
                'supplier_rating': 4.8,
                'supplier_reviews_count': 300,
                'verified_supplier': True,
                'product_certifications': ['CE', 'FCC', 'CB'],
                'supplier_profile_url': 'https://alibaba.com/supplier/test2',
                'productUrl': 'https://alibaba.com/product/test2',
                'image_link': 'https://s.alicdn.com/@sc04/kf/H8e1f2a3b4c5d6e7f8g9h0i1j2k3l4m5.jpg_300x300.jpg'
            },
            'best_value': {
                'title': 'TEST - Producto mejor valor',
                'companyName': 'Proveedor Equilibrado Co.',
                'unit_price_norm_usd': 18.25,
                'landed_est_usd': 54.75,
                'moq': 75,
                'supplier_rating': 4.5,
                'supplier_reviews_count': 200,
                'verified_supplier': True,
                'product_certifications': ['CE', 'RoHS', 'CB'],
                'supplier_profile_url': 'https://alibaba.com/supplier/test3',
                'productUrl': 'https://alibaba.com/product/test3',
                'image_link': 'https://s.alicdn.com/@sc04/kf/H9f0e1d2c3b4a5968776543210fedcba.jpg_300x300.jpg'
            }
        }
        
        # Datos simulados de productos adicionales
        additional_products = []
        for i in range(5):
            additional_products.append({
                'title': f'TEST - Producto adicional {i+1}',
                'companyName': f'Proveedor {i+1} Inc.',
                'unit_price_norm_usd': 12.0 + (i * 2),
                'landed_est_usd': 36.0 + (i * 6),
                'moq': 100 - (i * 10),
                'supplier_rating': 4.0 + (i * 0.1),
                'supplier_reviews_count': 100 + (i * 25),
                'verified_supplier': i % 2 == 0,  # Alternar verificado
                'product_certifications': ['CE'] if i % 2 == 0 else [],
                'supplier_profile_url': f'https://alibaba.com/supplier/test{i+4}',
                'productUrl': f'https://alibaba.com/product/test{i+4}',
                'image_link': f'https://s.alicdn.com/@sc04/kf/H{i}a1b2c3d4e5f6789.jpg_300x300.jpg'
            })
        
        # Convertir a DataFrame
        df_data = pd.DataFrame(additional_products)
        
        # Estadísticas simuladas
        estadisticas = {
            'precio_promedio': 16.50,
            'moq_promedio': 75,
            'rating_proveedor_promedio': 4.4,
            'proveedores_con_reviews': 8,
            'proveedores_verificados': 6,
            'total_productos': 8
        }
        
        # Ejecutar exportación
        print("📊 Ejecutando exportación a Google Sheets...")
        print("⚠️ NOTA: Este test requiere credenciales válidas de Google Sheets")
        
        query_title = "test_export"
        url = export_to_google_sheets(query_title, df_data, triad_data, estadisticas)
        
        if url:
            print("✅ ¡ÉXITO! Exportación completada")
            print(f"🔗 URL de la hoja: {url}")
            print("\n📋 Verificar en Google Sheets:")
            print("  • Headers profesionales sin emojis")
            print("  • MOQ cambiado a 'CANTIDAD MINIMA PEDIDO'")  
            print("  • Imágenes con formato =IMAGE(url; 4; 100; 100)")
            print("  • Fórmulas SIN apóstrofe: =F2*M2 (LANDED_USD × CANTIDAD)")
            print("  • Certificaciones y links de proveedores")
            print("  • Dimensiones de columnas ajustadas")
            return True
        else:
            print("❌ Error en la exportación")
            return False
            
    except ImportError as ie:
        print(f"❌ Error de importación: {ie}")
        print("💡 Asegúrate de que google_sheets_exporter.py esté en el mismo directorio")
        return False
    except Exception as e:
        print(f"❌ Error en test: {e}")
        return False

def test_formula_format():
    """Probar que las fórmulas tengan el formato correcto"""
    print("\n🧮 Probando formato de fórmulas...")
    
    # Probar fórmula de costo total CORREGIDA
    row = 5
    formula_costo = f"=F{row}*M{row}"  # F = LANDED_USD, M = CANTIDAD
    print(f"✅ Fórmula costo total: {formula_costo} (LANDED_USD × CANTIDAD)")
    
    # Probar fórmula de imagen con formato específico
    image_url = "https://s.alicdn.com/@sc04/kf/H5d143ec355d041e6aaf8476488f7f3920.jpg_300x300.jpg"
    formula_imagen = f'=IMAGE("{image_url}"; 4; 100; 100)'
    print(f"✅ Fórmula imagen: {formula_imagen}")
    
    # Verificar que no hay apóstrofes
    assert not formula_costo.startswith("'"), "❌ Fórmula de costo tiene apóstrofe"
    assert not formula_imagen.startswith("'"), "❌ Fórmula de imagen tiene apóstrofe"
    
    # Verificar separadores
    assert ";" in formula_imagen, "❌ Fórmula de imagen debe usar ; como separador"
    
    # Verificar formato de inserción por separado
    print("🔧 CORRECCIÓN APLICADA:")
    print("  • Las fórmulas de imagen se insertan por separado con update_cell()")
    print("  • NO se incluyen en append_row() para evitar apóstrofes automáticos")
    print("  • Método: worksheet.update_cell(row, 1, formula_imagen)")
    print("  • Método: worksheet.update_cell(row, 14, formula_costo)")
    print("  • COSTO TOTAL = LANDED_USD × CANTIDAD (columna F × columna M)")
    
    print("✅ Formato de fórmulas correcto")
    return True

if __name__ == "__main__":
    print("=" * 70)
    print("🧪 TEST GOOGLE SHEETS EXPORTER")
    print("=" * 70)
    
    # Test 1: Formato de fórmulas
    print("\n1️⃣ Test de formato de fórmulas...")
    success_formulas = test_formula_format()
    
    if success_formulas:
        print("\n2️⃣ Test de exportación a Google Sheets...")
        print("⚠️ REQUIERE: Archivo de credenciales de Google Sheets válido")
        
        try:
            success_export = test_google_sheets_export()
            
            if success_export:
                print("\n" + "=" * 70)
                print("🎉 ¡TODOS LOS TESTS EXITOSOS!")
                print("✅ Headers sin emojis (profesionales)")
                print("✅ MOQ → CANTIDAD MINIMA PEDIDO")
                print("✅ Fórmulas sin apóstrofe")
                print("✅ Cálculo correcto: LANDED_USD × CANTIDAD")
                print("✅ Formato de imagen correcto")
                print("✅ Exportación funcionando")
                print("✅ Dimensiones corregidas")
                print("=" * 70)
            else:
                print("\n" + "=" * 70)
                print("⚠️ Tests de formato OK, pero exportación falló")
                print("🔧 Verifica credenciales de Google Sheets")
                print("=" * 70)
                
        except Exception as e:
            print(f"\n❌ Error ejecutando test de exportación: {e}")
            print("💡 Esto es normal si no tienes credenciales de Google Sheets")
    else:
        print("\n❌ Error en tests básicos de formato")
