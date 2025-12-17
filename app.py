import streamlit as st
import pandas as pd
from collections import Counter

st.set_page_config(page_title="Conferência Pix vs Banco", layout="wide")

st.title("Conferência de Pix: Excel vs Extrato BB")
st.markdown("""
**Instruções:**
1. Faça upload da Planilha de Pix (pode ser **.xlsx** ou .csv)
2. Faça upload do Extrato do Banco (.csv)
3. O sistema irá comparar os valores ignorando as datas.
""")

# Upload dos arquivos
uploaded_pix = st.file_uploader("Carregar Planilha Pix (Excel .xlsx ou CSV)", type=["xlsx", "csv"])
uploaded_bb = st.file_uploader("Carregar Extrato BB (CSV)", type=["csv"])

if uploaded_pix and uploaded_bb:
    st.divider()
    
    # --- Processamento do Arquivo Pix ---
    # Função para ler o arquivo dependendo da extensão
    try:
        if uploaded_pix.name.endswith('.xlsx'):
            # Lê como Excel
            df_pix = pd.read_excel(uploaded_pix, header=None)
        else:
            # Lê como CSV (tenta detectar separador automaticamente)
            try:
                uploaded_pix.seek(0)
                df_pix = pd.read_csv(uploaded_pix, header=None, sep=None, engine='python')
            except:
                uploaded_pix.seek(0)
                df_pix = pd.read_csv(uploaded_pix, header=None, encoding='latin1', sep=None, engine='python')

        # Lógica para extrair valores (Colunas D e I -> índices 3 e 8)
        vals_1 = []
        # Verifica e pega Coluna D (index 3)
        if len(df_pix.columns) > 3:
            col_d = df_pix[[2, 3]].dropna()
            for i, row in col_d.iterrows():
                # Garante que é string antes de verificar "Total"
                label = str(row[2]) if pd.notna(row[2]) else ""
                if "Total" not in label:
                    # Tenta converter para float, ignorando erros
                    try:
                        vals_1.append(float(row[3]))
                    except:
                        pass
        
        # Verifica e pega Coluna I (index 8)
        vals_2 = []
        if len(df_pix.columns) > 8:
            col_i = df_pix[[7, 8]].dropna()
            for i, row in col_i.iterrows():
                label = str(row[7]) if pd.notna(row[7]) else ""
                if "Total" not in label:
                    try:
                        vals_2.append(float(row[8]))
                    except:
                        pass
        
        # Lista final de valores esperados (Planilha)
        pix_values = vals_1 + vals_2
        
        if len(pix_values) == 0:
            st.warning("Aviso: Nenhum valor encontrado na planilha Pix. Verifique se as colunas D e I contêm os valores.")
        else:
            st.success(f"Planilha Pix processada: {len(pix_values)} lançamentos encontrados.")
        
    except Exception as e:
        st.error(f"Erro ao ler planilha Pix: {e}")
        st.stop()

    # --- Processamento do Arquivo BB ---
    try:
        # Tenta ler o CSV do banco com encoding latin1 (comum em bancos brasileiros)
        try:
            df_bb = pd.read_csv(uploaded_bb, sep=';', header=None, encoding='latin1')
        except:
             # Fallback: tenta utf-8
            uploaded_bb.seek(0)
            df_bb = pd.read_csv(uploaded_bb, sep=';', header=None, encoding='utf-8')
        
        # Verifica se as colunas necessárias existem (J=9, K=10)
        if len(df_bb.columns) > 10:
            # Filtra onde a coluna J (9) contém "Pix-Recebido QR Code"
            mask = df_bb[9].astype(str).str.contains("Pix-Recebido QR Code", case=False, na=False)
            df_bb_filtered = df_bb[mask]
            
            bb_values = []
            for val in df_bb_filtered[10]:
                try:
                    if isinstance(val, str):
                        # Converte formato brasileiro "1.200,50" -> float 1200.50
                        val = val.replace('.', '').replace(',', '.')
                    bb_values.append(float(val))
                except:
                    pass
                
            st.success(f"Extrato BB processado: {len(bb_values)} lançamentos de QR Code encontrados.")
        else:
            st.error("O arquivo do Banco não parece ter colunas suficientes (esperado até a coluna K).")
            st.stop()
            
    except Exception as e:
        st.error(f"Erro ao ler Extrato BB: {e}")
        st.stop()

    # --- Comparação ---
    if pix_values and bb_values:
        pix_counter = Counter(pix_values)
        bb_counter = Counter(bb_values)
        
        missing_in_bb = [] # Está no Pix, falta no Banco
        extra_in_bb = []   # Está no Banco, falta no Pix
        matched = []       # Bateu
        
        all_unique_vals = set(list(pix_counter.keys()) + list(bb_counter.keys()))
        
        for val in all_unique_vals:
            qtd_pix = pix_counter[val]
            qtd_bb = bb_counter[val]
            
            # O que bateu
            matches = min(qtd_pix, qtd_bb)
            matched.extend([val] * matches)
            
            # Diferenças
            if qtd_pix > qtd_bb:
                diff = qtd_pix - qtd_bb
                missing_in_bb.extend([val] * diff)
                
            if qtd_bb > qtd_pix:
                diff = qtd_bb - qtd_pix
                extra_in_bb.extend([val] * diff)
                
        # --- Exibição ---
        st.divider()
        st.subheader("Resultados da Conferência")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Confirmados", len(matched))
        col2.metric("Faltam no Banco", len(missing_in_bb), delta_color="inverse")
        col3.metric("Sobram no Banco", len(extra_in_bb), delta_color="off")
        
        c1, c2 = st.columns(2)
        
        with c1:
            st.write("### ⚠️ Faltam no Extrato BB")
            st.caption("Estão na Planilha, mas o Banco não mostra.")
            if missing_in_bb:
                df_missing = pd.DataFrame(missing_in_bb, columns=["Valor"])
                st.dataframe(df_missing.style.format("R$ {:.2f}"), height=300, use_container_width=True)
            else:
                st.info("Tudo certo! Nada faltando.")
                
        with c2:
            st.write("### ❓ Extras no Extrato BB")
            st.caption("Aparecem no Banco, mas não estão na Planilha.")
            if extra_in_bb:
                df_extra = pd.DataFrame(extra_in_bb, columns=["Valor"])
                st.dataframe(df_extra.style.format("R$ {:.2f}"), height=300, use_container_width=True)
            else:
                st.success("Tudo certo! Nada sobrando.")
