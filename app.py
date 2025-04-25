import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from supabase import create_client
import os
from dotenv import load_dotenv
import uuid
from datetime import datetime
import chrono

# Cargar variables de entorno
load_dotenv()

# Configuración de Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Configuración de la página
st.set_page_config(page_title="Enhanced Database Statistics", page_icon="📊", layout="wide")
st.title("Estadísticas de bases de datos")

# Función para parsear fechas de manera segura
def safe_parse_date(date_str):
    if pd.isna(date_str) or date_str == '':
        return None
    try:
        return chrono.parse_date(str(date_str))
    except:
        return None

# Función para obtener datos de Supabase
@st.cache_data
def get_data(table_name):
    try:
        response = supabase.table(table_name).select("*").execute()
        if not response.data:
            st.error("No data returned from Supabase.")
            return pd.DataFrame()
        df = pd.DataFrame(response.data)
        
        # Convertir fechas
        df['fecha_contacto'] = df['fecha_contacto'].apply(safe_parse_date)
        df['fecha_ultima_compra'] = df['fecha_ultima_compra'].apply(safe_parse_date)
        
        # Asegurar tipos de datos
        numeric_cols = ['cantidad_ovas_compradas', 'monto_total_gastado', 'dias_desde_ultima_compra']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Convertir columnas categóricas
        df['estatus_llamada'] = df['estatus_llamada'].astype('category')
        df['cotizacion'] = df['cotizacion'].astype('category')
        df['periodo_compra'] = df['periodo_compra'].astype('category')
        
        return df
    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")
        return pd.DataFrame()

# Función para detectar outliers usando IQR
def detect_outliers(df, column):
    Q1 = df[column].quantile(0.25)
    Q3 = df[column].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    outliers = df[(df[column] < lower_bound) | (df[column] > upper_bound)][column]
    return outliers

# Sidebar para selección de tabla y filtros
st.sidebar.title("Opciones")
table_names = ["compras"]
selected_table = st.sidebar.selectbox("Select table", table_names)
estatus_filter = st.sidebar.multiselect("estatus_llamada", ["CONTESTO", "NO CONTESTO"], default=["CONTESTO", "NO CONTESTO"])
cotizacion_filter = st.sidebar.multiselect("cotizacion", [0, 1], default=[0, 1])

# Cargar datos
df = get_data(selected_table)

if not df.empty:
    # Aplicar filtros
    filtered_df = df[
        (df['estatus_llamada'].isin(estatus_filter)) &
        (df['cotizacion'].isin(cotizacion_filter))
    ]
    
    # Mostrar métricas generales
    st.header("Estadisticos")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Records", len(filtered_df))
    col2.metric("Unique Clients", filtered_df['id_cliente'].nunique())
    col3.metric("Earliest Contact", filtered_df['fecha_contacto'].min().strftime('%Y-%m-%d') if filtered_df['fecha_contacto'].notna().any() else "N/A")
    col4.metric("Latest Contact", filtered_df['fecha_contacto'].max().strftime('%Y-%m-%d') if filtered_df['fecha_contacto'].notna().any() else "N/A")
    
    # Verificar valores duplicados
    st.header("calidad datos")
    duplicates = filtered_df[filtered_df.duplicated(subset=['id_seguimiento'], keep=False)]
    st.subheader("valores duplicados ( id_seguimiento)")
    if not duplicates.empty:
        st.write(f"Found {len(duplicates)} duplicated records.")
        st.dataframe(duplicates)
    else:
        st.write("No duplicated records found.")
    
    # Verificar valores nulos
    st.subheader("valores nulos")
    null_counts = filtered_df.isnull().sum()
    null_df = pd.DataFrame({'Column': null_counts.index, 'Null Count': null_counts.values})
    st.dataframe(null_df[null_df['Null Count'] > 0])
    
    # Estadísticas numéricas
    st.header("Estdisticas Numericas")
    numeric_cols = ['cantidad_ovas_compradas', 'monto_total_gastado', 'dias_desde_ultima_compra']
    st.dataframe(filtered_df[numeric_cols].describe())
    
    # Detectar outliers
    st.subheader("Outliers ")
    for col in numeric_cols:
        outliers = detect_outliers(filtered_df, col)
        st.write(f"Outliers in {col}: {len(outliers)}")
        if not outliers.empty:
            fig, ax = plt.subplots()
            sns.boxplot(x=filtered_df[col], ax=ax)
            ax.set_title(f"Box Plot of {col}")
            st.pyplot(fig)
    
    # Distribuciones categóricas
    st.header("Categorical Data Distribution")
    categorical_cols = ['estatus_llamada', 'cotizacion', 'periodo_compra']
    for col in categorical_cols:
        st.subheader(f"Distribution of {col}")
        value_counts = filtered_df[col].value_counts()
        fig, ax = plt.subplots()
        value_counts.plot(kind='bar', ax=ax)
        ax.set_title(f"Distribution of {col}")
        ax.set_xlabel(col)
        ax.set_ylabel("Count")
        st.pyplot(fig)
    
    # Histogramas para columnas numéricas
    st.header("Numerical Data Distribution")
    for col in numeric_cols:
        st.subheader(f"Histogram of {col}")
        fig, ax = plt.subplots()
        sns.histplot(filtered_df[col].dropna(), bins=30, ax=ax)
        ax.set_title(f"Histogram of {col}")
        ax.set_xlabel(col)
        ax.set_ylabel("Frequency")
        st.pyplot(fig)
    
    
    # Insights adicionales
    st.header("Additional Insights")
    # Clientes con múltiples registros
    client_counts = filtered_df['id_cliente'].value_counts()
    repeated_clients = client_counts[client_counts > 1]
    st.subheader("Clients with Multiple Records")
    if not repeated_clients.empty:
        st.write(f"Found {len(repeated_clients)} clients with multiple records.")
        st.dataframe(repeated_clients)
    else:
        st.write("No clients with multiple records.")
    
    # Registros sin compras
    no_purchases = filtered_df[filtered_df['cantidad_ovas_compradas'] == 0]
    st.subheader("Records with No Purchases")
    st.write(f"Found {len(no_purchases)} records with zero purchases.")
    if not no_purchases.empty:
        st.dataframe(no_purchases.head())
    
    # Registros con última compra antigua
    old_purchases = filtered_df[filtered_df['dias_desde_ultima_compra'] > 1000]
    st.subheader("Records with Last Purchase > 1000 Days Ago")
    st.write(f"Found {len(old_purchases)} records with last purchase over 1000 days ago.")
    if not old_purchases.empty:
        st.dataframe(old_purchases.head())
    
    # Mostrar datos crudos
    st.header("Raw Data")
    st.dataframe(filtered_df)

else:
    st.error("No data available to display.")
