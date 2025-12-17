import streamlit as st
import pandas as pd
from collections import Counter

# Configuração da página
st.set_page_config(page_title="Conferência Pix vs Banco", layout="wide")

st.title("Conferência de Pix: Excel vs Extrato BB")
st.markdown("""
**Instruções:**
1. Faça upload da Planilha de Pix (.xlsx ou .csv)
2. Faça upload do Extrato do Banco (.csv)
3. O sistema irá comparar os valores ignorando as datas.
""")

# Upload dos arquivos
uploaded_pix = st.file_uploader("Carregar Planilha Pix (Excel .xlsx ou CSV)", type=["xlsx", "csv"])
uploaded_bb = st.file_uploader("Carregar Extrato BB (CSV)", type=["csv"])

if uploaded_pix and uploaded_bb:
    st.divider()
    
    # ==========================================
    # 1. PROCESSAMENTO DA PLANILHA PIX
    # ==========================================
    pix_values = []
    try:
        # Detecta se é Excel ou CSV pela extensão do arquivo
        if uploaded_pix.name.endswith('.xlsx'):
            df_pix = pd.read_excel(uploaded_pix, header=None)
        else:
            # Se for CSV, tenta ler detectando separador e encoding automaticamente
            try:
                uploaded_pix.seek(0)
                df_pix = pd.read_csv(uploaded_pix, header=None, sep=None, engine='python')
            except:
                uploaded_pix.seek(0)
                df_pix = pd.read_csv(uploaded_pix, header=None, encoding='latin1', sep=None, engine='python')

        # Extração: Coluna D (índice 3)
        vals_1 = []
        if len(df_pix.columns) > 3:
            # Pega colunas C e D (Indices 2 e 3) para checar o rótulo "Total"
            col_d = df_pix[[2, 3]].dropna()
            for i, row in col_d.iterrows():
                label = str(row[2]) if pd.notna(row[2]) else ""
                # Ignora se tiver "Total" escrito ao lado
                if "Total" not in label:
                    try:
                        vals_1.append(float(row[3]))
                    except:
                        pass # Ignora se não for número
        
        # Extração: Coluna I (índice 8)
        vals_2 = []
        if len(df_pix.columns) > 8:
            # Pega colunas H e I (Indices 7 e 8)
            col_i = df_pix[[7, 8]].dropna()
            for i, row in col_i.iterrows():
                label = str(row[7]) if pd.notna(row[7]) else ""
                if "Total" not in label:
                    try:
                        vals_2.append(float(row[8]))
                    except:
                        pass

        # Junta tudo numa lista só
        pix_values = vals_1 + vals_2
        
        if not pix_values:
            st.warning("⚠️ Nenhum valor encontrado na planilha Pix. Verifique se os dados estão nas colunas D e I.")
        else:
            st.success(f"✅ Planilha Pix processada: {len(pix_values)} lançamentos encontrados.")
        
    except Exception as e:
        st.error(f"Erro ao ler planilha Pix: {e}")
        st.stop()

    # ==========================================
    # 2. PROCESSAMENTO DO EXTRATO BB
    # ==========================================
    bb_values = []
    try:
        # Tenta ler CSV com encoding comum de bancos (latin1)
        try:
            df_bb = pd.read_csv(uploaded_bb, sep=';', header=None, encoding='latin1')
        except:
            uploaded_bb.seek(0)
            df_bb = pd.read_csv(uploaded_bb, sep=';', header=None, encoding='utf-8')
        
        # Verifica colunas J (9) e K (10)
        if len(df_bb.columns) > 10:
            # Filtra apenas linhas onde Coluna J contém "Pix-Recebido QR Code"
            mask = df_bb[9].astype(str).str.contains("Pix-Recebido QR Code", case=False, na=False)
            df_bb_filtered = df_bb[mask]
            
            # Pega os valores da Coluna K
            for val in df_bb_filtered[10]:
                try:
                    if isinstance(val, str):
                        # Converte formato brasileiro (1.000,00 -> 1000.00)
                        val = val.replace('.', '').replace(',', '.')
                    bb_values.append(float(val))
                except:
                    pass
                
            st.success(f"✅ Extrato BB processado: {len(bb_values)} lançamentos de QR Code encontrados.")
        else:
            st.error("❌ O arquivo do Banco não tem colunas suficientes (esperado até a coluna K).")
            st.stop()
            
    except Exception as e:
        st.error(f"Erro ao ler Extrato BB: {e}")
        st.stop()

    # ==========================================
    # 3. COMPARAÇÃO E RESULTADOS
    # ==========================================
    if pix_values and bb_values:
        # Usa Counter para lidar com duplicatas (ex: três notas de 50 reais)
        pix_counter = Counter(pix_values)
        bb_counter = Counter(bb_values)
        
        missing_in_bb = [] # Está no Pix, falta no Banco
        extra_in_bb = []   # Está no Banco, falta no Pix
        matched = []       # Bateu
        
        # Pega todos os valores únicos que aparecem em qualquer um dos arquivos
        all_unique_vals = set(list(pix_counter.keys()) + list(bb_counter.keys()))
        
        for val in all_unique_vals:
            qtd_pix = pix_counter[val]
            qtd_bb = bb_counter[val]
            
            # Quantidade confirmada (o mínimo entre os dois)
            matches = min(qtd_pix, qtd_bb)
            matched.extend([val] * matches)
            
            # Se tem mais no Pix -> Falta no Banco
            if qtd_pix > qtd_bb:
                diff = qtd_pix - qtd_bb
                missing_in_bb.extend([val] * diff)
                
            # Se tem mais no Banco -> Extra no Banco
            if qtd_bb > qtd_pix:
                diff = qtd_bb - qtd_pix
                extra_in_bb.extend([val] * diff)
                
        # --- Exibição ---
        st.divider()
        st.header("📊 Resultados da Conferência")
        
        # Métricas no topo
        col1, col2, col3 = st.columns(3)
        col1.metric("Confirmados", len(matched))
        col2.metric("Faltam no Banco", len(missing_in_bb), delta_color="inverse")
        col3.metric("Sobram no Banco", len(extra_in_bb), delta_color="off")
        
        st.markdown("---")
        
        # Tabelas lado a lado
        c1, c2 = st.columns(2)
        
        with c1:
            st.subheader("⚠️ Faltam no Extrato BB")
            st.markdown("**Estão na Planilha, mas o Banco não mostra.**")
            if missing_in_bb:
                df_missing = pd.DataFrame(missing_in_bb, columns=["Valor"])
                # Exibe com formatação de moeda R$
                st.dataframe(df_missing.style.format("R$ {:.2f}"), height=400, use_container_width=True)
            else:
                st.success("Tudo certo! Nada faltando.")
                
        with c2:
            st.subheader("❓ Extras no Extrato BB")
            st.markdown("**Aparecem no Banco, mas não estão na Planilha.**")
            if extra_in_bb:
                df_extra = pd.DataFrame(extra_in_bb, columns=["Valor"])
                st.dataframe(df_extra.style.format("R$ {:.2f}"), height=400, use_container_width=True)
            else:
                st.success("Tudo certo! Nada sobrando.")
