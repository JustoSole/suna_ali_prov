#!/usr/bin/env python3
"""
Streamlit App - Main Entry Point
================================
Aplicación principal optimizada para deploy en Streamlit Cloud
"""

# Configuración inicial para deployment
import sys
from pathlib import Path

# Asegurar que el directorio actual esté en el path
current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))

# Imports principales
import streamlit as st

# Configuración de página (debe ser lo primero)
st.set_page_config(
    page_title="Sourcing Triads Pro",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import del módulo principal
try:
    from sourcing_app_clean import main_streamlit
    
    # Ejecutar la aplicación principal
    if __name__ == "__main__":
        main_streamlit()
        
except ImportError as e:
    st.error(f"❌ Error importando módulos: {e}")
    st.info("🔧 Verifica que todos los archivos necesarios estén presentes")
    st.stop()
except Exception as e:
    st.error(f"❌ Error ejecutando la aplicación: {e}")
    st.info("🔧 Por favor contacta al administrador")
    st.stop()
