import streamlit as st
import pandas as pd
from supabase import create_client
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Inicializar cliente de Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Configuración de la página
st.set_page_config(page_title="Database Statistics", page_icon="📊")
st.title("Database Statistics Dashboard")

# Función para obtener datos de Supabase
def get_data(table_name):
    response = supabase.table(table_name).select("*").execute()
    return pd.DataFrame(response.data)

# Sidebar para selección de tabla
st.sidebar.title("Settings")
# Aquí debes reemplazar con los nombres reales de tus tablas
table_names = ["tabla1", "tabla2", "tabla3"]  
selected_table = st.sidebar.selectbox("Select table", table_names)

try:
    # Cargar datos
    df = get_data(selected_table)
    
    # Mostrar estadísticas generales
    st.header("General Statistics")
    st.write(f"Total records: {len(df)}")
    
    # Mostrar estadísticas numéricas
    st.header("Numerical Statistics")
    st.write(df.describe())
    
    # Mostrar distribución de datos categóricos
    st.header("Categorical Data Distribution")
    for column in df.select_dtypes(include=['object']).columns:
        st.subheader(f"Distribution of {column}")
        value_counts = df[column].value_counts()
        st.bar_chart(value_counts)
    
    # Mostrar los últimos registros
    st.header("Latest Records")
    st.dataframe(df.tail())

except Exception as e:
    st.error(f"Error accessing the database: {str(e)}")