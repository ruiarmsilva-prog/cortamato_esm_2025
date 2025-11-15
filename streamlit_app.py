import streamlit as st
import pandas as pd
import qrcode
from io import BytesIO
from datetime import datetime, date
import os

st.set_page_config(page_title="Corta-Mato ESM", layout="wide")

DATA_FILE = "data/inscricoes.csv"
DORSAL_DIR = "data/dorsais"

# --- Autenticação simples ---
def autenticar():
    senha = st.sidebar.text_input("🔒 Palavra-passe (admin)", type="password")
    if senha == "admin123":
        return True
    elif senha:
        st.sidebar.warning("Senha incorreta.")
    return False

acesso_admin = autenticar()

# --- Menu condicionado por permissões ---
if acesso_admin:
    menu = st.sidebar.radio("Menu", ["Nova Inscrição", "Lista de Inscritos", "Lista de Inscritos (admin)", "Chegadas", "Classificações"])
else:
    menu = st.sidebar.radio("Menu", ["Nova Inscrição", "Lista de Inscritos"])

# --- Função para carregar dados ---
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
    # QR agora contém o link direto para o site com o parâmetro de chegada
    url = f"https://cortamatoesm.streamlit.app/?chegada={numero}"
    qr = qrcode.make(url)
    buf = BytesIO()
    qr.save(buf, format="PNG")
    return buf.getvalue()


# --- Carregar base de dados de alunos ---
df = load_data()

# --- Menu: Nova Inscrição ---
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
                    st.markdown(f"**CC:** {dados['CC']}")
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

# --- Menu: Lista de Inscritos ---
elif menu == "Lista de Inscritos":
    st.subheader("📋 Lista de Inscrições")
    if os.path.exists(DATA_FILE):
        inscritos = pd.read_csv(DATA_FILE)
    else:
        inscritos = pd.DataFrame(columns=[
            "Processo", "Nome", "Data nascimento", "Género", "Turma", "Escalão", "Tempo", "QR"
        ])

    processo = st.text_input("🔍 Pesquisar por número de processo")
    if processo:
        try:
            processo = int(processo)
            aluno = inscritos[inscritos["Processo"] == processo]
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
                    inscritos = inscritos[inscritos["Processo"] != processo]
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
    if os.path.exists(DATA_FILE):
        inscritos = pd.read_csv(DATA_FILE)
    else:
        inscritos = pd.DataFrame(columns=[
            "Processo", "Nome", "Data nascimento", "Género", "Turma", "Escalão",
        ])

    # 📋 Mostrar tabela
    st.dataframe(inscritos.drop(columns=["Tempo", "QR"], errors="ignore"))
    csv = inscritos.to_csv(index=False).encode('utf-8')
    st.download_button("⬇️ Exportar CSV", csv, "inscricoes.csv", "text/csv")

    # 🔍 Eliminar inscrição por processo
    processo = st.text_input("🔍 Eliminar inscrição por número de processo")
    if processo:
        try:
            processo = int(processo)
            aluno = inscritos[inscritos["Processo"] == processo]
            if not aluno.empty:
                dados = aluno.iloc[0]
                st.success(f"✅ Aluno encontrado: {dados['Nome']}")
                st.write(f"📅 Data de nascimento: {dados['Data nascimento']}")
                st.write(f"🏫 Turma: {dados['Turma']}")
                st.write(f"🎽 Escalão: {dados['Escalão']}")
                st.write(f"👤 Sexo: {dados['Género']}")

                if st.button("❌ Confirmar eliminação"):
                    inscritos = inscritos[inscritos["Processo"] != processo]
                    inscritos.to_csv(DATA_FILE, index=False)
                    st.warning(f"Inscrição de {dados['Nome']} eliminada.")
            else:
                st.error("❌ Processo não encontrado.")
        except ValueError:
            st.error("⚠️ Introduz um número de processo válido.")

    # 🧹 Limpar todas as inscrições
    if st.button("🧹 Apagar todas as inscrições"):
        if os.path.exists(DATA_FILE):
            os.remove(DATA_FILE)
            st.success("✅ Todas as inscrições foram apagadas.")
        else:
            st.info("ℹ️ Nenhuma inscrição encontrada.")

    # ⬇️ Download dos dorsais em ZIP
    if st.button("⬇️ Download dos dorsais (ZIP)"):
        import zipfile
        import tempfile

        zip_path = os.path.join(tempfile.gettempdir(), "dorsais.zip")
        with zipfile.ZipFile(zip_path, "w") as zipf:
            for _, row in inscritos.iterrows():
                qr_path = row["QR"]
                if os.path.exists(qr_path):
                    zipf.write(qr_path, arcname=os.path.basename(qr_path))
        with open(zip_path, "rb") as f:
            st.download_button("📦 Clique para descarregar", f.read(), file_name="dorsais.zip")

