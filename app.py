import streamlit as st
import pandas as pd
import openpyxl
from openpyxl.styles.colors import Color
from datetime import datetime
import re

# --- Funções Auxiliares ---

def get_color_info(cell):
    """Retorna informações detalhadas sobre a cor da célula para debug."""
    fill = cell.fill
    if not fill or not fill.start_color:
        return "Sem Preenchimento", None
    
    color = fill.start_color
    
    # Caso 1: Cor RGB direta (Padrão ou Hex)
    if color.type == 'rgb':
        return f"RGB: {color.rgb}", color.rgb
        
    # Caso 2: Cor de Tema (Theme)
    if color.type == 'theme':
        return f"Tema: {color.theme} (Tint: {color.tint})", 'THEME'
    
    # Caso 3: Índice (Legado)
    if color.type == 'indexed':
        return f"Index: {color.indexed}", 'INDEX'
        
    return "Outro", None

def is_green_smart(cell, wb):
    """
    Verifica se a célula é verde, tentando lidar com Temas e RGB.
    """
    fill = cell.fill
    if not fill or not fill.start_color:
        return False
    
    color = fill.start_color
    hex_code = None

    # Tenta obter o código Hex
    if color.type == 'rgb':
        hex_code = color.rgb 
    elif color.type == 'theme':
        # Tentar estimar se é verde baseando-se em índices comuns de temas esverdeados
        # (Isso é uma estimativa, pois temas variam)
        # Frequentemente Accent 3 (id 6) ou Accent 6 (id 9) são verdes/azuis
        if color.theme in [5, 6, 9]: 
            return True # Assume verde para temas comuns
        # Se não conseguimos converter, retornamos False por segurança, mas o Debug vai avisar
        return False
        
    if hex_code:
        try:
            # Limpa o canal Alpha se existir (ex: FF00FF00 -> 00FF00)
            if len(hex_code) > 6:
                hex_code = hex_code[2:] 
                
            if len(hex_code) == 6:
                r = int(hex_code[0:2], 16)
                g = int(hex_code[2:4], 16)
                b = int(hex_code[4:6], 16)
                
                # Regra: Verde predominante e intenso
                return g > r and g > b and g > 60
        except:
            pass
            
    return False

def parse_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        # Procura padrões dd/mm/aaaa ou dd/mm/aa
        match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{2,4})', value)
        if match:
            try:
                d, m, y = int(match.group(1)), int(match.group(2)), int(match.group(3))
                if y < 100: y += 2000
                return datetime(y, m, d).date()
            except:
                pass
    return None

# --- Interface Streamlit ---

st.set_page_config(page_title="Controle Unimed 2.0", layout="wide")

st.title("💊 Análise de Atrasos - Unimed")
st.markdown("Verifica células da **Coluna G** (pintadas de verde) e compara com a data de hoje.")

uploaded_file = st.file_uploader("Carregue a planilha (.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        wb = openpyxl.load_workbook(uploaded_file, data_only=True)
        if 'CONTROLE' in wb.sheetnames:
            ws = wb['CONTROLE']
        else:
            ws = wb.active
            
        hoje = datetime.now().date()
        st.info(f"📅 **Data de Hoje:** {hoje.strftime('%d/%m/%Y')} | Aba analisada: {ws.title}")
        
        atrasados = []
        debug_data = [] # Para armazenar infos do Raio-X
        
        # Iterar a partir da linha 8
        for i, row in enumerate(ws.iter_rows(min_row=8, min_col=1, max_col=10), start=8):
            cell_date = row[6] # Coluna G
            cell_name = row[1] # Coluna B
            cell_med = row[3]  # Coluna D
            
            # Pega valor da data
            val_date = cell_date.value
            parsed_date = parse_date(val_date)
            
            # Verifica cor
            e_verde = is_green_smart(cell_date, wb)
            
            # Coleta dados para Debug
            color_desc, _ = get_color_info(cell_date)
            debug_data.append({
                "Linha Excel": i,
                "Paciente": cell_name.value,
                "Conteúdo Coluna G": str(val_date),
                "Data Entendida": parsed_date.strftime('%d/%m/%Y') if parsed_date else "Não detectada",
                "Cor Detectada": color_desc,
                "É Verde?": "SIM" if e_verde else "NÃO"
            })
            
            # Lógica principal
            if e_verde and parsed_date:
                if parsed_date < hoje:
                    atrasados.append({
                        "Linha": i,
                        "Nome do Paciente": cell_name.value,
                        "Medicamento": cell_med.value,
                        "Data Prevista": parsed_date.strftime('%d/%m/%Y'),
                        "Dias de Atraso": (hoje - parsed_date).days
                    })

        # --- Exibição dos Resultados ---
        
        if atrasados:
            st.error(f"🚨 **{len(atrasados)} MEDICAMENTOS ATRASADOS ENCONTRADOS!**")
            df_atrasados = pd.DataFrame(atrasados)
            st.dataframe(df_atrasados.style.background_gradient(cmap="Reds", subset=["Dias de Atraso"]), use_container_width=True)
        else:
            st.success("✅ Nenhum atraso detectado nas células verdes.")
            st.warning("⚠️ Se você vê uma célula verde atrasada e ela não apareceu, verifique o 'Modo Raio-X' abaixo.")

        # --- Modo Raio-X (Debug) ---
        with st.expander("🔍 MODO RAIO-X (Verifique se o programa está lendo a cor correta)"):
            st.write("Veja abaixo como o programa está lendo cada linha. Procure a **Linha 11** (ou a linha do atraso) e veja se a coluna 'É Verde?' diz SIM.")
            df_debug = pd.DataFrame(debug_data)
            st.dataframe(df_debug)

    except Exception as e:
        st.error(f"Erro: {e}")
