import streamlit as st
import pandas as pd
import qrcode
from io import BytesIO
from datetime import datetime
import os
from PIL import Image, ImageDraw, ImageFont
import zipfile
import tempfile

st.set_page_config(page_title="Corta-Mato ESM", layout="wide")

DATA_FILE = "data/inscricoes.csv"
DORSAL_DIR = "data/dorsais"

# --- Função para gerar dorsal A6 com QR e dados ---
def gerar_dorsal_a6(nome, processo, escalao, turma):
    # Dimensões A6 a 300 DPI
    A6_WIDTH = 1240
    A6_HEIGHT = 1748

    dorsal = Image.new("RGB", (A6_WIDTH, A6_HEIGHT), "white")
    draw = ImageDraw.Draw(dorsal)

    draw.rectangle([(1, 1), (A6_WIDTH - 15, A6_HEIGHT - 15)], outline="black", width=4)

    qr_size = int(A6_HEIGHT * 0.60)
    url = f"https://cortamatoesm.streamlit.app/?chegada={processo}"
    qr_img = qrcode.make(url).resize((qr_size, qr_size))
    qr_x = (A6_WIDTH - qr_size) // 2
    dorsal.paste(qr_img, (qr_x, 0))

    bottom_y = qr_size
    center_x = A6_WIDTH // 2
    FONT_MAIN = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    font_name  = ImageFont.truetype(FONT_MAIN, 60)
    font_proc  = ImageFont.truetype(FONT_MAIN, 60)
    font_esc   = ImageFont.truetype(FONT_MAIN, 60)
    font_turma = ImageFont.truetype(FONT_MAIN, 60)

    # Espaçamentos
    linha1_y = bottom_y + 40
    linha2_y = bottom_y + 250
    linha3_y = bottom_y + 350
    linha4_y = bottom_y + 450

    # Dividir nome longo
    partes_nome = nome.split()
    if len(partes_nome) > 3:
        meio = len(partes_nome) // 2
        nome_linha1 = " ".join(partes_nome[:meio])
        nome_linha2 = " ".join(partes_nome[meio:])
    else:
        nome_linha1 = nome
        nome_linha2 = None

    draw.text((center_x, linha1_y), nome_linha1, fill="black", font=font_name, anchor="mm")
    if nome_linha2:
        draw.text((center_x, linha1_y + 80), nome_linha2, fill="black", font=font_name, anchor="mm")
    draw.text((center_x, linha2_y), str(processo), fill="black", font=font_proc, anchor="mm")
    draw.text((center_x, linha3_y), escalao, fill="black", font=font_esc, anchor="mm")
    draw.text((center_x, linha4_y), turma, fill="black", font=font_turma, anchor="mm")

    buffer = BytesIO()
    dorsal.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.getvalue()

# --- Função para autenticação ---
def autenticar():
    senha = st.sidebar.text_input("🔒 Palavra-passe (admin)", type="password")
    if senha == "admin123":
        return True
    elif senha:
        st.sidebar.warning("Senha incorreta.")
    return False

acesso_admin = autenticar()

# --- Menu lateral com key para evitar duplo clique ---
if acesso_admin:
    menu = st.sidebar.radio(
        "Menu",
        ["Nova Inscrição", "Lista de Inscritos", "Lista de Inscritos (admin)", "Chegadas", "Classificações"],
        key="menu_admin"
    )
else:
    menu = st.sidebar.radio(
        "Menu",
        ["Nova Inscrição", "Lista de Inscritos", "Chegadas"],
        key="menu_user"
    )

# --- Carregar dados de alunos ---
@st.cache_data
def load_data():
    df_raw = pd.read_excel("ListagemAlunos_25_26.xlsx", sheet_name=0, header=0)
    df = pd.DataFrame()
    df["processo"] = pd.to_numeric(df_raw.iloc[:, 0], errors="coerce")
    df["nome"] = df_raw.iloc[:, 1].astype(str).str.strip()
    df["género"] = df_raw.iloc[:, 2].astype(str).str.strip()
    df["data_nascimento"] = pd.to_datetime(df_raw.iloc[:, 3], errors="coerce")
    df["CC"] = df_raw.iloc[:, 4].astype(str).str.strip()
    df["turma"] = df_raw.iloc[:, 5].astype(str).str.strip()
    df = df[df["processo"].notnull()]
    df["processo"] = df["processo"].astype("Int64")
    return df

def get_escalão(data_nascimento):
    if isinstance(data_nascimento, str):
        data_nascimento = datetime.strptime(data_nascimento, "%Y-%m-%d")
    if datetime(2015,1,1) <= data_nascimento <= datetime(2017,12,31):
        return "Infantil A"
    elif datetime(2013,1,1) <= data_nascimento <= datetime(2014,12,31):
        return "Infantil B"
    elif datetime(2011,1,1) <= data_nascimento <= datetime(2012,12,31):
        return "Iniciado"
    elif datetime(2008,1,1) <= data_nascimento <= datetime(2010,12,31):
        return "Juvenil"
    elif datetime(2004,1,1) <= data_nascimento <= datetime(2007,12,31):
        return "Júnior"
    else:
        return "Fora de escalão"

