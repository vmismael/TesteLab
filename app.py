import streamlit as st
import pandas as pd
import plotly.express as px
import openpyxl
from datetime import datetime
import re

# ---------------------------------------------------------
# FUNÇÕES AUXILIARES (PARA A ABA DE MEDICAMENTOS)
# ---------------------------------------------------------
def is_green(cell):
    """
    Verifica se a célula tem preenchimento verde.
    A lógica verifica se o componente Verde (G) do RGB é predominante.
    """
    fill = cell.fill
    if not fill or not fill.start_color:
        return False
    
    color = fill.start_color
    
    # Verifica se é uma cor RGB definida
    if color.type == 'rgb' and color.rgb:
        hex_code = color.rgb
        # Tratamento para ARGB (ex: FF00FF00) ou RGB (ex: 00FF00)
        try:
            if len(hex_code) == 8: # ARGB
                r = int(hex_code[2:4], 16)
                g = int(hex_code[4:6], 16)
                b = int(hex_code[6:8], 16)
            elif len(hex_code) == 6: # RGB
                r = int(hex_code[0:2], 16)
                g = int(hex_code[2:4], 16)
                b = int(hex_code[4:6], 16)
            else:
                return False
            
            # Lógica simples: Verde deve ser maior que Vermelho e Azul, e ter uma intensidade mínima
            return g > r and g > b and g > 50
        except:
            return False
            
    # Se for cor de tema (Theme), o openpyxl pode não trazer o RGB direto sem converter o tema.
    return False

def parse_date(value):
    if isinstance(value, datetime):
        return value.date()
    
    if isinstance(value, str):
        # Tenta encontrar padrão dd/mm/aaaa ou dd/mm/aa na string (ex: "QT - 23/12/2025")
        match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{2,4})', value)
        if match:
            try:
                d, m, y = int(match.group(1)), int(match.group(2)), int(match.group(3))
                # Ajuste para ano com 2 dígitos
                if y < 100:
                    y += 2000
                return datetime(y, m, d).date()
            except:
                pass
    return None

# ---------------------------------------------------------
# CONFIGURAÇÃO GERAL DA PÁGINA
# ---------------------------------------------------------
st.set_page_config(page_title="Dashboard Integrado", layout="wide")

# Título Principal
st.title("📊 Dashboard Integrado de Gestão")

# ---------------------------------------------------------
# MENU DE NAVEGAÇÃO LATERAL
# ---------------------------------------------------------
st.sidebar.title("Navegação")
pagina_selecionada = st.sidebar.radio(
    "Ir para:",
    ["📋 Análise de Coletas", "⚠️ Mapeamento de Riscos", "💊 Controle de Medicamentos"]
)
st.sidebar.markdown("---")

