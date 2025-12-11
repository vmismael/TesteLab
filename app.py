import streamlit as st
import pandas as pd
import numpy as np

# Configuração da Página
st.set_page_config(page_title="Conciliação Fiscal x Contábil", layout="wide")
st.title("📊 Análise de Notas Fiscais vs Balancete")
st.markdown("---")

# --- FUNÇÕES DE LIMPEZA ---
def clean_currency_planilha(val):
    """Limpa valores da Planilha (formato geralmente float ou texto simples)"""
    if pd.isna(val) or val == '':
        return 0.0
    val_str = str(val).strip()
    try:
        return float(val_str)
    except:
        try:
            return float(val_str.replace('.', '').replace(',', '.'))
        except:
            return 0.0

def clean_currency_balancete(val):
    """Limpa valores do Balancete (formato 1.000,00D ou C)"""
    if pd.isna(val) or val == '':
        return 0.0
    # Remove letras de Débito/Crédito e espaços
    val_str = str(val).upper().replace('D', '').replace('C', '').strip()
    # Converte formato brasileiro (remove ponto de milhar, troca vírgula por ponto)
    val_str = val_str.replace('.', '').replace(',', '.')
    try:
        return float(val_str)
    except:
        return 0.0

# --- BARRA LATERAL (UPLOADS) ---
st.sidebar.header("📂 Upload de Arquivos")

# 1. Upload do Arquivo Mestre de Notas (Excel com várias abas)
uploaded_planilha_master = st.sidebar.file_uploader(
    "1. Arquivo de Notas (Excel .xlsx com abas mensais)", 
    type=['xlsx']
)

# 2. Upload do Balancete (Arquivo do mês específico)
uploaded_balancete = st.sidebar.file_uploader(
    "2. Arquivo do Balancete (CSV ou Excel)", 
    type=['csv', 'xlsx']
)

