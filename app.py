import streamlit as st
import pandas as pd

# ---------------------------------------------------------
# CONFIGURAÇÃO GERAL DA PÁGINA
# ---------------------------------------------------------
st.set_page_config(page_title="Dashboard Integrado", layout="wide")
st.title("📊 Dashboard Integrado de Gestão")

# Criação das Abas
aba1, aba2 = st.tabs(["📋 Análise de Coletas", "⚠️ Mapeamento de Riscos"])

# =========================================================
# ABA 1: ANÁLISE DE COLETAS (Código Gerado Anteriormente)
# =========================================================
with aba1:
    st.header("Análise de Produtividade por Colaborador")
    st.markdown("Esta aba analisa o arquivo CSV `COLETAS POR COLABORADOR..csv` salvo no diretório.")

    # Função para carregar os dados
    @st.cache_data
    def carregar_dados_coletas():
        arquivo = "COLETAS POR COLABORADOR..csv"
        try:
            df = pd.read_csv(arquivo, sep=";", encoding='utf-8')
        except UnicodeDecodeError:
            df = pd.read_csv(arquivo, sep=";", encoding='latin1')
        return df

    try:
        df_coletas = carregar_dados_coletas()
        
        # Lógica de Contagem
        resumo = df_coletas.groupby('Usuário Nome')['O.S.'].nunique().reset_index()
        resumo.columns = ['Colaborador', 'Qtd. Pacientes Atendidos']
        resumo = resumo.sort_values(by='Qtd. Pacientes Atendidos', ascending=False).reset_index(drop=True)

        st.subheader("Resumo de Atendimentos")
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st
