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
# ABA 1: ANÁLISE DE COLETAS POR COLABORADOR
# =========================================================
with aba1:
    st.header("Análise de Produtividade por Colaborador")
    st.markdown("Esta aba analisa o arquivo CSV `COLETAS POR COLABORADOR..csv`.")

    # Função para carregar os dados da Aba 1
    @st.cache_data
    def carregar_dados_coletas():
        arquivo = "COLETAS POR COLABORADOR..csv"
        try:
            df = pd.read_csv(arquivo, sep=";", encoding='utf-8')
        except UnicodeDecodeError:
            df = pd.read_csv(arquivo, sep=";", encoding='latin1')
        return df

    # Lógica de processamento da Aba 1
    try:
        # Tenta carregar automaticamente o arquivo local
        df_coletas = carregar_dados_coletas()
        
        # Lógica de Contagem
        # Agrupa por Colaborador e conta O.S. únicas
        resumo = df_coletas.groupby('Usuário Nome')['O.S.'].nunique().reset_index()
        resumo.columns = ['Colaborador', 'Qtd. Pacientes Atendidos']
        resumo = resumo.sort_values(by='Qtd. Pacientes Atendidos', ascending=False).reset_index(drop=True)

        # Exibição do Resumo
        st.subheader("Resumo de Atendimentos")
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.dataframe(resumo, use_container_width=True)
            
        with col2:
            st.bar_chart(resumo.set_index('Colaborador'))

        st.markdown("---")

        # Detalhes Interativos
        st.subheader("🔎 Detalhes por Colaborador")
        st.info("Selecione um colaborador abaixo para ver a lista detalhada.")

        lista_colaboradores = resumo['Colaborador'].unique()
        colaborador_selecionado = st.selectbox("Escolha o Colaborador:", lista_colaboradores)

        if colaborador_selecionado:
            df_filtrado = df_coletas[df_coletas['Usuário Nome'] == colaborador_selecionado].copy()
            
            # Colunas de interesse
            colunas_detalhe = ['Data da Operação', 'O.S.', 'Paciente', 'Paciente Nome', 'Detalhe Descrição']
            cols_existentes = [c for c in colunas_detalhe if c in df_filtrado.columns]
            df_detalhe_final = df_filtrado[cols_existentes]
            
            # Remove duplicatas de O.S. para visualização limpa
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

    except FileNotFoundError:
        st.error("Erro: O arquivo 'COLETAS POR COLABORADOR..csv' não foi encontrado na pasta.")
    except Exception as e:
        st.error(f"Ocorreu um erro na aba de Coletas: {e}")

# =========================================================
# ABA 2: MAPEAMENTO DE RISCOS
# =========================================================
with aba2:
    st.header("Análise de Riscos Institucionais - Alta e Muito Alta Gravidade")
    st.markdown("""
    Esta ferramenta analisa o arquivo Excel de Mapeamento de Riscos e filtra eventos classificados como **Alto** ou **Muito Alto**.
    Códigos considerados: `2A`, `3A`, `4A`, `5A`, `3B`, `4B`, `5B`, `5C`.
    """)

    # Upload do Arquivo Excel (Específico desta aba)
    uploaded_file_riscos = st.file_uploader("📂 Carregue seu arquivo Excel de Riscos aqui", type=["xlsx"], key="upload_riscos")

    if uploaded_file_riscos:
        try:
            # Carregar o arquivo Excel para ler as abas disponíveis
            xl = pd.ExcelFile(uploaded_file_riscos)
            # Filtra a aba 'Legenda' pois não será usada
            sheet_names = [s for s in xl.sheet_names if "Legenda" not in s]
            
            # Layout de colunas para filtros dentro da aba
            col_filtros1, col_filtros2 = st.columns(2)
            
            with col_filtros1:
                selected_sheet = st.selectbox("Selecione o Setor (Aba):", sheet_names)
            
            with col_filtros2:
                months = ['JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ']
                selected_month = st.selectbox("Selecione o Mês:", months)
            
            # Botão para processar
            if st.button("🔍 Buscar Riscos", key="btn_buscar_riscos"):
                # Ler a aba selecionada sem cabeçalho para tratar a estrutura mesclada manualmente
                df_riscos = pd.read_excel(uploaded_file_riscos, sheet_name=selected_sheet, header=None)
                
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
                for index, row in df_riscos.iterrows():
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
            st.error(f"Erro ao processar o arquivo Excel: {e}")
    else:
        st.warning("Por favor, carregue o arquivo Excel na área acima para começar a análise de riscos.")