# --- Menu: Chegadas (admin only) ---
if menu == "Chegadas":
    if not acesso_admin:
        st.warning("🔒 Esta funcionalidade está disponível apenas para administradores.")
        st.stop()

    st.subheader("🏁 Registo de Chegadas")

    # Carregar inscrições
    if os.path.exists(DATA_FILE):
        inscritos = pd.read_csv(DATA_FILE)
    else:
        st.error("❌ Não há inscrições registadas.")
        st.stop()

    # Ler parâmetro da URL
    params = st.experimental_get_query_params()
    chegada = params.get("chegada", [None])[0]

    if chegada:
        try:
            processo = int(chegada)
            aluno = inscritos[inscritos["Processo"] == processo]
            if aluno.empty:
                st.error("❌ Aluno não encontrado.")
            else:
                if "Classificação" not in inscritos.columns:
                    inscritos["Classificação"] = ""

                if aluno.iloc[0]["Classificação"] != "":
                    st.warning(f"⚠️ {aluno.iloc[0]['Nome']} já foi classificado em {aluno.iloc[0]['Classificação']}º.")
                else:
                    # Próxima posição
                    classificados = inscritos[inscritos["Classificação"] != ""]
                    posicao = len(classificados) + 1
                    inscritos.loc[inscritos["Processo"] == processo, "Classificação"] = posicao
                    inscritos.to_csv(DATA_FILE, index=False)
                    st.success(f"✅ {aluno.iloc[0]['Nome']} classificado em {posicao}º lugar.")
        except ValueError:
            st.error("⚠️ Parâmetro de chegada inválido.")

    # Mostrar tabela de classificados
    if "Classificação" in inscritos.columns:
        classificados = inscritos[inscritos["Classificação"] != ""].sort_values("Classificação")
        st.dataframe(classificados.drop(columns=["QR"], errors="ignore"))

# --- Menu: Classificações (admin only) ---
elif menu == "Classificações":
    if not acesso_admin:
        st.warning("🔒 Esta funcionalidade está disponível apenas para administradores.")
        st.stop()

    st.subheader("🏁 Classificações por Escalão e Género")

    if os.path.exists(DATA_FILE):
        inscritos = pd.read_csv(DATA_FILE)
    else:
        inscritos = pd.DataFrame(columns=[
            "Processo", "Nome", "Data nascimento", "Género", "Turma", "Escalão", 
        ])

    op = st.selectbox("Escolher escalão", sorted(inscritos["Escalão"].unique()))
    filtro = inscritos[inscritos["Escalão"] == op]
    st.write(f"Inscritos no escalão {op}:")
    st.dataframe(filtro)

    nome = st.selectbox("Adicionar tempo a:", filtro["Nome"])
    tempo = st.text_input("Tempo (ex: 00:12:45)")
    if st.button("Registar tempo"):
        inscritos.loc[inscritos["Nome"] == nome, "Tempo"] = tempo
        inscritos.to_csv(DATA_FILE, index=False)
        st.success(f"Tempo registado para {nome}: {tempo}")