df = load_data()

# --- Função para carregar inscrições ---
def load_inscricoes():
    if os.path.exists(DATA_FILE):
        inscritos = pd.read_csv(DATA_FILE, dtype=str).fillna("")
    else:
        inscritos = pd.DataFrame(columns=[
            "Processo", "Nome", "Data nascimento", "Género", "Turma", "Escalão", "Tempo", "QR", "Classificação", "Hora"
        ])
    # Garantir colunas
    for col in ["Classificação", "Hora", "Tempo", "QR"]:
        if col not in inscritos.columns:
            inscritos[col] = ""
    return inscritos

# --- Menu: Nova Inscrição ---
if menu == "Nova Inscrição":
    st.subheader("🆕 Nova Inscrição")
    processo_input = st.text_input("Número de processo do aluno")
    if processo_input:
        try:
            processo = int(processo_input)
            aluno_base = df[df["processo"] == processo]
            if aluno_base.empty:
                st.error("❌ Processo não encontrado na base de dados.")
            else:
                dados = aluno_base.iloc[0]
                escalão = get_escalão(dados["data_nascimento"])

                with st.expander("📋 Dados do aluno"):
                    st.markdown(f"**Nome:** {dados['nome']}")
                    st.markdown(f"**Data de nascimento:** {dados['data_nascimento'].strftime('%d-%m-%Y')}")
                    st.markdown(f"**CC:** {dados['CC']}")
                    st.markdown(f"**Turma:** {dados['turma']}")
                    st.markdown(f"**Género:** {dados['género']}")
                    st.markdown(f"**Escalão:** {escalão}")

                inscritos = load_inscricoes()
                if str(processo) in inscritos["Processo"].values:
                    st.warning("⚠️ Este aluno já está inscrito.")
                else:
                    if st.button("✅ Confirmar inscrição"):
                        dorsal_img = gerar_dorsal_a6(dados["nome"], processo, escalão, dados["turma"])
                        os.makedirs(DORSAL_DIR, exist_ok=True)
                        qr_path = f"{DORSAL_DIR}/{processo}_{escalão}_{dados['género']}.png"
                        with open(qr_path, "wb") as f:
                            f.write(dorsal_img)

                        novo = pd.DataFrame([[processo, dados["nome"], dados["data_nascimento"], dados["género"],
                                              dados["turma"], escalão, "", qr_path, "", ""]],
                                            columns=inscritos.columns)
                        inscritos = pd.concat([inscritos, novo], ignore_index=True)
                        inscritos.to_csv(DATA_FILE, index=False)
                        st.success(f"✅ {dados['nome']} inscrito com sucesso!")
                        st.image(dorsal_img, width=300)
        except ValueError:
            st.error("⚠️ Introduz um número de processo válido.")

# --- Menu: Lista de Inscritos ---
elif menu == "Lista de Inscritos":
    st.subheader("📋 Lista de Inscrições")
    inscritos = load_inscricoes()
    processo = st.text_input("🔍 Pesquisar por número de processo", key="busca_lista")
    if processo:
        try:
            processo = int(processo)
            aluno = inscritos[inscritos["Processo"] == str(processo)]
            if not aluno.empty:
                dados = aluno.iloc[0]
                st.success(f"✅ Aluno encontrado: {dados['Nome']}")
                st.write(f"📅 Data de nascimento: {dados['Data nascimento']}")
                st.write(f"🏫 Turma: {dados['Turma']}")
                st.write(f"🎽 Escalão: {dados['Escalão']}")
                st.write(f"👤 Sexo: {dados['Género']}")

                if st.button("🖨️ Imprimir Dorsal"):
                    st.image(dados["QR"], caption=f"Dorsal de {dados['Nome']}", width=200)

                if acesso_admin and st.button("❌ Eliminar inscrição"):
                    inscritos = inscritos[inscritos["Processo"] != str(processo)]
                    inscritos.to_csv(DATA_FILE, index=False)
                    st.warning(f"Inscrição de {dados['Nome']} eliminada.")
            else:
                st.error("❌ Processo não encontrado.")
        except ValueError:
            st.error("⚠️ Introduz um número de processo válido.")

    st.dataframe(inscritos.drop(columns=["Tempo", "QR"], errors="ignore"))
    csv = inscritos.to_csv(index=False).encode('utf-8')
    st.download_button("⬇️ Exportar CSV", csv, "inscricoes.csv", "text/csv")

