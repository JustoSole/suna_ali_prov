# 🏭 Sourcing Triads Pro

**Plataforma profesional para análisis inteligente de productos Alibaba con sincronización automática a Google Sheets**

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://your-app-url.streamlit.app)

## ✨ Características

- 🔍 **Scraping Avanzado**: Extracción automática de productos de Alibaba
- 📊 **Análisis Inteligente**: Algoritmos para encontrar las mejores oportunidades  
- 🏆 **Sistema de Tríadas**: Cheapest, Best Quality, Best Value
- 📋 **Google Sheets**: Exportación automática con fórmulas profesionales
- 🎯 **Filtros de Calidad**: Proveedores verificados, ratings, certificaciones
- 🖼️ **Visualización Rica**: Imágenes de productos extraídas automáticamente
- 💰 **Cálculo de Precios**: Precios landed con multiplicadores personalizables

## 🚀 Demo en Vivo

Visita la aplicación desplegada: **[Sourcing Triads Pro](https://your-app-url.streamlit.app)**

## 📦 Instalación Local

### Prerrequisitos

- Python 3.8+
- Cuenta de Google Cloud con Sheets API habilitada
- Token de Apify (opcional, para scraping avanzado)

### Pasos de Instalación

1. **Clonar el repositorio**
   ```bash
   git clone https://github.com/JustoSole/suna_ali_prov.git
   cd suna_ali_prov
   ```

2. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configurar secretos**
   - Copia `.streamlit/secrets.toml.example` a `.streamlit/secrets.toml`
   - Configura tus credenciales (ver sección de configuración)

4. **Ejecutar la aplicación**
   ```bash
   streamlit run app.py
   ```

## ⚙️ Configuración

### Google Sheets API

1. **Crear proyecto en Google Cloud Console**
   - Ve a [Google Cloud Console](https://console.cloud.google.com)
   - Crea un nuevo proyecto o selecciona uno existente
   - Habilita la Google Sheets API

2. **Crear cuenta de servicio**
   - Ve a "IAM & Admin" > "Service Accounts"
   - Crea una nueva cuenta de servicio
   - Descarga las credenciales JSON

3. **Configurar en Streamlit**
   ```toml
   [google_credentials]
   type = "service_account"
   project_id = "tu-project-id"
   private_key_id = "tu-private-key-id"
   private_key = "-----BEGIN PRIVATE KEY-----\\ntu-private-key\\n-----END PRIVATE KEY-----\\n"
   client_email = "tu-email@tu-project.iam.gserviceaccount.com"
   client_id = "tu-client-id"
   auth_uri = "https://accounts.google.com/o/oauth2/auth"
   token_uri = "https://oauth2.googleapis.com/token"
   auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
   client_x509_cert_url = "tu-cert-url"
   ```

### Configuración de Secrets

En `.streamlit/secrets.toml`:

```toml
[apify]
token = "tu-apify-token"

[openai]
api_key = "tu-openai-key"

[google_sheets]
spreadsheet_id = "tu-spreadsheet-id"

[app]
max_products = 50
default_multiplier = 3.0
```

### Deploy en Streamlit Cloud

1. **Fork del repositorio**
   - Haz fork de este repositorio en tu cuenta de GitHub

2. **Conectar a Streamlit Cloud**
   - Ve a [share.streamlit.io](https://share.streamlit.io)
   - Conecta tu repositorio de GitHub
   - Selecciona `app.py` como archivo principal

3. **Configurar secretos**
   - En Streamlit Cloud, ve a "Secrets"
   - Pega el contenido de tu `secrets.toml`

## 📖 Uso

### Búsqueda de Productos

1. **Selecciona el modo de búsqueda**:
   - 📁 **Datos locales**: Usa archivos JSON/CSV existentes
   - 🌐 **Búsqueda directa**: Scraping en tiempo real de Alibaba

2. **Configura los parámetros**:
   - Queries de búsqueda (separadas por coma)
   - Top N candidatos
   - Multiplicador landed
   - Filtros de calidad

3. **Analiza los resultados**:
   - Visualiza la tríada de productos recomendados
   - Revisa la tabla completa con imágenes
   - Exporta a Google Sheets

### Sistema de Tríadas

- **💰 MÁS BARATO**: Precio más bajo del mercado
- **⭐ MEJOR CALIDAD**: Mejor proveedor por rating y verificación  
- **💎 MEJOR VALOR**: Equilibrio óptimo precio-calidad

### Filtros de Calidad

- ✅ **Solo proveedores verificados**
- 📝 **Mínimo de reviews requeridas**
- 🏷️ **Solo productos con certificaciones**

## 🔧 Desarrollo

### Estructura del Proyecto

```
suna_ali_prov/
├── app.py                    # Punto de entrada principal
├── sourcing_app_clean.py     # Lógica principal de la aplicación
├── alibaba_scraper.py        # Scraper de Alibaba
├── google_sheets_exporter.py # Exportador a Google Sheets
├── config.py                 # Configuración y secretos
├── requirements.txt          # Dependencias
└── .streamlit/
    └── secrets.toml         # Configuración de secretos
```

### Contribuir

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📊 Características Técnicas

- **Framework**: Streamlit
- **Web Scraping**: BeautifulSoup4, Requests
- **Análisis de Datos**: Pandas
- **APIs**: Google Sheets API, Apify
- **Procesamiento de Imágenes**: Extracción automática de URLs
- **Normalización de Precios**: Soporte para formatos europeos/americanos

## 🛠️ Troubleshooting

### Errores Comunes

**❌ Error: No se encontró archivo de credenciales**
- Verifica que `google_credentials` esté configurado en `secrets.toml`
- Asegúrate de que las credenciales JSON sean válidas

**❌ Error: Scraper no disponible**
- Verifica que todos los archivos estén presentes
- Revisa los logs para más detalles

**❌ Error: Google Sheets no configurado**
- Habilita la Sheets API en Google Cloud
- Verifica las credenciales de la cuenta de servicio

### Soporte

Para soporte o preguntas:
- Abre un [Issue](https://github.com/JustoSole/suna_ali_prov/issues)
- Contacta al desarrollador

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para detalles.

## 🙏 Reconocimientos

- **Streamlit**: Framework de aplicaciones web
- **Alibaba**: Fuente de datos de productos
- **Google Sheets API**: Integración de hojas de cálculo
- **BeautifulSoup**: Web scraping

---

**Desarrollado con ❤️ para profesionales del sourcing**

*Powered by Streamlit & Google Sheets API*