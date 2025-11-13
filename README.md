import streamlit as st
import pandas as pd
import qrcode
from io import BytesIO
from datetime import datetime

st.set_page_config(page_title="Corta-Mato ESM", layout="wide")

DATA_FILE = "data/inscricoes.csv"

# --- Função para carregar dados ---
def load_data():
    try:
        return pd.read_csv(DATA_FILE)
    except FileNotFoundError:
        return pd.DataFrame(columns=["Nome", "Data de Nascimento", "Género", "Escalão", "Número", "QR"])

# --- Função para determinar escalão ---
def get_escalão(data_nascimento):
    dn = datetime.strptime(data_nascimento, "%Y-%m-%d")
    if datetime(2015,1,1) <= dn <= datetime(2017,12,31):
        return "Infantil A"
    elif datetime(2013,1,1) <= dn <= datetime(2014,12,31):
        return "Infantil B"
    elif datetime(2011,1,1) <= dn <= datetime(2012,12,31):
        return "Iniciado"
    elif datetime(2008,1,1) <= dn <= datetime(2010,12,31):
        return "Juvenil"
    elif datetime(2004,1,1) <= dn <= datetime(2007,12,31):
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
        data_nasc = st.date_input("Data de nascimento")
        genero = st.selectbox("Género", ["Masculino", "Feminino"])
        submeter = st.form_submit_button("Inscrever")

    if submeter:
        escalão = get_escalão(data_nasc.strftime("%Y-%m-%d"))
        numero = len(df) + 1
        qr_img = gerar_qr(numero, nome)

        # Guarda QR como ficheiro
        qr_path = f"data/dorsais/{numero}.png"
        with open(qr_path, "wb") as f:
            f.write(qr_img)

        novo = pd.DataFrame([[nome, data_nasc, genero, escalão, numero, qr_path]],
                            columns=df.columns)
        df = pd.concat([df, novo], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)
        st.success(f"✅ {nome} inscrito com sucesso! (Nº {numero}, {escalão})")
        st.image(qr_img, width=150)

elif menu == "Lista de Inscritos":
    st.subheader("📋 Lista de Inscrições")
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
