import streamlit as st
import pandas as pd
import re

# Configuração da página
st.set_page_config(page_title="Análise de Desempenho", layout="wide")

st.title("📊 Painel de Análise de Desempenho")
st.markdown("Faça o upload do arquivo CSV para visualizar as médias e observações por colaborador.")

# Upload do arquivo
uploaded_file = st.file_uploader("Carregue o arquivo CSV aqui", type=["csv"])

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        
        # Dicionário para armazenar a estrutura dos dados:
        # { 'Nome do Colaborador': {'coluna_contato': str, 'colunas_notas': list, 'coluna_obs': str} }
        collaborators_data = {}
        
        current_collaborator = None
        
        # Iterar sobre todas as colunas para mapear a estrutura dinamicamente
        for col in df.columns:
            # 1. Identificar o início de um novo colaborador (Coluna de "Sim/Não")
            if "Você tem contato suficiente com o(a) colaborador(a)" in col:
                # Extrair o nome usando Regex
                match = re.search(r"colaborador\(a\) (.+?) para", col)
                if match:
                    current_collaborator = match.group(1)
                    collaborators_data[current_collaborator] = {
                        'coluna_contato': col,
                        'colunas_notas': [],
                        'coluna_obs': None
                    }
            
            # 2. Identificar a coluna de Observações (Fim da seção do colaborador atual)
            elif current_collaborator and col.strip().startswith("Observações:"):
                collaborators_data[current_collaborator]['coluna_obs'] = col
                current_collaborator = None # Fecha o ciclo deste colaborador
            
            # 3. Se estivermos dentro de uma seção de colaborador, é uma coluna de nota
            elif current_collaborator:
                collaborators_data[current_collaborator]['colunas_notas'].append(col)

        # Seletor de Colaborador na barra lateral ou principal
        collab_list = list(collaborators_data.keys())
        
        if collab_list:
            selected_collab = st.selectbox("👤 Selecione o Colaborador:", collab_list)
            
            # Dados do colaborador selecionado
            data_info = collaborators_data[selected_collab]
            col_contato = data_info['coluna_contato']
            cols_notas = data_info['colunas_notas']
            col_obs = data_info['coluna_obs']
            
            # FILTRAGEM: Pegar apenas quem respondeu "Sim"
            # O filtro procura por qualquer resposta que comece com "Sim" (ignorando maiúsculas/minúsculas)
            df_filtered = df[df[col_contato].astype(str).str.contains(r"^Sim", case=False, na=False)]
            
            qtd_avaliadores = len(df_filtered)
            
            if qtd_avaliadores > 0:
                st.write(f"**Total de avaliações consideradas:** {qtd_avaliadores}")
                st.divider()

                # --- CÁLCULO DAS MÉDIAS ---
                st.subheader("📈 Médias de Desempenho (0 a 100)")
                
                # Converter colunas de notas para numérico (para garantir) e calcular média
                medias = {}
                for col in cols_notas:
                    # Limpar o nome da coluna (remover sufixos numéricos que o Excel/CSV cria, ex: "Carisma 2" -> "Carisma")
                    clean_name = re.sub(r'\s+\d+$', '', col).strip() 
                    # Extrair apenas o texto descritivo (remove "1. ", "2. ", etc se desejar, mas mantive para referência)
                    
                    # Forçar conversão para números, erros viram NaN (não contam na média)
                    numeric_series = pd.to_numeric(df_filtered[col], errors='coerce')
                    media_val = numeric_series.mean()
                    medias[clean_name] = media_val

                # Criar DataFrame para exibição
                df_medias = pd.DataFrame(list(medias.items()), columns=['Critério', 'Média'])
                df_medias = df_medias.set_index('Critério')
                
                # Exibir Tabela colorida e Gráfico
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    # Formatar para mostrar 2 casas decimais
                    st.dataframe(df_medias.style.format("{:.2f}"))
                
                with col2:
                    st.bar_chart(df_medias)

                st.divider()

                # --- OBSERVAÇÕES ---
                st.subheader("📝 Observações")
                
                if col_obs:
                    # Pegar observações não nulas do dataset filtrado
                    observacoes = df_filtered[col_obs].dropna()
                    
                    if not observacoes.empty:
                        for i, obs in enumerate(observacoes):
                            st.info(f"**Observação {i+1}:** {obs}")
                    else:
                        st.write("Nenhuma observação registrada para este colaborador.")
                else:
                    st.warning("Coluna de observações não encontrada para este colaborador.")

            else:
                st.warning("Nenhum avaliador respondeu que tem contato suficiente com este colaborador (ou não há dados marcados com 'Sim').")
        
        else:
            st.error("Não foi possível identificar colaboradores no arquivo. Verifique se as colunas contêm 'Você tem contato suficiente com o(a) colaborador(a)'.")

    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")
