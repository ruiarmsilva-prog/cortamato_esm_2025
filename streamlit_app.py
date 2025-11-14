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
    df = pd.read_excel("ListagemAlunos_25_26.xlsx", sheet_name=0)
    df.columns = df.columns.str.strip()  # remove espaços extras
    st.write("🧾 Colunas encontradas no ficheiro:", df.columns.tolist())
    if "Data nascimento" in df.columns:
        df["Data nascimento"] = pd.to_datetime(df["Data nascimento"], errors="coerce")
    else:
        st.error("❌ A coluna 'Data nascimento' não foi encontrada.")
    df["Processo"] = df["Processo"].astype(int)
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
    with st.form("inscricao_form"):
        nome = st.text_input("Nome do aluno")
        data_nasc = st.date_input("Data de nascimento", value=date(2010,1,1), min_value=date(2004,1,1), max_value=date(2017,12,31))
        genero = st.selectbox("Género", ["Masculino", "Feminino"])
        turma = st.text_input("Turma")
        submeter = st.form_submit_button("Inscrever")

    if submeter:
        escalão = get_escalão(data_nasc)
        numero = df["Processo"].max() + 1 if not df.empty else 1
        qr_img = gerar_qr(numero, nome)

        os.makedirs(DORSAL_DIR, exist_ok=True)
        qr_path = f"{DORSAL_DIR}/{numero}.png"
        with open(qr_path, "wb") as f:
            f.write(qr_img)

        novo = pd.DataFrame([[numero, nome, data_nasc, genero, turma, escalão, "", qr_path]],
                            columns=["Processo", "Nome", "Data nascimento", "Género", "Turma", "Escalão", "Tempo", "QR"])
        df = pd.concat([df, novo], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)
        st.success(f"✅ {nome} inscrito com sucesso! (Nº {numero}, {escalão})")
        st.image(qr_img, width=150)

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