# =========================================================
# PÁGINA 1: ANÁLISE DE COLETAS POR COLABORADOR
# =========================================================
if pagina_selecionada == "📋 Análise de Coletas":
    st.header("Análise de Produtividade por Colaborador")
    st.markdown("Esta ferramenta analisa o arquivo de coletas (CSV) para contabilizar atendimentos.")

    # Upload do Arquivo de Coletas
    uploaded_file_coletas = st.file_uploader("📂 Carregue o arquivo de Coletas (CSV) aqui", type=["csv"], key="upload_coletas")

    if uploaded_file_coletas:
        try:
            # Tenta ler o arquivo com diferentes encodings
            try:
                df_coletas = pd.read_csv(uploaded_file_coletas, sep=";", encoding='utf-8')
            except UnicodeDecodeError:
                uploaded_file_coletas.seek(0)
                df_coletas = pd.read_csv(uploaded_file_coletas, sep=";", encoding='latin1')
            
            # Lógica de Contagem
            if 'Usuário Nome' in df_coletas.columns and 'O.S.' in df_coletas.columns:
                # Agrupa por Colaborador e conta O.S. únicas
                resumo = df_coletas.groupby('Usuário Nome')['O.S.'].nunique().reset_index()
                resumo.columns = ['Colaborador', 'Qtd. Pacientes Atendidos']
                # Ordenação para o gráfico (crescente) e tabela (decrescente)
                resumo_grafico = resumo.sort_values(by='Qtd. Pacientes Atendidos', ascending=True)
                resumo_tabela = resumo.sort_values(by='Qtd. Pacientes Atendidos', ascending=False).reset_index(drop=True)

                st.subheader("Resumo de Atendimentos")
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.write("**Tabela de Dados:**")
                    st.dataframe(
                        resumo_tabela,
                        use_container_width=True,
                        hide_index=True,
                        height=500,
                        column_config={
                            "Qtd. Pacientes Atendidos": st.column_config.NumberColumn(
                                "Qtd. Pacientes",
                                help="Número total de pacientes únicos atendidos",
                                format="%d"
                            )
                        }
                    )
                    
                with col2:
                    st.write("**Gráfico Visual:**")
                    fig = px.bar(
                        resumo_grafico, 
                        x='Qtd. Pacientes Atendidos', 
                        y='Colaborador', 
                        orientation='h', 
                        text_auto=True,
                        title="Pacientes Atendidos por Colaborador"
                    )
                    
                    fig.update_layout(
                        xaxis_title="Quantidade de Pacientes",
                        yaxis_title="Colaborador",
                        showlegend=False,
                        height=500,
                        margin=dict(r=50)
                    )
                    fig.update_traces(textposition='outside', cliponaxis=False)
                    
                    st.plotly_chart(fig, use_container_width=True)

                st.markdown("---")

                # Detalhes Interativos
                st.subheader("🔎 Detalhes por Colaborador")
                st.info("Selecione um colaborador abaixo para ver a lista detalhada.")

                lista_colaboradores = resumo_tabela['Colaborador'].unique()
                colaborador_selecionado = st.selectbox("Escolha o Colaborador:", lista_colaboradores)

                if colaborador_selecionado:
                    df_filtrado = df_coletas[df_coletas['Usuário Nome'] == colaborador_selecionado].copy()
                    
                    colunas_detalhe = ['Data da Operação', 'O.S.', 'Paciente', 'Paciente Nome', 'Detalhe Descrição']
                    cols_existentes = [c for c in colunas_detalhe if c in df_filtrado.columns]
                    df_detalhe_final = df_filtrado[cols_existentes]
                    
                    df_detalhe_unico = df_detalhe_final.drop_duplicates(subset=['O.S.'])

                    st.write(f"**Pacientes atendidos por: {colaborador_selecionado}**")
                    st.dataframe(df_detalhe_unico, use_container_width=True, hide_index=True)
                    
                    csv = df_detalhe_unico.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Baixar detalhes (CSV)",
                        data=csv,
                        file_name=f'detalhes_{colaborador_selecionado}.csv',
                        mime='text/csv',
                    )
            else:
                st.error("O arquivo carregado não possui as colunas 'Usuário Nome' ou 'O.S.'. Verifique se o arquivo está correto.")

        except Exception as e:
            st.error(f"Ocorreu um erro ao processar o arquivo de coletas: {e}")
    else:
        st.info("Por favor, carregue o arquivo CSV de coletas para visualizar os dados.")

# =========================================================
# PÁGINA 2: MAPEAMENTO DE RISCOS
# =========================================================
elif pagina_selecionada == "⚠️ Mapeamento de Riscos":
    st.header("Análise de Riscos Institucionais - Alta e Muito Alta Gravidade")
    st.markdown("""
    Esta ferramenta analisa o arquivo de Mapeamento de Riscos (Excel ou CSV) e filtra eventos classificados como **Alto** ou **Muito Alto**.
    Códigos considerados: `2A`, `3A`, `4A`, `5A`, `3B`, `4B`, `5B`, `5C`.
    """)

    uploaded_file_riscos = st.file_uploader("📂 Carregue seu arquivo Excel ou CSV de Riscos aqui", type=["xlsx", "csv"], key="upload_riscos")

    if uploaded_file_riscos:
        try:
            is_csv = uploaded_file_riscos.name.lower().endswith('.csv')
            
            if is_csv:
                sheet_names = ["Arquivo CSV"]
            else:
                xl = pd.ExcelFile(uploaded_file_riscos)
                sheet_names = [s for s in xl.sheet_names if "Legenda" not in s]
            
            st.sidebar.header("Filtros (Riscos)")
            selected_sheet = st.sidebar.selectbox("Selecione o Setor (Aba):", sheet_names)
            
            months = ['JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ']
            selected_month = st.sidebar.selectbox("Selecione o Mês:", months)
            
            if st.sidebar.button("🔍 Buscar Riscos", key="btn_buscar_riscos"):
                
                if is_csv:
                    uploaded_file_riscos.seek(0) 
                    df_riscos = pd.read_csv(uploaded_file_riscos, header=None, sep=';', encoding='latin1')
                else:
                    df_riscos = pd.read_excel(uploaded_file_riscos, sheet_name=selected_sheet, header=None)
                
                target_risks = ['2A', '3A', '4A', '5A', '3B', '4B', '5B', '5C']
                
                month_idx = months.index(selected_month)
                content_col_index = 8 + (month_idx * 2)
                risk_col_index = content_col_index + 1
                
                results = []
                
                for index, row in df_riscos.iterrows():
                    first_col = str(row[0])
                    if pd.isna(row[0]) or first_col.strip() in [
                        'FONTE', 'IDENTIFICAÇÃO DO RISCO', 'Identificação do Risco', 
                        'Riscos Institucionais Gerenciados', 
                        'Riscos Institucionais  não Gerenciados/Inventariados', 
                        'C.H.O.R.C.'
                    ]:
                        continue
                    
                    if len(row) > risk_col_index:
                        risk_value = str(row[risk_col_index]).strip().upper()
                        
                        if risk_value in target_risks:
                            results.append({
                                "Identificação do Risco": row[0],
                                "Causa": row[1],
                                f"Conteúdo ({selected_month})": row[content_col_index],
                                "Classificação": risk_value
                            })
                
                if results:
                    st.success(f"Foram encontrados {len(results)} riscos com gravidade Alta/Muito Alta em {selected_sheet} no mês de {selected_month}.")
                    df_results = pd.DataFrame(results)
                    st.dataframe(df_results, use_container_width=True, hide_index=True)
                else:
                    st.info(f"Nenhum risco alto ou muito alto encontrado em {selected_sheet} para {selected_month}.")
                    
        except Exception as e:
            st.error(f"Erro ao processar o arquivo: {e}")
    else:
        st.info("Por favor, carregue o arquivo Excel ou CSV na área acima para começar a análise de riscos.")

