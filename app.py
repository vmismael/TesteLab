import streamlit as st
import pandas as pd
from collections import Counter

st.set_page_config(page_title="Conferência Pix vs Banco", layout="wide")

st.title("Conferência de Pix: Excel vs Extrato BB")
st.markdown("""
**Instruções:**
1. Faça upload da Planilha de Pix (.csv ou .xlsx convertido)
2. Faça upload do Extrato do Banco (.csv)
3. O sistema irá comparar os valores ignorando as datas.
""")

# Upload dos arquivos
uploaded_pix = st.file_uploader("Carregar Planilha Pix (CSV do Excel)", type=["csv", "xlsx"])
uploaded_bb = st.file_uploader("Carregar Extrato BB (CSV)", type=["csv"])

if uploaded_pix and uploaded_bb:
    st.divider()
    
    # --- Processamento do Arquivo Pix ---
    try:
        # Tenta ler como UTF-8 (padrão)
        try:
            df_pix = pd.read_csv(uploaded_pix, header=None)
        except UnicodeDecodeError:
            # Se der erro de encoding, volta o arquivo pro início e tenta ler como Latin-1 (Excel Padrão)
            uploaded_pix.seek(0)
            df_pix = pd.read_csv(uploaded_pix, header=None, encoding='latin1')
        
        # A planilha parece ter duas listas lado a lado (Colunas D e I, índices 3 e 8)
        # Vamos pegar valores da coluna D (index 3)
        # Regra: Ignorar linhas onde a coluna de hora (index 2) contém "Total" ou é vazia
        vals_1 = []
        if len(df_pix.columns) > 3:
            col_d = df_pix[[2, 3]].dropna()
            for i, row in col_d.iterrows():
                if "Total" not in str(row[2]):
                    vals_1.append(float(row[3]))
        
        # Vamos pegar valores da coluna I (index 8) se existir
        vals_2 = []
        if len(df_pix.columns) > 8:
            col_i = df_pix[[7, 8]].dropna()
            for i, row in col_i.iterrows():
                if "Total" not in str(row[7]):
                    vals_2.append(float(row[8]))
        
        # Lista final de valores esperados (Planilha)
        pix_values = vals_1 + vals_2
        st.success(f"Planilha Pix processada: {len(pix_values)} lançamentos encontrados.")
        
    except Exception as e:
        st.error(f"Erro ao ler planilha Pix: {e}")
        st.stop()

    # --- Processamento do Arquivo BB ---
    try:
        # Lê o CSV do banco (separador ponto e vírgula, encoding latin1)
        df_bb = pd.read_csv(uploaded_bb, sep=';', header=None, encoding='latin1')
        
        # Regra: Coluna J (index 9) deve conter "Pix-Recebido QR Code"
        # Regra: Pegar valor da Coluna K (index 10)
        # Verifica se a coluna 9 existe antes de filtrar
        if 9 in df_bb.columns and 10 in df_bb.columns:
            mask = df_bb[9].astype(str).str.contains("Pix-Recebido QR Code", case=False, na=False)
            df_bb_filtered = df_bb[mask]
            
            bb_values = []
            for val in df_bb_filtered[10]:
                if isinstance(val, str):
                    # Converte "1.200,50" para float
                    val = val.replace('.', '').replace(',', '.')
                bb_values.append(float(val))
                
            st.success(f"Extrato BB processado: {len(bb_values)} lançamentos de QR Code encontrados.")
        else:
            st.error("O arquivo do Banco não tem as colunas esperadas (J e K). Verifique o formato.")
            st.stop()
        
    except Exception as e:
        st.error(f"Erro ao ler Extrato BB: {e}")
        st.stop()

    # --- Comparação (Lógica de Contagem) ---
    pix_counter = Counter(pix_values)
    bb_counter = Counter(bb_values)
    
    missing_in_bb = [] # Está no Pix, falta no Banco
    extra_in_bb = []   # Está no Banco, falta no Pix
    matched = []       # Bateu
    
    all_unique_vals = set(list(pix_counter.keys()) + list(bb_counter.keys()))
    
    for val in all_unique_vals:
        qtd_pix = pix_counter[val]
        qtd_bb = bb_counter[val]
        
        # O que bateu (mínimo entre os dois)
        matches = min(qtd_pix, qtd_bb)
        matched.extend([val] * matches)
        
        # Diferenças
        if qtd_pix > qtd_bb:
            diff = qtd_pix - qtd_bb
            missing_in_bb.extend([val] * diff)
            
        if qtd_bb > qtd_pix:
            diff = qtd_bb - qtd_pix
            extra_in_bb.extend([val] * diff)
            
    # --- Exibição dos Resultados ---
    st.divider()
    st.subheader("Resultados da Conferência")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Confirmados", len(matched))
    col2.metric("Faltam no Banco", len(missing_in_bb), delta_color="inverse")
    col3.metric("Sobram no Banco", len(extra_in_bb), delta_color="off")
    
    c1, c2 = st.columns(2)
    
    with c1:
        st.write("### ⚠️ Faltam no Extrato BB (Estão na Planilha)")
        if missing_in_bb:
            df_missing = pd.DataFrame(missing_in_bb, columns=["Valor"])
            # Formatação para moeda
            st.dataframe(df_missing.style.format("{:.2f}"), height=300)
        else:
            st.info("Nenhum valor faltando no banco.")
            
    with c2:
        st.write("### ❓ Extras no Extrato BB (Não estão na Planilha)")
        if extra_in_bb:
            df_extra = pd.DataFrame(extra_in_bb, columns=["Valor"])
            st.dataframe(df_extra.style.format("{:.2f}"), height=300)
        else:
            st.success("Nenhum valor extra inesperado no banco.")
