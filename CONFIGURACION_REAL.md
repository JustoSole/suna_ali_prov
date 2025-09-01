# 🔐 Configuración Real de Secrets

**⚠️ ARCHIVO PRIVADO - NO SUBIR A GITHUB**

Este archivo contiene los tokens y keys reales para configurar la aplicación.

## 🔑 Tokens Reales para Streamlit Cloud

### Para desarrollo y testing (usar estos valores):

```toml
[apify]
token = "apify_api_[TOKEN_OCULTO_POR_SEGURIDAD]"

[openai]
api_key = "sk-proj-[OPENAI_KEY_OCULTA_POR_SEGURIDAD]"

[meli]
client_id = "1002015801056145"
client_secret = "C4zpjYsz19K1NaltbU3IWbdWGTYCwsVL"

[oxylabs]
username = "justo_[USERNAME_OCULTO]"
password = "[PASSWORD_OCULTO_POR_SEGURIDAD]"

[google_sheets]
spreadsheet_id = "1rXxEqoDyGo5RIIowyvHjuIlKnJ18QjX7ewleY1PfI4w"

[app]
max_products = 50
default_multiplier = 3.0
```

## 📋 Instrucciones de Uso

⚠️ **IMPORTANTE**: Los tokens arriba están ocultos por seguridad. 

**Para obtener los tokens reales**:
1. **Contacta al administrador del proyecto** para los valores completos
2. **Para Streamlit Cloud**: Usa los tokens reales en el panel de secrets
3. **Para Google Credentials**: Necesitas crear tu propio service account
4. **Para producción**: Considera usar tus propios tokens

## 🔒 APIs incluidas

- **Apify**: Para scraping alternativo
- **OpenAI**: Para funciones de AI (si se implementan)
- **MercadoLibre**: Para integración con ML
- **Oxylabs**: Para scraping principal de Alibaba
- **Google Sheets**: Para exportación de datos

## 🔒 Seguridad

- ✅ Este archivo no se sube al repositorio
- ✅ Todas las credenciales están configuradas
- ⚠️ Mantener privado siempre