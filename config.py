#!/usr/bin/env python3
"""
Config module for Streamlit deployment
=====================================
Handles secrets and configuration from Streamlit secrets.toml
"""

import streamlit as st
import os
from typing import Optional

def get_apify_token() -> str:
    """Obtener token de Apify desde Streamlit secrets o env vars"""
    try:
        return st.secrets["apify"]["token"]
    except (KeyError, AttributeError):
        return os.getenv('APIFY_TOKEN', '')

def get_openai_key() -> str:
    """Obtener API key de OpenAI desde Streamlit secrets o env vars"""
    try:
        return st.secrets["openai"]["api_key"]
    except (KeyError, AttributeError):
        return os.getenv('OPENAI_API_KEY', '')

def get_meli_client_id() -> str:
    """Obtener Client ID de MercadoLibre desde Streamlit secrets o env vars"""
    try:
        return st.secrets["meli"]["client_id"]
    except (KeyError, AttributeError):
        return os.getenv('MELI_CLIENT_ID', '1002015801056145')

def get_meli_client_secret() -> str:
    """Obtener Client Secret de MercadoLibre desde Streamlit secrets o env vars"""
    try:
        return st.secrets["meli"]["client_secret"]
    except (KeyError, AttributeError):
        return os.getenv('MELI_CLIENT_SECRET', 'C4zpjYsz19K1NaltbU3IWbdWGTYCwsVL')

def get_google_sheets_spreadsheet_id() -> str:
    """Obtener ID del spreadsheet de Google Sheets"""
    try:
        return st.secrets["google_sheets"]["spreadsheet_id"]
    except (KeyError, AttributeError):
        return "1rXxEqoDyGo5RIIowyvHjuIlKnJ18QjX7ewleY1PfI4w"

def get_google_credentials() -> Optional[dict]:
    """Obtener credenciales de Google desde Streamlit secrets"""
    try:
        # En Streamlit Cloud, las credenciales se configuran como un dict completo
        return st.secrets["google_credentials"]
    except (KeyError, AttributeError):
        return None

def get_app_config() -> dict:
    """Obtener configuración general de la app"""
    try:
        return {
            'max_products': st.secrets["app"]["max_products"],
            'default_multiplier': st.secrets["app"]["default_multiplier"]
        }
    except (KeyError, AttributeError):
        return {
            'max_products': 50,
            'default_multiplier': 3.0
        }