# --- LÓGICA PRINCIPAL ---
if uploaded_planilha_master and uploaded_balancete:
    try:
        # Carrega o arquivo Excel para ler os nomes das abas (meses)
        xls_file = pd.ExcelFile(uploaded_planilha_master)
        sheet_names = xls_file.sheet_names
        
        # Seletor de Mês (baseado nas abas do Excel)
        st.subheader("🗓️ Seleção do Mês")
        selected_sheet = st.selectbox("Escolha a aba (mês) que deseja analisar:", sheet_names)
        
        if st.button("Iniciar Análise"):
            with st.spinner(f'Lendo aba "{selected_sheet}" e processando dados...'):
                
                # --- 1. PROCESSAR PLANILHA DE NOTAS (ABA SELECIONADA) ---
                # Lê a aba específica sem cabeçalho (header=None)
                df_p_raw = pd.read_excel(uploaded_planilha_master, sheet_name=selected_sheet, header=None, dtype=str)
                
                planilha_items = []
                # Itera sobre as linhas procurando valores na Coluna B (índice 1)
                for idx, row in df_p_raw.iterrows():
                    # Garante que a linha tem pelo menos 2 colunas
                    if len(row) < 2: continue
                    
                    desc = row[0] # Coluna A: Descrição/Nome
                    val_raw = row[1] # Coluna B: Valor
                    
                    val = clean_currency_planilha(val_raw)
                    
                    # Filtros: Valor > 0 e ignorar linhas de "TOTAL"
                    if val > 0 and "TOTAL" not in str(desc).upper():
                        planilha_items.append({
                            "Descrição Planilha": str(desc) if pd.notna(desc) else "Sem Descrição",
                            "Valor Planilha": val,
                            "Index Original": idx
                        })
                
                df_planilha = pd.DataFrame(planilha_items)

                # --- 2. PROCESSAR BALANCETE ---
                try:
                    df_b_raw = pd.read_csv(uploaded_balancete, header=None, dtype=str)
                except:
                    uploaded_balancete.seek(0)
                    df_b_raw = pd.read_excel(uploaded_balancete, header=None, dtype=str)

                balancete_items = []
                
                # --- CORREÇÃO: COLUNA O (Índice 14) ---
                # Definindo índice 14 como alvo principal
                target_col_idx = 14 
                
                for idx, row in df_b_raw.iterrows():
                    if len(row) > target_col_idx:
                        val_raw = row[target_col_idx]
                        val = clean_currency_balancete(val_raw)
                        
                        if val > 0:
                            # Tenta achar a descrição (geralmente col C=2 ou F=5 no balancete)
                            desc_cand = str(row[2]) if len(row) > 2 and pd.notna(row[2]) else ""
                            if not desc_cand and len(row) > 5:
                                desc_cand = str(row[5])
                            
                            balancete_items.append({
                                "Descrição Balancete": desc_cand if desc_cand else "Sem Descrição",
                                "Valor Balancete": val,
                                "Index Original": idx
                            })
                
                df_balancete = pd.DataFrame(balancete_items)

                # --- 3. LÓGICA DE COMPARAÇÃO (MATCHING) ---
                matched_rows = []
                unmatched_planilha = []
                
                df_bal_pool = df_balancete.copy()

                if not df_planilha.empty and not df_bal_pool.empty:
                    for idx, row_p in df_planilha.iterrows():
                        val_p = row_p['Valor Planilha']
                        desc_p = row_p['Descrição Planilha']
                        
                        # Busca por valor exato (com pequena tolerância de centavos)
                        matches = df_bal_pool[np.isclose(df_bal_pool['Valor Balancete'], val_p, atol=0.01)]
                        
                        match_found = None
                        
                        if len(matches) == 1:
                            match_found = matches.iloc[0]
                        elif len(matches) > 1:
                            # Critério de desempate: Similaridade de nome
                            best_score = -1
                            p_words = set(desc_p.lower().split())
                            
                            for i, cand in matches.iterrows():
                                b_words = set(cand['Descrição Balancete'].lower().split())
                                score = len(p_words.intersection(b_words))
                                if score > best_score:
                                    best_score = score
                                    match_found = cand
                        
                        if match_found is not None:
                            matched_rows.append({
                                "Descrição (Planilha)": desc_p,
                                "Valor": val_p,
                                "Descrição (Balancete)": match_found['Descrição Balancete'],
                                "Status": "✅ Conferido"
                            })
                            # Remove do pool
                            df_bal_pool = df_bal_pool.drop(match_found.name)
                        else:
                            unmatched_planilha.append({
                                "Descrição (Planilha)": desc_p,
                                "Valor": val_p,
                                "Descrição (Balancete)": "---",
                                "Status": "❌ Não encontrado"
                            })

                # Sobras do Balancete
                extra_balancete = []
                for idx, row_b in df_bal_pool.iterrows():
                    extra_balancete.append({
                        "Descrição (Planilha)": "---",
                        "Valor": row_b['Valor Balancete'],
                        "Descrição (Balancete)": row_b['Descrição Balancete'],
                        "Status": "⚠️ Extra Balancete"
                    })

                # --- 4. EXIBIÇÃO ---
                df_conferidos = pd.DataFrame(matched_rows)
                df_divergentes = pd.DataFrame(unmatched_planilha)
                df_extras = pd.DataFrame(extra_balancete)

                st.success("Processamento Concluído!")

                c1, c2, c3 = st.columns(3)
                c1.metric("Conferidos", len(df_conferidos))
                c2.metric("Não achados no Balancete", len(df_divergentes))
                c3.metric("Sobras no Balancete", len(df_extras))

                tab1, tab2, tab3 = st.tabs(["✅ Conferidos", "❌ Diferenças (Planilha)", "⚠️ Diferenças (Balancete)"])

                with tab1:
                    st.dataframe(df_conferidos, use_container_width=True)
                with tab2:
                    st.write("Valores da planilha que **não** bateram com a Coluna O do Balancete:")
                    st.dataframe(df_divergentes, use_container_width=True)
                with tab3:
                    st.write("Valores na Coluna O do Balancete que **sobraram**:")
                    st.dataframe(df_extras, use_container_width=True)

    except Exception as e:
        st.error(f"Erro ao processar arquivo: {e}")
else:
    st.info("👆 Faça o upload dos arquivos na barra lateral para começar.")
