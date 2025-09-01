# 🏭 Sourcing Triads Pro

**Análisis profesional de productos Alibaba con scraping en tiempo real**

## 🚀 Deployment en Streamlit Cloud

1. **Conecta el repositorio**: `JustoSole/suna_ali_prov`
2. **Archivo principal**: `app.py`
3. **Configura secrets** en Streamlit Cloud:

```toml
[apify]
token = "tu_apify_token"

[openai]
api_key = "tu_openai_key"

[meli]
client_id = "tu_meli_client_id"
client_secret = "tu_meli_client_secret"

[oxylabs]
username = "tu_oxylabs_username"
password = "tu_oxylabs_password"

[google_sheets]
spreadsheet_id = "tu_google_sheets_id"

[google_service_account]
credentials = """{
  "type": "service_account",
  "project_id": "tu_project_id",
  "private_key_id": "tu_private_key_id",
  "private_key": "-----BEGIN PRIVATE KEY-----\\ntu_private_key\\n-----END PRIVATE KEY-----\\n",
  "client_email": "tu_service_account_email",
  "client_id": "tu_client_id",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "tu_cert_url",
  "universe_domain": "googleapis.com"
}"""

[app]
max_products = 50
default_multiplier = 3.0
```

## ✨ Funcionalidades

- 🔍 **Scraping en tiempo real** de productos Alibaba
- 🏆 **Sistema de tríadas**: Cheapest, Best Quality, Best Value
- 📊 **Análisis inteligente** con algoritmos de scoring
- 🖼️ **Visualización rica** con imágenes de productos
- 📋 **Exportación automática** a Google Sheets
- 🎯 **Filtros avanzados** por calidad y certificaciones

## 🔧 Google Sheets Setup

1. [Google Cloud Console](https://console.cloud.google.com) → Crear proyecto
2. Habilitar **Google Sheets API**
3. Crear **Service Account** → Descargar JSON
4. Copiar credenciales JSON a `google_credentials` en secrets
5. Crear Google Sheet → Compartir con email de service account

---

**¡Tu herramienta profesional de sourcing está lista!** 🚀
