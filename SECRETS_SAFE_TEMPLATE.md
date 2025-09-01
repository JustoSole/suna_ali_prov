# 🔐 Template Seguro de Secrets para Streamlit Cloud

Este archivo contiene el template seguro para configurar los secrets en Streamlit Cloud.

## 📋 Instrucciones

1. Ve a tu app en Streamlit Cloud
2. Settings → Secrets
3. Copia y pega el contenido de abajo
4. **IMPORTANTE:** Reemplaza TODOS los valores con tus credenciales reales

## 🔑 Template de Configuración

```toml
[apify]
token = "REEMPLAZAR_CON_TU_APIFY_TOKEN"

[openai]
api_key = "REEMPLAZAR_CON_TU_OPENAI_API_KEY"

[meli]
client_id = "REEMPLAZAR_CON_TU_MELI_CLIENT_ID"
client_secret = "REEMPLAZAR_CON_TU_MELI_CLIENT_SECRET"

[google_sheets]
spreadsheet_id = "REEMPLAZAR_CON_TU_GOOGLE_SHEETS_ID"

[app]
max_products = 50
default_multiplier = 3.0

# 🚨 IMPORTANTE: Reemplazar con valores reales del archivo JSON de Google Cloud
[google_credentials]
type = "service_account"
project_id = "REEMPLAZAR_CON_TU_PROJECT_ID"
private_key_id = "REEMPLAZAR_CON_TU_PRIVATE_KEY_ID"
private_key = "-----BEGIN PRIVATE KEY-----\nREEMPLAZAR_CON_TU_PRIVATE_KEY\n-----END PRIVATE KEY-----\n"
client_email = "REEMPLAZAR_CON_TU_SERVICE_ACCOUNT_EMAIL"
client_id = "REEMPLAZAR_CON_TU_CLIENT_ID"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "REEMPLAZAR_CON_TU_CERT_URL"
```

## ⚠️ Notas Importantes

1. **Private Key**: Debe mantener los `\n` para los saltos de línea
2. **Client Email**: Debe ser el email de la service account que creaste
3. **Spreadsheet ID**: Obténlo de la URL de tu Google Sheet
4. **Espacios**: No uses espacios extra alrededor de los `=`

## 🔍 Cómo obtener las credenciales de Google

1. [Google Cloud Console](https://console.cloud.google.com) → Tu proyecto
2. APIs & Services → Credentials → Service Accounts
3. Crea nueva service account → Download JSON
4. Abre el JSON y copia cada campo al template de arriba

## ✅ Verificación

Después de configurar, verifica que la app muestre:
- ✅ "Google Sheets disponible" en la sidebar
- ❌ Si sale "Google Sheets no configurado", revisa las credenciales

## 💡 Para tokens de prueba

Consulta el archivo `CONFIGURACION_REAL.md` (no incluido en el repositorio por seguridad) para obtener valores de prueba válidos.
