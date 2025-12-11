import streamlit as st
import pandas as pd

# Configuração da página
st.set_page_config(page_title="Mapeamento de Riscos", layout="wide")

st.title("📊 Análise de Riscos Institucionais - Alta e Muito Alta Gravidade")
st.markdown("""
Esta ferramenta analisa o arquivo Excel de Mapeamento de Riscos e filtra eventos classificados como **Alto** ou **Muito Alto**.
Códigos considerados: `2A`, `3A`, `4A`, `5A`, `3B`, `4B`, `5B`, `5C`.
""")

# Upload do Arquivo
uploaded_file = st.file_uploader("📂 Carregue seu arquivo Excel aqui", type=["xlsx"])

if uploaded_file:
    try:
        # Carregar o arquivo Excel para ler as abas disponíveis
        xl = pd.ExcelFile(uploaded_file)
        # Filtra a aba 'Legenda' pois não será usada
        sheet_names = [s for s in xl.sheet_names if "Legenda" not in s]
        
        # Sidebar para filtros
        st.sidebar.header("Filtros de Pesquisa")
        selected_sheet = st.sidebar.selectbox("Selecione o Setor (Aba):", sheet_names)
        
        months = ['JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ']
        selected_month = st.sidebar.selectbox("Selecione o Mês:", months)
        
        # Botão para processar
        if st.sidebar.button("🔍 Buscar Riscos"):
            # Ler a aba selecionada sem cabeçalho para tratar a estrutura mesclada manualmente
            df = pd.read_excel(uploaded_file, sheet_name=selected_sheet, header=None)
            
            # Lista de riscos alvo
            target_risks = ['2A', '3A', '4A', '5A', '3B', '4B', '5B', '5C']
            
            # Calcular índices das colunas
            # JAN começa na coluna índice 8 (Coluna I no Excel).
            # Padrão: Mês X -> Coluna de Conteúdo, Coluna de Risco
            month_idx = months.index(selected_month)
            content_col_index = 8 + (month_idx * 2)
            risk_col_index = content_col_index + 1
            
            results = []
            
            # Iterar pelas linhas ignorando cabeçalhos e linhas vazias
            for index, row in df.iterrows():
                # Validação básica para pular linhas de cabeçalho ou vazias
                first_col = str(row[0])
                if pd.isna(row[0]) or first_col.strip() in [
                    'FONTE', 'IDENTIFICAÇÃO DO RISCO', 'Identificação do Risco', 
                    'Riscos Institucionais Gerenciados', 
                    'Riscos Institucionais  não Gerenciados/Inventariados', 
                    'C.H.O.R.C.'
                ]:
                    continue
                
                # Verifica se a coluna de risco existe nessa linha
                if len(row) > risk_col_index:
                    risk_value = str(row[risk_col_index]).strip().upper()
                    
                    if risk_value in target_risks:
                        results.append({
                            "Identificação do Risco": row[0],
                            "Causa": row[1],
                            f"Conteúdo ({selected_month})": row[content_col_index],
                            "Classificação": risk_value
                        })
            
            # Exibir Resultados
            if results:
                st.success(f"Foram encontrados {len(results)} riscos com gravidade Alta/Muito Alta em {selected_sheet} no mês de {selected_month}.")
                df_results = pd.DataFrame(results)
                st.table(df_results)
            else:
                st.info(f"Nenhum risco alto ou muito alto encontrado em {selected_sheet} para {selected_month}.")
                
    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")
else:
    st.warning("Por favor, carregue o arquivo Excel para começar.")
