import streamlit as st
import pandas as pd
import plotly.express as px
import openpyxl
from openpyxl.styles.colors import Color
from datetime import datetime
import re

# ---------------------------------------------------------
# FUNÇÕES AUXILIARES (Para Análise de Medicamentos)
# ---------------------------------------------------------

def get_color_info(cell):
    """Retorna informações detalhadas sobre a cor da célula para debug."""
    fill = cell.fill
    if not fill or not fill.start_color:
        return "Sem Preenchimento", None
    
    color = fill.start_color
    
    if color.type == 'rgb':
        return f"RGB: {color.rgb}", color.rgb
    if color.type == 'theme':
        return f"Tema: {color.theme} (Tint: {color.tint})", 'THEME'
    if color.type == 'indexed':
        return f"Index: {color.indexed}", 'INDEX'
        
    return "Outro", None

def is_green_smart(cell, wb):
    """Verifica se a célula é verde, tentando lidar com Temas e RGB."""
    fill = cell.fill
    if not fill or not fill.start_color:
        return False
    
    color = fill.start_color
    hex_code = None

    if color.type == 'rgb':
        hex_code = color.rgb 
    elif color.type == 'theme':
        # Temas comuns de verde/azul (Estimativa para temas do Excel)
        if color.theme in [5, 6, 9]: 
            return True 
        return False
        
    if hex_code:
        try:
            if len(hex_code) > 6:
                hex_code = hex_code[2:] 
            if len(hex_code) == 6:
                r = int(hex_code[0:2], 16)
                g = int(hex_code[2:4], 16)
                b = int(hex_code[4:6], 16)
                return g > r and g > b and g > 60
        except:
            pass
    return False

def parse_date(value):
    """Extrai data de strings ou objetos datetime."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{2,4})', value)
        if match:
            try:
                d, m, y = int(match.group(1)), int(match.group(2)), int(match.group(3))
                if y < 100: y += 2000
                return datetime(y, m, d).date()
            except:
                pass
    return None

# ---------------------------------------------------------
# CONFIGURAÇÃO GERAL DA PÁGINA
# ---------------------------------------------------------
st.set_page_config(page_title="Dashboard Integrado", layout="wide")

st.title("📊 Dashboard Integrado de Gestão")

# ---------------------------------------------------------
# MENU DE NAVEGAÇÃO LATERAL
# ---------------------------------------------------------
st.sidebar.title("Navegação")
pagina_selecionada = st.sidebar.radio(
    "Ir para:",
    ["📋 Análise de Coletas", "⚠️ Mapeamento de Riscos", "💊 Análise de Medicamentos"]
)
st.sidebar.markdown("---")

# =========================================================
# PÁGINA 1: ANÁLISE DE COLETAS POR COLABORADOR
# =========================================================
if pagina_selecionada == "📋 Análise de Coletas":
    st.header("Análise de Produtividade por Colaborador")
    st.markdown("Esta ferramenta analisa o arquivo de coletas (CSV) para contabilizar atendimentos.")

    uploaded_file_coletas = st.file_uploader("📂 Carregue o arquivo de Coletas (CSV) aqui", type=["csv"], key="upload_coletas")

    if uploaded_file_coletas:
        try:
            try:
                df_coletas = pd.read_csv(uploaded_file_coletas, sep=";", encoding='utf-8')
            except UnicodeDecodeError:
                uploaded_file_coletas.seek(0)
                df_coletas = pd.read_csv(uploaded_file_coletas, sep=";", encoding='latin1')
            
            if 'Usuário Nome' in df_coletas.columns and 'O.S.' in df_coletas.columns:
                resumo = df_coletas.groupby('Usuário Nome')['O.S.'].nunique().reset_index()
                resumo.columns = ['Colaborador', 'Qtd. Pacientes Atendidos']
                resumo_grafico = resumo.sort_values(by='Qtd. Pacientes Atendidos', ascending=True)
                resumo_tabela = resumo.sort_values(by='Qtd. Pacientes Atendidos', ascending=False).reset_index(drop=True)

                st.subheader("Resumo de Atendimentos")
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.write("**Tabela de Dados:**")
                    st.dataframe(
                        resumo_tabela,
                        use_container_width=True,
                        hide_index=True,
                        height=500,
                        column_config={
                            "Qtd. Pacientes Atendidos": st.column_config.NumberColumn(
                                "Qtd. Pacientes",
                                help="Número total de pacientes únicos atendidos",
                                format="%d"
                            )
                        }
                    )
                    
                with col2:
                    st.write("**Gráfico Visual:**")
                    fig = px.bar(
                        resumo_grafico, 
                        x='Qtd. Pacientes Atendidos', 
                        y='Colaborador', 
                        orientation='h', 
                        text_auto=True,
                        title="Pacientes Atendidos por Colaborador"
                    )
                    
                    fig.update_layout(
                        xaxis_title="Quantidade de Pacientes",
                        yaxis_title="Colaborador",
                        showlegend=False,
                        height=500,
                        margin=dict(r=50)
                    )
                    fig.update_traces(textposition='outside', cliponaxis=False)
                    st.plotly_chart(fig, use_container_width=True)

                st.markdown("---")

                st.subheader("🔎 Detalhes por Colaborador")
                st.info("Selecione um colaborador abaixo para ver a lista detalhada.")

                lista_colaboradores = resumo_tabela['Colaborador'].unique()
                colaborador_selecionado = st.selectbox("Escolha o Colaborador:", lista_colaboradores)

                if colaborador_selecionado:
                    df_filtrado = df_coletas[df_coletas['Usuário Nome'] == colaborador_selecionado].copy()
                    
                    colunas_detalhe = ['Data da Operação', 'O.S.', 'Paciente', 'Paciente Nome', 'Detalhe Descrição']
                    cols_existentes = [c for c in colunas_detalhe if c in df_filtrado.columns]
                    df_detalhe_final = df_filtrado[cols_existentes]
                    
                    df_detalhe_unico = df_detalhe_final.drop_duplicates(subset=['O.S.'])

                    st.write(f"**Pacientes atendidos por: {
