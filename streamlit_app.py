import streamlit as st
import pandas as pd
import qrcode
from io import BytesIO
from datetime import datetime, date
import os

st.set_page_config(page_title="Corta-Mato ESM", layout="wide")

DATA_FILE = "data/inscricoes.csv"
DORSAL_DIR = "data/dorsais"

# --- Função para carregar dados ---
@st.cache_data
def load_data():
    df_raw = pd.read_excel("ListagemAlunos_25_26.xlsx", sheet_name=0, header=0)

    # Extrair colunas por índice
    df = pd.DataFrame()
    df["processo"] = pd.to_numeric(df_raw.iloc[:, 0], errors="coerce")
    df["nome"] = df_raw.iloc[:, 1].astype(str).str.strip()
    df["género"] = df_raw.iloc[:, 2].astype(str).str.strip()
    df["data_nascimento"] = pd.to_datetime(df_raw.iloc[:, 3], errors="coerce")
    df["turma"] = df_raw.iloc[:, 5].astype(str).str.strip()

    # Remover registos inválidos
    df = df[df["processo"].notnull()]
    df["processo"] = df["processo"].astype("Int64")

    return df


# --- Função para determinar escalão ---
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

# --- Função para gerar QR Code ---
def gerar_qr(numero, nome):
    qr = qrcode.make(f"Corta-Mato ESM | Nº {numero} | {nome}")
    buf = BytesIO()
    qr.save(buf, format="PNG")
    return buf.getvalue()

# --- Interface ---
st.title("🏃‍♂️ Corta-Mato ESM — Sistema de Inscrições")

menu = st.sidebar.radio("Menu", ["Nova Inscrição", "Lista de Inscritos", "Classificações"])

df = load_data()

if menu == "Nova Inscrição":
    st.subheader("🆕 Nova Inscrição")

    processo_input = st.text_input("Número de processo do aluno")
    aluno_base = None

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
                    st.markdown(f"**Turma:** {dados['turma']}")
                    st.markdown(f"**Género:** {dados['género']}")
                    st.markdown(f"**Escalão:** {escalão}")

                inscricoes = pd.read_csv(DATA_FILE) if os.path.exists(DATA_FILE) else pd.DataFrame(columns=[
                    "Processo", "Nome", "Data nascimento", "Género", "Turma", "Escalão", "Tempo", "QR"
                ])

                if processo in inscricoes["Processo"].values:
                    st.warning("⚠️ Este aluno já está inscrito.")
                else:
                    if st.button("✅ Confirmar inscrição"):
                        qr_img = gerar_qr(processo, dados["nome"])
                        os.makedirs(DORSAL_DIR, exist_ok=True)
                        qr_path = f"{DORSAL_DIR}/{processo}.png"
                        with open(qr_path, "wb") as f:
                            f.write(qr_img)

                        novo = pd.DataFrame([[processo, dados["nome"], dados["data_nascimento"], dados["género"],
                                              dados["turma"], escalão, "", qr_path]],
                                            columns=inscricoes.columns)
                        inscricoes = pd.concat([inscricoes, novo], ignore_index=True)
                        inscricoes.to_csv(DATA_FILE, index=False)
                        st.success(f"✅ {dados['nome']} inscrito com sucesso!")
                        st.image(qr_img, width=150)
        except ValueError:
            st.error("⚠️ Introduz um número de processo válido.")

elif menu == "Lista de Inscritos":
    st.subheader("📋 Lista de Inscrições")

    processo = st.text_input("🔍 Pesquisar por número de processo")
    if processo:
        try:
            processo = int(processo)
            aluno = df[df["Processo"] == processo]
            if not aluno.empty:
                dados = aluno.iloc[0]
                st.success(f"✅ Aluno encontrado: {dados['Nome']}")
                st.write(f"📅 Data de nascimento: {dados['Data nascimento'].strftime('%d-%m-%Y')}")
                st.write(f"🏫 Turma: {dados['Turma']}")
                st.write(f"🎽 Escalão: {dados['Escalão']}")
                st.write(f"👤 Sexo: {dados['Género']}")

                if st.button("🖨️ Imprimir Dorsal"):
                    st.image(dados["QR"], caption=f"Dorsal de {dados['Nome']}", width=200)

                if st.button("❌ Eliminar inscrição"):
                    df = df[df["Processo"] != processo]
                    df.to_csv(DATA_FILE, index=False)
                    st.warning(f"Inscrição de {dados['Nome']} eliminada.")
            else:
                st.error("❌ Processo não encontrado.")
        except ValueError:
            st.error("⚠️ Introduz um número de processo válido.")

    st.dataframe(df)
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("⬇️ Exportar CSV", csv, "inscricoes.csv", "text/csv")

elif menu == "Classificações":
    st.subheader("🏁 Classificações por Escalão e Género")

    if "Tempo" not in df.columns:
        df["Tempo"] = ""

    op = st.selectbox("Escolher escalão", sorted(df["Escalão"].unique()))
    filtro = df[df["Escalão"] == op]
    st.write(f"Inscritos no escalão {op}:")
    st.dataframe(filtro)

    nome = st.selectbox("Adicionar tempo a:", filtro["Nome"])
    tempo = st.text_input("Tempo (ex: 00:12:45)")
    if st.button("Registar tempo"):
        df.loc[df["Nome"] == nome, "Tempo"] = tempo
        df.to_csv(DATA_FILE, index=False)
        st.success(f"Tempo registado para {nome}: {tempo}")