# =========================================================
# PÁGINA 3: CONTROLE DE MEDICAMENTOS
# =========================================================
elif pagina_selecionada == "💊 Controle de Medicamentos":
    st.header("Análise de Retirada de Medicamentos")
    st.markdown("""
    Esta ferramenta analisa o arquivo Excel de controle e identifica:
    1. Células na **Coluna G** (a partir da linha 8) pintadas de **Verde**.
    2. Verifica se a data nessas células está **atrasada** em relação ao dia de hoje.
    """)

    # Upload do Arquivo
    uploaded_file_med = st.file_uploader("📂 Carregue sua planilha Excel (.xlsx) de Medicamentos", type=["xlsx"], key="upload_med")

    if uploaded_file_med:
        try:
            # Carregar o workbook com openpyxl para acessar cores
            wb = openpyxl.load_workbook(uploaded_file_med, data_only=True)
            
            # Tenta pegar a aba ativa ou a aba 'CONTROLE' se existir
            if 'CONTROLE' in wb.sheetnames:
                ws = wb['CONTROLE']
            else:
                ws = wb.active
                
            st.info(f"Analisando a aba: **{ws.title}**")
            
            # Data de hoje
            hoje = datetime.now().date()
            st.write(f"📅 **Data da Análise:** {hoje.strftime('%d/%m/%Y')}")
            
            atrasados = []
            
            # Iterar sobre as linhas a partir da linha 8
            # Coluna G é a 7ª coluna (índice 6)
            for row in ws.iter_rows(min_row=8, min_col=1, max_col=10):
                cell_date = row[6] # Coluna G (índice 6 base 0)
                cell_name = row[1] # Coluna B (Nome Cliente)
                cell_med = row[3]  # Coluna D (Medicamento)
                
                # Verifica a cor
                if is_green(cell_date):
                    data_retirada = parse_date(cell_date.value)
                    
                    if data_retirada:
                        # Verifica se está atrasado (Data Retirada < Hoje)
                        if data_retirada < hoje:
                            atrasados.append({
                                "Nome do Paciente": cell_name.value,
                                "Medicamento": cell_med.value,
                                "Data Prevista": data_retirada.strftime('%d/%m/%Y'),
                                "Dias de Atraso": (hoje - data_retirada).days
                            })
            
            # Resultados
            if atrasados:
                df_atrasados = pd.DataFrame(atrasados)
                
                st.error(f"🚨 Foram encontrados **{len(df_atrasados)}** medicamentos atrasados para retirada!")
                
                # Exibir tabela com gradiente
                st.dataframe(
                    df_atrasados.style.background_gradient(cmap="Reds", subset=["Dias de Atraso"]),
                    use_container_width=True,
                    hide_index=True
                )
                
                # Opção de download
                csv = df_atrasados.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Baixar Relatório de Atrasados (CSV)",
                    data=csv,
                    file_name="medicamentos_atrasados.csv",
                    mime="text/csv"
                )
                
            else:
                st.success("✅ Nenhum medicamento disponível (verde) está atrasado para retirada hoje!")
                
        except Exception as e:
            st.error(f"Ocorreu um erro ao processar o arquivo: {e}")
            st.warning("Certifique-se de que o arquivo é um Excel (.xlsx) válido e não está corrompido.")
    else:
        st.info("Por favor, carregue o arquivo Excel na área acima.")
