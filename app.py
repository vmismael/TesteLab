import streamlit as st
import pandas as pd
import numpy as np

# Configuração da Página
st.set_page_config(page_title="Conciliação Fiscal x Contábil", layout="wide")
st.title("📊 Análise de Notas Fiscais vs Balancete")
st.markdown("---")

# --- FUNÇÕES DE LIMPEZA ---
def clean_currency_planilha(val):
    """Limpa valores da Planilha (formato float ou texto simples)"""
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
    """Limpa valores do Balancete (formato brasileiro 1.000,00)"""
    if pd.isna(val) or val == '':
        return 0.0
    # Remove 'D', 'C' e espaços
    val_str = str(val).upper().replace('D', '').replace('C', '').strip()
    # Remove ponto de milhar e troca vírgula decimal por ponto
    val_str = val_str.replace('.', '').replace(',', '.')
    try:
        return float(val_str)
    except:
        return 0.0

# --- BARRA LATERAL (UPLOADS) ---
st.sidebar.header("📂 Upload de Arquivos")

uploaded_planilha_master = st.sidebar.file_uploader(
    "1. Arquivo de Notas (Excel .xlsx com abas mensais)", 
    type=['xlsx']
)

uploaded_balancete = st.sidebar.file_uploader(
    "2. Arquivo do Balancete (CSV ou Excel)", 
    type=['csv', 'xlsx']
)

# --- LÓGICA PRINCIPAL ---
if uploaded_planilha_master and uploaded_balancete:
    try:
        # Carrega nomes das abas
        xls_file = pd.ExcelFile(uploaded_planilha_master)
        sheet_names = xls_file.sheet_names
        
        st.subheader("🗓️ Seleção do Mês")
        selected_sheet = st.selectbox("Escolha a aba (mês) que deseja analisar:", sheet_names)
        
        if st.button("Iniciar Análise"):
            with st.spinner(f'Processando aba "{selected_sheet}"...'):
                
                # ==========================================
                # 1. PROCESSAR PLANILHA DE NOTAS (ABA SELECIONADA)
                # ==========================================
                df_p_raw = pd.read_excel(uploaded_planilha_master, sheet_name=selected_sheet, header=None, dtype=str)
                
                planilha_items = []
                for idx, row in df_p_raw.iterrows():
                    if len(row) < 2: continue
                    
                    # Coluna A (0) = Nome, Coluna B (1) = Valor
                    desc = row[0]
                    val_raw = row[1]
                    val = clean_currency_planilha(val_raw)
                    
                    if val > 0 and "TOTAL" not in str(desc).upper():
                        planilha_items.append({
                            "Descrição Planilha": str(desc).strip() if pd.notna(desc) else "Sem Descrição",
                            "Valor Planilha": val
                        })
                
                df_planilha = pd.DataFrame(planilha_items)

                # ==========================================
                # 2. PROCESSAR BALANCETE (BUSCA DINÂMICA)
                # ==========================================
                try:
                    df_b_raw = pd.read_csv(uploaded_balancete, header=None, dtype=str)
                except:
                    uploaded_balancete.seek(0)
                    df_b_raw = pd.read_excel(uploaded_balancete, header=None, dtype=str)

                balancete_items = []
                debito_col_idx = None
                nome_col_idx = None # Vamos tentar achar onde fica o nome da conta também

                # 2.1 Identificar onde está a coluna "DÉBITO"
                # O usuário disse que está na LINHA 3 (índice 2)
                if len(df_b_raw) > 2:
                    header_row = df_b_raw.iloc[2] # Linha 3
                    
                    for i, col_val in enumerate(header_row):
                        col_text = str(col_val).upper().strip()
                        if "DÉBITO" in col_text or "DEBITO" in col_text:
                            debito_col_idx = i
                        # Geralmente a coluna "NOME" ou "DESCRIÇÃO" vem antes
                        if "NOME" in col_text or "CONTA" in col_text or "DESCRIÇÃO" in col_text:
                            if nome_col_idx is None: # Pega a primeira que achar
                                nome_col_idx = i
                
                # Fallback se não achar o cabeçalho (mas deve achar com sua instrução)
                if debito_col_idx is None:
                    st.warning("⚠️ Não achei a coluna escrito 'DÉBITO' na linha 3. Tentando a coluna O (14) por padrão.")
                    debito_col_idx = 14
                
                # Se não achou coluna de nome, chuta coluna C (2) ou F (5)
                possible_name_cols = [2, 5]
                if nome_col_idx: possible_name_cols.insert(0, nome_col_idx)

                # 2.2 Extrair valores (começam na Linha 4 -> índice 3)
                start_row = 3 # Linha 4
                
                for idx, row in df_b_raw.iterrows():
                    if idx < start_row: continue # Pula cabeçalho
                    
                    if len(row) > debito_col_idx:
                        val_raw = row[debito_col_idx]
                        val = clean_currency_balancete(val_raw)
                        
                        if val > 0:
                            # Tenta pegar descrição
                            desc = "Sem Descrição"
                            for name_idx in possible_name_cols:
                                if len(row) > name_idx and pd.notna(row[name_idx]):
                                    desc = str(row[name_idx]).strip()
                                    if desc: break
                            
                            balancete_items.append({
                                "Descrição Balancete": desc,
                                "Valor Balancete": val
                            })

                df_balancete = pd.DataFrame(balancete_items)

                # ==========================================
                # 3. COMPARAÇÃO (MATCHING)
                # ==========================================
                matched_rows = []
                unmatched_planilha = []
                
                df_bal_pool = df_balancete.copy()

                if not df_planilha.empty and not df_bal_pool.empty:
                    for idx, row_p in df_planilha.iterrows():
                        val_p = row_p['Valor Planilha']
                        desc_p = row_p['Descrição Planilha']
                        
                        # 1. Busca por valor exato (com tolerância de 0.02 centavos para arredondamentos)
                        matches = df_bal_pool[np.isclose(df_bal_pool['Valor Balancete'], val_p, atol=0.02)]
                        
                        match_found = None
                        
                        if len(matches) == 1:
                            match_found = matches.iloc[0]
                        elif len(matches) > 1:
                            # 2. Desempate por Nome
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
                            df_bal_pool = df_bal_pool.drop(match_found.name)
                        else:
                            unmatched_planilha.append({
                                "Descrição (Planilha)": desc_p,
                                "Valor": val_p,
                                "Status": "❌ Não encontrado"
                            })

                # Sobras
                extra_balancete = df_bal_pool.rename(columns={
                    "Descrição Balancete": "Descrição", 
                    "Valor Balancete": "Valor"
                })

                # ==========================================
                # 4. EXIBIÇÃO
                # ==========================================
                st.success(f"Análise Finalizada! (Coluna DÉBITO detectada no índice {debito_col_idx})")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Conferidos", len(matched_rows))
                c2.metric("Não encontrados (Planilha)", len(unmatched_planilha))
                c3.metric("Não encontrados (Balancete)", len(extra_balancete))

                tab1, tab2, tab3 = st.tabs(["✅ Conferidos", "❌ Diferenças (Planilha)", "⚠️ Diferenças (Balancete)"])

                with tab1:
                    st.dataframe(pd.DataFrame(matched_rows), use_container_width=True)
                with tab2:
                    st.dataframe(pd.DataFrame(unmatched_planilha), use_container_width=True)
                with tab3:
                    st.dataframe(extra_balancete, use_container_width=True)

    except Exception as e:
        st.error(f"Erro durante o processamento: {e}")
else:
    st.info("👆 Faça o upload dos arquivos para começar.")
