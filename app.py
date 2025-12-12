import streamlit as st
import pandas as pd
import plotly.express as px  # Nova biblioteca para gráficos bonitos

# ---------------------------------------------------------
# CONFIGURAÇÃO GERAL DA PÁGINA
# ---------------------------------------------------------
st.set_page_config(page_title="Dashboard Integrado", layout="wide")

# Título Principal (aparece em todas as páginas)
st.title("📊 Dashboard Integrado de Gestão")

# ---------------------------------------------------------
# MENU DE NAVEGAÇÃO LATERAL
# ---------------------------------------------------------
st.sidebar.title("Navegação")
pagina_selecionada = st.sidebar.radio(
    "Ir para:",
    ["📋 Análise de Coletas", "⚠️ Mapeamento de Riscos"]
)
st.sidebar.markdown("---")

# =========================================================
# PÁGINA 1: ANÁLISE DE COLETAS POR COLABORADOR
# =========================================================
if pagina_selecionada == "📋 Análise de Coletas":
    st.header("Análise de Produtividade por Colaborador")
    st.markdown("Esta ferramenta analisa o arquivo de coletas (CSV) para contabilizar atendimentos.")

    # Upload do Arquivo de Coletas
    uploaded_file_coletas = st.file_uploader("📂 Carregue o arquivo de Coletas (CSV) aqui", type=["csv"], key="upload_coletas")

    if uploaded_file_coletas:
        try:
            # Tenta ler o arquivo com diferentes encodings
            try:
                df_coletas = pd.read_csv(uploaded_file_coletas, sep=";", encoding='utf-8')
            except UnicodeDecodeError:
                uploaded_file_coletas.seek(0)
                df_coletas = pd.read_csv(uploaded_file_coletas, sep=";", encoding='latin1')
            
            # Lógica de Contagem
            if 'Usuário Nome' in df_coletas.columns and 'O.S.' in df_coletas.columns:
                # Agrupa por Colaborador e conta O.S. únicas
                resumo = df_coletas.groupby('Usuário Nome')['O.S.'].nunique().reset_index()
                resumo.columns = ['Colaborador', 'Qtd. Pacientes Atendidos']
                resumo = resumo.sort_values(by='Qtd. Pacientes Atendidos', ascending=True) # Ascending true para o gráfico horizontal ficar na ordem certa

                # Exibição do Resumo
                st.subheader("Resumo de Atendimentos")
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    # Ordena do maior para o menor para a tabela
                    resumo_tabela = resumo.sort_values(by='Qtd. Pacientes Atendidos', ascending=False).reset_index(drop=True)
                    st.dataframe(resumo_tabela, use_container_width=True)
                    
                with col2:
                    # --- MUDANÇA AQUI: GRÁFICO PLOTLY ---
                    fig = px.bar(
                        resumo, 
                        x='Qtd. Pacientes Atendidos', 
                        y='Colaborador', 
                        orientation='h', # Barras horizontais
                        text_auto=True,  # Mostra o número na barra
                        title="Pacientes Atendidos por Colaborador"
                    )
                    # Ajustes visuais para limpar o gráfico
                    fig.update_layout(
                        xaxis_title="Quantidade de Pacientes",
                        yaxis_title="Colaborador",
                        showlegend=False,
                        height=400
                    )
                    st.plotly_chart(fig, use_container_width=True)

                st.markdown("---")

                # Detalhes Interativos
                st.subheader("🔎 Detalhes por Colaborador")
                st.info("Selecione um colaborador abaixo para ver a lista detalhada.")

                # Pega a lista ordenada da tabela para o selectbox ficar na ordem correta
                lista_colaboradores = resumo_tabela['Colaborador'].unique()
                colaborador_selecionado = st.selectbox("Escolha o Colaborador:", lista_colaboradores)

                if colaborador_selecionado:
                    df_filtrado = df_coletas[df_coletas['Usuário Nome'] == colaborador_selecionado].copy()
                    
                    # Colunas de interesse
                    colunas_detalhe = ['Data da Operação', 'O.S.', 'Paciente', 'Paciente Nome', 'Detalhe Descrição']
                    cols_existentes = [c for c in colunas_detalhe if c in df_filtrado.columns]
                    df_detalhe_final = df_filtrado[cols_existentes]
                    
                    # Remove duplicatas de O.S.
                    df_detalhe_unico = df_detalhe_final.drop_duplicates(subset=['O.S.'])

                    st.write(f"**Pacientes atendidos por: {colaborador_selecionado}**")
                    st.dataframe(df_detalhe_unico, use_container_width=True)
                    
                    # Botão de Download
                    csv = df_detalhe_unico.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Baixar detalhes (CSV)",
                        data=csv,
                        file_name=f'detalhes_{colaborador_selecionado}.csv',
                        mime='text/csv',
                    )
            else:
                st.error("O arquivo carregado não possui as colunas 'Usuário Nome' ou 'O.S.'. Verifique se o arquivo está correto.")

        except Exception as e:
            st.error(f"Ocorreu um erro ao processar o arquivo de coletas: {e}")
    else:
        st.info("Por favor, carregue o arquivo CSV de coletas para visualizar os dados.")

