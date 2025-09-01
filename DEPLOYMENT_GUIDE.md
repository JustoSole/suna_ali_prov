# 🚀 Guía de Deployment en Streamlit Cloud

## ✅ Repositorio Preparado

¡Perfecto! Tu proyecto **Sourcing Triads Pro** ya está listo para deployment en Streamlit Cloud. 

**Repositorio:** https://github.com/JustoSole/suna_ali_prov

## 📋 Pasos para Deploy en Streamlit Cloud

### 1. 🌐 Crear App en Streamlit Cloud

1. Ve a [share.streamlit.io](https://share.streamlit.io)
2. Inicia sesión con tu cuenta de GitHub
3. Haz click en **"New app"**
4. Selecciona:
   - **Repository:** `JustoSole/suna_ali_prov`
   - **Branch:** `main`
   - **Main file path:** `app.py`
   - **App URL:** (elige tu URL personalizada)

### 2. 🔐 Configurar Secrets

En Streamlit Cloud, ve a tu app → **Settings** → **Secrets** y pega esta configuración:

⚠️ **IMPORTANTE:** Reemplaza los valores con tus tokens reales (consulta CONFIGURACION_REAL.md para valores de prueba)

```toml
# Secrets para Streamlit Cloud
[apify]
token = "TU_APIFY_TOKEN_AQUI"

[openai]
api_key = "TU_OPENAI_API_KEY_AQUI"

[meli]
client_id = "TU_MELI_CLIENT_ID"
client_secret = "TU_MELI_CLIENT_SECRET"

[oxylabs]
username = "TU_OXYLABS_USERNAME"
password = "TU_OXYLABS_PASSWORD"

[google_sheets]
spreadsheet_id = "TU_GOOGLE_SHEETS_ID"

[app]
max_products = 50
default_multiplier = 3.0

# Google Credentials (IMPORTANTE: Configurar después)
[google_credentials]
type = "service_account"
project_id = "TU_PROJECT_ID"
private_key_id = "TU_PRIVATE_KEY_ID"
private_key = "-----BEGIN PRIVATE KEY-----\nTU_PRIVATE_KEY\n-----END PRIVATE KEY-----\n"
client_email = "TU_EMAIL@TU_PROJECT.iam.gserviceaccount.com"
client_id = "TU_CLIENT_ID"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "TU_CERT_URL"
```

### 3. 🔧 Configurar Google Sheets (Obligatorio)

#### A. Crear Proyecto en Google Cloud

1. Ve a [Google Cloud Console](https://console.cloud.google.com)
2. Crea un nuevo proyecto o selecciona uno existente
3. Habilita la **Google Sheets API**

#### B. Crear Service Account

1. Ve a **IAM & Admin** → **Service Accounts**
2. Crea nueva service account
3. Descarga el archivo JSON de credenciales
4. Abre el archivo JSON y copia cada campo al secrets.toml

#### C. Configurar Spreadsheet

1. Crea un nuevo Google Sheet
2. Copia el ID del spreadsheet (de la URL)
3. Reemplaza `spreadsheet_id` en secrets.toml
4. Comparte el sheet con el email de la service account

### 4. 🔧 Configurar Oxylabs (Para scraping en tiempo real)

**Oxylabs** es el servicio principal para scraping de Alibaba en tiempo real.

- **Username**: Usar el valor proporcionado
- **Password**: Usar el valor proporcionado  
- **Funcionalidad**: Permite búsquedas directas en Alibaba con extracción de imágenes y datos completos

### 5. 🎯 Deploy Final

1. Guarda los secrets en Streamlit Cloud
2. Haz click en **"Deploy!"**
3. Espera a que termine el deployment (2-3 minutos)
4. ¡Tu app estará lista!

## 🔍 Testing

### Funciones que puedes probar inmediatamente:
- ✅ **Scraping local**: Carga archivos JSON/CSV existentes
- ✅ **Análisis de tríadas**: Cheapest, Best Quality, Best Value
- ✅ **Filtros avanzados**: Proveedores verificados, certificaciones
- ✅ **Visualización rica**: Tablas con imágenes de productos

### Requiere configuración de Google:
- 📋 **Exportación a Google Sheets**: Necesita credenciales configuradas

## 🆘 Troubleshooting

### Error: "Missing Google Credentials"
- Verifica que todos los campos de `google_credentials` estén completos
- Asegúrate de que el service account tenga acceso al spreadsheet

### Error: "Module not found"
- Verifica que todos los archivos estén en el repositorio
- Redeployar la aplicación

### Error: "Secrets not found"
- Ve a Settings → Secrets en Streamlit Cloud
- Verifica que la sintaxis TOML sea correcta (sin espacios extra)

## 📊 Estructura Final del Proyecto

```
suna_ali_prov/
├── app.py                    # 🚀 Punto de entrada principal
├── sourcing_app_clean.py     # 🧠 Lógica principal
├── alibaba_scraper.py        # 🕷️ Web scraper
├── google_sheets_exporter.py # 📋 Exportador Google Sheets
├── config.py                 # ⚙️ Configuración
├── requirements.txt          # 📦 Dependencias
├── README.md                 # 📖 Documentación
├── .gitignore               # 🚫 Archivos ignorados
└── .streamlit/
    └── secrets.toml         # 🔐 NO incluido en repo
```

## 🎉 ¡Listo!

Tu aplicación **Sourcing Triads Pro** está preparada para production. Una vez completada la configuración de Google Sheets, tendrás una herramienta profesional completa para análisis de productos Alibaba.

### URL de tu app:
`https://tu-app-url.streamlit.app`

### Funcionalidades principales:
- 🔍 **Búsqueda avanzada** de productos Alibaba
- 📊 **Análisis inteligente** con algoritmos de scoring
- 🏆 **Sistema de tríadas** para mejores decisiones
- 📋 **Exportación automática** a Google Sheets
- 🎯 **Filtros de calidad** por proveedor y certificaciones

---

**¡Felicitaciones por tu nueva herramienta de sourcing profesional!** 🎯