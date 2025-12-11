import streamlit as st
import pandas as pd
import numpy as np
import io

# Configuração da Página
st.set_page_config(page_title="Conciliação Fiscal x Contábil", layout="wide")
st.title("📊 Análise de Notas Fiscais vs Balancete")

# --- FUNÇÕES DE LIMPEZA ---
def clean_currency_planilha(val):
    """Limpa valores da Planilha (formato geralmente float ou texto simples)"""
    if pd.isna(val) or val == '':
        return 0.0
    val_str = str(val).strip()
    # Tenta converter direto (formato 1000.00)
    try:
        return float(val_str)
    except:
        # Se falhar, tenta converter formato brasileiro (1.000,00)
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
    # Converte formato brasileiro
    val_str = val_str.replace('.', '').replace(',', '.')
    try:
        return float(val_str)
    except:
        return 0.0

# --- UPLOAD DE ARQUIVOS ---
st.sidebar.header("📂 Upload de Arquivos")
uploaded_planilhas = st.sidebar.file_uploader("Arquivos de Notas (CSV/Excel)", accept_multiple_files=True, type=['csv', 'xlsx'])
uploaded_balancete = st.sidebar.file_uploader("Arquivo do Balancete (CSV/Excel)", type=['csv', 'xlsx'])

if uploaded_planilhas and uploaded_balancete:
    # --- SELETOR DE MÊS ---
    # Cria um dicionário para mapear nomes de arquivos
    file_map = {f.name: f for f in uploaded_planilhas}
    file_names = list(file_map.keys())
    file_names.sort() # Ordena para facilitar (Jan, Fev...)
    
    selected_file_name = st.selectbox("Selecione o Mês para Análise:", file_names)
    selected_planilha_file = file_map[selected_file_name]

    st.divider()

    # --- PROCESSAMENTO ---
    with st.spinner('Processando dados...'):
        # 1. Carregar Planilha Selecionada
        # Tenta ler como CSV, se falhar tenta Excel (flexibilidade)
        try:
            df_p_raw = pd.read_csv(selected_planilha_file, header=None, dtype=str)
        except:
            selected_planilha_file.seek(0)
            df_p_raw = pd.read_excel(selected_planilha_file, header=None, dtype=str)

        # Extrair dados da Planilha (Coluna B = Índice 1)
        planilha_items = []
        for idx, row in df_p_raw.iterrows():
            # Assume Coluna A=Descrição, Coluna B=Valor
            if len(row) < 2: continue
            
            desc = row[0]
            val_raw = row[1]
            val = clean_currency_planilha(val_raw)
            
            # Filtra linhas válidas (maior que zero e não é cabeçalho)
            if val > 0 and "TOTAL" not in str(desc).upper():
                planilha_items.append({
                    "Descrição Planilha": str(desc) if pd.notna(desc) else "Sem Descrição",
                    "Valor Planilha": val,
                    "Index Original": idx
                })
        df_planilha = pd.DataFrame(planilha_items)

        # 2. Carregar Balancete
        try:
            df_b_raw = pd.read_csv(uploaded_balancete, header=None, dtype=str)
        except:
            uploaded_balancete.seek(0)
            df_b_raw = pd.read_excel(uploaded_balancete, header=None, dtype=str)

        # Extrair dados do Balancete (Coluna Q = Índice 16)
        # OBS: Adicionei colunas vizinhas (14, 17) caso o layout varie, mas prioriza a busca.
        balancete_items = []
        target_indices = [16, 14, 17] # Q é 16. Adicionei 14/17 por segurança devido ao formato do CSV.
        
        for idx, row in df_b_raw.iterrows():
            for col_idx in target_indices:
                if len(row) > col_idx:
                    val_raw = row[col_idx]
                    val = clean_currency_balancete(val_raw)
                    
                    if val > 0:
                        # Tenta pegar descrição na coluna C (idx 2) ou F (idx 5)
                        desc_cand = str(row[2]) if len(row) > 2 and pd.notna(row[2]) else ""
                        if not desc_cand and len(row) > 5:
                            desc_cand = str(row[5])
                        
                        balancete_items.append({
                            "Descrição Balancete": desc_cand if desc_cand else "Sem Descrição",
                            "Valor Balancete": val,
                            "Index Original": idx
                        })
                        break # Se achou valor em uma das colunas alvo, para de procurar nessa linha
        
        df_balancete = pd.DataFrame(balancete_items)

        # --- LÓGICA DE COMPARAÇÃO (MATCHING) ---
        matched_rows = []
        unmatched_planilha = []
        
        # Cria uma cópia do balancete para ir "riscando" os itens encontrados
        df_bal_pool = df_balancete.copy()

        if not df_planilha.empty and not df_bal_pool.empty:
            for idx, row_p in df_planilha.iterrows():
                val_p = row_p['Valor Planilha']
                desc_p = row_p['Descrição Planilha']
                
                # 1. Filtra Balancete pelo VALOR (com tolerância de 1 centavo)
                matches = df_bal_pool[np.isclose(df_bal_pool['Valor Balancete'], val_p, atol=0.01)]
                
                match_found = None
                
                if len(matches) == 1:
                    # Encontrou apenas 1 valor igual
                    match_found = matches.iloc[0]
                elif len(matches) > 1:
                    # Encontrou DUPLICIDADE de valores -> Usa o NOME para diferenciar
                    best_score = -1
                    p_words = set(desc_p.lower().split())
                    
                    for i, cand in matches.iterrows():
                        b_words = set(cand['Descrição Balancete'].lower().split())
                        # Conta palavras em comum
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
                    # Remove o item encontrado do pool para não duplicar
                    df_bal_pool = df_bal_pool.drop(match_found.name)
                else:
                    unmatched_planilha.append({
                        "Descrição (Planilha)": desc_p,
                        "Valor": val_p,
                        "Descrição (Balancete)": "---",
                        "Status": "❌ Não encontrado no Balancete"
                    })

        # Itens que sobraram no Balancete
        extra_balancete = []
        for idx, row_b in df_bal_pool.iterrows():
            extra_balancete.append({
                "Descrição (Planilha)": "---",
                "Valor": row_b['Valor Balancete'],
                "Descrição (Balancete)": row_b['Descrição Balancete'],
                "Status": "⚠️ Extra no Balancete"
            })

        # DataFrames Finais
        df_conferidos = pd.DataFrame(matched_rows)
        df_divergentes = pd.DataFrame(unmatched_planilha)
        df_extras = pd.DataFrame(extra_balancete)

        # --- EXIBIÇÃO DOS RESULTADOS ---
        
        # Métricas
        c1, c2, c3 = st.columns(3)
        c1.metric("Itens Conferidos", len(df_conferidos))
        c2.metric("Faltando no Balancete", len(df_divergentes))
        c3.metric("Sobrando no Balancete", len(df_extras))

        tab1, tab2, tab3 = st.tabs(["✅ Conferidos", "❌ Diferenças (Planilha)", "⚠️ Diferenças (Balancete)"])

        with tab1:
            st.dataframe(df_conferidos, use_container_width=True)
        
        with tab2:
            st.write("Estes valores estão na planilha mas não foram achados no balancete:")
            st.dataframe(df_divergentes, use_container_width=True)

        with tab3:
            st.write("Estes valores estão no balancete mas não na planilha (podem ser outras despesas):")
            st.dataframe(df_extras, use_container_width=True)

else:
    st.info("Por favor, faça o upload dos arquivos das planilhas mensais e do balancete na barra lateral.")