# =========================================================
# PÁGINA 2: MAPEAMENTO DE RISCOS
# =========================================================
elif pagina_selecionada == "⚠️ Mapeamento de Riscos":
    st.header("Análise de Riscos Institucionais - Alta e Muito Alta Gravidade")
    st.markdown("""
    Esta ferramenta analisa o arquivo de Mapeamento de Riscos (Excel ou CSV) e filtra eventos classificados como **Alto** ou **Muito Alto**.
    Códigos considerados: `2A`, `3A`, `4A`, `5A`, `3B`, `4B`, `5B`, `5C`.
    """)

    # Upload do Arquivo Excel/CSV
    uploaded_file_riscos = st.file_uploader("📂 Carregue seu arquivo Excel ou CSV de Riscos aqui", type=["xlsx", "csv"], key="upload_riscos")

    if uploaded_file_riscos:
        try:
            # Verifica a extensão do arquivo
            is_csv = uploaded_file_riscos.name.lower().endswith('.csv')
            
            if is_csv:
                sheet_names = ["Arquivo CSV"]
            else:
                xl = pd.ExcelFile(uploaded_file_riscos)
                sheet_names = [s for s in xl.sheet_names if "Legenda" not in s]
            
            # Filtros na Sidebar
            st.sidebar.header("Filtros (Riscos)")
            selected_sheet = st.sidebar.selectbox("Selecione o Setor (Aba):", sheet_names)
            
            months = ['JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ']
            selected_month = st.sidebar.selectbox("Selecione o Mês:", months)
            
            # Botão para processar
            if st.sidebar.button("🔍 Buscar Riscos", key="btn_buscar_riscos"):
                
                # Leitura do arquivo
                if is_csv:
                    uploaded_file_riscos.seek(0) 
                    df_riscos = pd.read_csv(uploaded_file_riscos, header=None, sep=';', encoding='latin1')
                else:
                    df_riscos = pd.read_excel(uploaded_file_riscos, sheet_name=selected_sheet, header=None)
                
                # Lógica de Riscos
                target_risks = ['2A', '3A', '4A', '5A', '3B', '4B', '5B', '5C']
                
                month_idx = months.index(selected_month)
                content_col_index = 8 + (month_idx * 2)
                risk_col_index = content_col_index + 1
                
                results = []
                
                for index, row in df_riscos.iterrows():
                    first_col = str(row[0])
                    if pd.isna(row[0]) or first_col.strip() in [
                        'FONTE', 'IDENTIFICAÇÃO DO RISCO', 'Identificação do Risco', 
                        'Riscos Institucionais Gerenciados', 
                        'Riscos Institucionais  não Gerenciados/Inventariados', 
                        'C.H.O.R.C.'
                    ]:
                        continue
                    
                    if len(row) > risk_col_index:
                        risk_value = str(row[risk_col_index]).strip().upper()
                        
                        if risk_value in target_risks:
                            results.append({
                                "Identificação do Risco": row[0],
                                "Causa": row[1],
                                f"Conteúdo ({selected_month})": row[content_col_index],
                                "Classificação": risk_value
                            })
                
                if results:
                    st.success(f"Foram encontrados {len(results)} riscos com gravidade Alta/Muito Alta em {selected_sheet} no mês de {selected_month}.")
                    df_results = pd.DataFrame(results)
                    st.table(df_results)
                else:
                    st.info(f"Nenhum risco alto ou muito alto encontrado em {selected_sheet} para {selected_month}.")
                    
        except Exception as e:
            st.error(f"Erro ao processar o arquivo: {e}")
    else:
        st.info("Por favor, carregue o arquivo Excel ou CSV na área acima para começar a análise de riscos.")
