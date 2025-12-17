import streamlit as st
import pandas as pd

# Configuração da página
st.set_page_config(page_title="Conferência Pix vs Banco", layout="wide")

st.title("Conferência de Pix: Excel vs Extrato BB")
st.markdown("""
**Instruções:**
1. Faça upload da Planilha de Pix (.xlsx ou .csv)
2. Faça upload do Extrato do Banco (.csv)
3. O sistema irá comparar os valores e indicar a **Linha do Excel** para conferência.
""")

# Upload dos arquivos
uploaded_pix = st.file_uploader("Carregar Planilha Pix (Excel .xlsx ou CSV)", type=["xlsx", "csv"])
uploaded_bb = st.file_uploader("Carregar Extrato BB (CSV)", type=["csv"])

if uploaded_pix and uploaded_bb:
    st.divider()
    
    # ==========================================
    # 1. PROCESSAMENTO DA PLANILHA PIX (COM LINHAS)
    # ==========================================
    pix_entries = [] # Lista de dicionários: {'val': 10.0, 'row': 5, 'col': 'D'}
    
    try:
        # Detecta se é Excel ou CSV
        if uploaded_pix.name.endswith('.xlsx'):
            df_pix = pd.read_excel(uploaded_pix, header=None)
        else:
            try:
                uploaded_pix.seek(0)
                df_pix = pd.read_csv(uploaded_pix, header=None, sep=None, engine='python')
            except:
                uploaded_pix.seek(0)
                df_pix = pd.read_csv(uploaded_pix, header=None, encoding='latin1', sep=None, engine='python')

        # Extração: Coluna D (índice 3)
        if len(df_pix.columns) > 3:
            col_d = df_pix[[2, 3]].dropna()
            for index, row in col_d.iterrows():
                label = str(row[2]) if pd.notna(row[2]) else ""
                if "Total" not in label:
                    try:
                        val = float(row[3])
                        # index + 1 para corresponder à linha do Excel (que começa em 1)
                        pix_entries.append({'valor': val, 'linha': index + 1, 'coluna': 'D'})
                    except:
                        pass
        
        # Extração: Coluna I (índice 8)
        if len(df_pix.columns) > 8:
            col_i = df_pix[[7, 8]].dropna()
            for index, row in col_i.iterrows():
                label = str(row[7]) if pd.notna(row[7]) else ""
                if "Total" not in label:
                    try:
                        val = float(row[8])
                        pix_entries.append({'valor': val, 'linha': index + 1, 'coluna': 'I'})
                    except:
                        pass
        
        if not pix_entries:
            st.warning("⚠️ Nenhum valor encontrado na planilha Pix.")
        else:
            st.success(f"✅ Planilha Pix processada: {len(pix_entries)} lançamentos.")
        
    except Exception as e:
        st.error(f"Erro ao ler planilha Pix: {e}")
        st.stop()

    # ==========================================
    # 2. PROCESSAMENTO DO EXTRATO BB
    # ==========================================
    bb_values = []
    try:
        try:
            df_bb = pd.read_csv(uploaded_bb, sep=';', header=None, encoding='latin1')
        except:
            uploaded_bb.seek(0)
            df_bb = pd.read_csv(uploaded_bb, sep=';', header=None, encoding='utf-8')
        
        if len(df_bb.columns) > 10:
            mask = df_bb[9].astype(str).str.contains("Pix-Recebido QR Code", case=False, na=False)
            df_bb_filtered = df_bb[mask]
            
            for val in df_bb_filtered[10]:
                try:
                    if isinstance(val, str):
                        val = val.replace('.', '').replace(',', '.')
                    bb_values.append(float(val))
                except:
                    pass
            st.success(f"✅ Extrato BB processado: {len(bb_values)} lançamentos de QR Code.")
        else:
            st.error("❌ Arquivo do Banco inválido.")
            st.stop()
            
    except Exception as e:
        st.error(f"Erro ao ler Extrato BB: {e}")
        st.stop()

    # ==========================================
    # 3. COMPARAÇÃO DETALHADA
    # ==========================================
    if pix_entries and bb_values:
        
        # Cria uma cópia da lista do banco para ir removendo os encontrados
        bb_pool = list(bb_values)
        
        missing_entries = [] # Pix que não achou no BB
        matched_entries = [] # Pix que achou no BB
        
        # Itera sobre cada entrada da planilha Pix (linha por linha)
        for entry in pix_entries:
            val = entry['valor']
            
            # Tenta encontrar o valor no pool do banco
            if val in bb_pool:
                bb_pool.remove(val) # Remove para não casar duplicado errado
                matched_entries.append(entry)
            else:
                missing_entries.append(entry)
        
        # O que sobrou no bb_pool são os Extras
        extra_in_bb = bb_pool
        
        # --- Exibição ---
        st.divider()
        st.header("📊 Resultados Detalhados")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Confirmados", len(matched_entries))
        col2.metric("Faltam no Banco", len(missing_entries), delta_color="inverse")
        col3.metric("Sobram no Banco", len(extra_in_bb), delta_color="off")
        
        st.markdown("---")
        
        c1, c2 = st.columns(2)
        
        with c1:
            st.subheader("⚠️ Faltam no Extrato BB")
            st.markdown("**Estão na Planilha (Pix), mas não no Banco.**")
            if missing_entries:
                df_missing = pd.DataFrame(missing_entries)
                # Reordena colunas para facilitar leitura
                df_missing = df_missing[['linha', 'coluna', 'valor']]
                st.dataframe(
                    df_missing.style.format({'valor': 'R$ {:.2f}', 'linha': '{:.0f}'}), 
                    height=500, 
                    use_container_width=True
                )
            else:
                st.info("Nada faltando.")
                
        with c2:
            st.subheader("❓ Extras no Extrato BB")
            st.markdown("**Estão no Banco, mas não na Planilha.**")
            if extra_in_bb:
                df_extra = pd.DataFrame(extra_in_bb, columns=["Valor"])
                st.dataframe(df_extra.style.format("R$ {:.2f}"), height=500, use_container_width=True)
            else:
                st.success("Nada sobrando.")
