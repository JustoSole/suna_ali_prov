#!/usr/bin/env python3
"""
Suna Solutions Proveedores IA - Entry Point
==========================================
"""

import streamlit as st

# Configuración de página (debe ser lo primero)
st.set_page_config(
    page_title="Suna Solutions Proveedores IA",
    page_icon="🏭", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import y ejecutar aplicación principal
try:
    # Import directo sin path manipulation
    import sourcing_app_clean
    
    # Ejecutar la aplicación
    sourcing_app_clean.main_streamlit()
    
except ImportError as e:
    st.error("❌ Error de importación")
    st.error(f"Detalles: {str(e)}")
    st.info("🔧 Contacta al administrador si el problema persiste")
    
except Exception as e:
    st.error("❌ Error ejecutando la aplicación")
    st.error(f"Detalles: {str(e)}")
    st.info("🔧 Contacta al administrador si el problema persiste")