# --- Menu: Lista de Inscritos (admin) ---
elif menu == "Lista de Inscritos (admin)":
    st.subheader("📋 Lista de Inscrições (Admin)")
    inscritos = load_inscricoes()
    st.dataframe(inscritos.drop(columns=["Tempo", "QR"], errors="ignore"))
    csv = inscritos.to_csv(index=False).encode('utf-8')
    st.download_button("⬇️ Exportar CSV", csv, "inscricoes.csv", "text/csv")

    # Apagar inscrição
    processo = st.text_input("🔍 Eliminar inscrição por número de processo", key="elim_admin")
    if processo:
        try:
            processo = int(processo)
            aluno = inscritos[inscritos["Processo"] == str(processo)]
            if not aluno.empty:
                dados = aluno.iloc[0]
                st.success(f"✅ Aluno encontrado: {dados['Nome']}")
                st.write(f"📅 Data de nascimento: {dados['Data nascimento']}")
                st.write(f"🏫 Turma: {dados['Turma']}")
                st.write(f"🎽 Escalão: {dados['Escalão']}")
                st.write(f"👤 Sexo: {dados['Género']}")
                if st.button("❌ Confirmar eliminação", key=f"elim_{processo}"):
                    inscritos = inscritos[inscritos["Processo"] != str(processo)]
                    inscritos.to_csv(DATA_FILE, index=False)
                    st.warning(f"Inscrição de {dados['Nome']} eliminada.")
            else:
                st.error("❌ Processo não encontrado.")
        except ValueError:
            st.error("⚠️ Introduz um número de processo válido.")

    # Apagar todas inscrições
    if st.button("🧹 Apagar todas as inscrições"):
        if os.path.exists(DATA_FILE):
            os.remove(DATA_FILE)
            st.success("✅ Todas as inscrições foram apagadas.")
        else:
            st.info("ℹ️ Nenhuma inscrição encontrada.")

    # Download ZIP dos dorsais
    if st.button("⬇️ Download dos dorsais (ZIP)"):
        zip_path = os.path.join(tempfile.gettempdir(), "dorsais.zip")
        with zipfile.ZipFile(zip_path, "w") as zipf:
            for _, row in inscritos.iterrows():
                qr_path = row["QR"]
                if os.path.exists(qr_path):
                    filename = f"{row['Processo']}_{row['Escalão']}_{row['Género']}.png"
                    zipf.write(qr_path, arcname=filename)
        with open(zip_path, "rb") as f:
            st.download_button("📦 Clique para descarregar", f.read(), file_name="dorsais.zip")

# --- Menu: Chegadas ---
elif menu == "Chegadas":
    st.subheader("🏁 Registo de Chegadas")
    inscritos = load_inscricoes()

    params = st.experimental_get_query_params()
    chegada = params.get("chegada", [None])[0]

    if chegada:
        try:
            processo = str(int(chegada))
            aluno = inscritos[inscritos["Processo"] == processo]
            if aluno.empty:
                st.error("❌ Número de processo não encontrado.")
            else:
                nome = aluno.iloc[0]["Nome"]
                if aluno.iloc[0]["Classificação"] != "":
                    pos = aluno.iloc[0]["Classificação"]
                    hora = aluno.iloc[0]["Hora"]
                    st.warning(f"⚠️ {nome} já foi registado: {pos}º lugar às {hora}.")
                else:
                    posicao = inscritos[inscritos["Classificação"] != ""].shape[0] + 1
                    hora_agora = datetime.now().strftime("%H:%M:%S")
                    inscritos.loc[inscritos["Processo"] == processo, "Classificação"] = str(posicao)
                    inscritos.loc[inscritos["Processo"] == processo, "Hora"] = hora_agora
                    inscritos.to_csv(DATA_FILE, index=False)
                    st.success(f"🏁 {nome} classificado em {posicao}º lugar!")
                    st.info(f"⏱ Hora de chegada: {hora_agora}")
        except ValueError:
            st.error("⚠️ Parâmetro inválido.")

    st.subheader("📊 Classificação por Escalão e Género")
    esc = st.selectbox("Escolher escalão", sorted(inscritos["Escalão"].unique()))
    sex = st.selectbox("Escolher género", sorted(inscritos["Género"].unique()))
    classificados = inscritos[
        (inscritos["Classificação"] != "") &
        (inscritos["Escalão"] == esc) &
        (inscritos["Género"] == sex)
    ].copy()
    if not classificados.empty:
        classificados["Classificação"] = classificados["Classificação"].astype(int)
        classificados = classificados.sort_values("Classificação")
    st.dataframe(classificados.drop(columns=["QR", "Tempo"], errors="ignore"))

# --- Menu: Classificações ---
elif menu == "Classificações":
    if not acesso_admin:
        st.warning("🔒 Apenas disponível para administradores.")
        st.stop()
    st.subheader("🏁 Classificações por Escalão e Género")
    inscritos = load_inscricoes()
    esc = st.selectbox("Escolher escalão", sorted(inscritos["Escalão"].unique()))
    filtro = inscritos[inscritos["Escalão"] == esc]
    st.write(f"Inscritos no escalão {esc}:")
    st.dataframe(filtro)