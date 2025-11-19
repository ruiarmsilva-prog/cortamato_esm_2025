import streamlit as st
import pandas as pd
import qrcode
from io import BytesIO
from datetime import datetime
import os
from PIL import Image, ImageDraw, ImageFont
import zipfile
import tempfile
import supabase
from supabase import create_client, Client

st.set_page_config(page_title="Corta-Mato ESM", layout="wide")

# --- Supabase setup ---
SUPABASE_URL = "https://xxxxxx.supabase.co"  # substitui com a tua URL
SUPABASE_KEY = "eyJhbGciOiJI..."  # substitui com a tua anon key
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

DORSAL_DIR = "data/dorsais"

# --- Função para gerar dorsal A6 com QR e dados ---
def gerar_dorsal_a6(nome, processo, escalao, turma):
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
    linha1_y = bottom_y + 40
    linha2_y = bottom_y + 250
    linha3_y = bottom_y + 350
    linha4_y = bottom_y + 450
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

# --- Função de autenticação ---
def autenticar():
    senha = st.sidebar.text_input("🔒 Palavra-passe (admin)", type="password")
    if senha == "admin123":
        return True
    elif senha:
        st.sidebar.warning("Senha incorreta.")
    return False

acesso_admin = autenticar()

# --- Menu lateral ---
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
    df["genero"] = df_raw.iloc[:, 2].astype(str).str.strip()
    df["data_nasc"] = pd.to_datetime(df_raw.iloc[:, 3], errors="coerce")
    df["CC"] = df_raw.iloc[:, 4].astype(str).str.strip()
    df["turma"] = df_raw.iloc[:, 5].astype(str).str.strip()
    df = df[df["processo"].notnull()]
    df["processo"] = df["processo"].astype("Int64")
    return df

def get_escalao(data_nasc):
    if isinstance(data_nasc, str):
        data_nasc = datetime.strptime(data_nasc, "%Y-%m-%d")
    if datetime(2015,1,1) <= data_nasc <= datetime(2017,12,31):
        return "Infantil A"
    elif datetime(2013,1,1) <= data_nasc <= datetime(2014,12,31):
        return "Infantil B"
    elif datetime(2011,1,1) <= data_nasc <= datetime(2012,12,31):
        return "Iniciado"
    elif datetime(2008,1,1) <= data_nasc <= datetime(2010,12,31):
        return "Juvenil"
    elif datetime(2004,1,1) <= data_nasc <= datetime(2007,12,31):
        return "Júnior"
    else:
        return "Fora de escalão"

df = load_data()

# --- Funções Supabase ---
def load_inscricoes():
    result = supabase.table("inscricoes").select("*").execute()
    data = result.data
    if data:
        df = pd.DataFrame(data)
    else:
        df = pd.DataFrame(columns=["processo","nome","data_nasc","genero","turma","escalao","classificacao","hora","qr_url"])
    return df

def insert_inscricao(dados_aluno, escalao, qr_path):
    supabase.table("inscricoes").insert({
        "processo": dados_aluno["processo"],
        "nome": dados_aluno["nome"],
        "data_nasc": dados_aluno["data_nasc"].strftime("%Y-%m-%d"),
        "genero": dados_aluno["genero"],
        "turma": dados_aluno["turma"],
        "escalao": escalao,
        "classificacao": None,
        "hora": None,
        "qr_url": qr_path
    }).execute()

def update_chegada(processo, classificacao, hora):
    supabase.table("inscricoes").update({
        "classificacao": classificacao,
        "hora": hora
    }).eq("processo", processo).execute()

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
                escalao = get_escalao(dados["data_nasc"])
                with st.expander("📋 Dados do aluno"):
                    st.markdown(f"**Nome:** {dados['nome']}")
                    st.markdown(f"**Data de nascimento:** {dados['data_nasc'].strftime('%d-%m-%Y')}")
                    st.markdown(f"**CC:** {dados['CC']}")
                    st.markdown(f"**Turma:** {dados['turma']}")
                    st.markdown(f"**Género:** {dados['genero']}")
                    st.markdown(f"**Escalão:** {escalao}")

                inscritos = load_inscricoes()
                if str(processo) in inscritos["processo"].astype(str).values:
                    st.warning("⚠️ Este aluno já está inscrito.")
                else:
                    if st.button("✅ Confirmar inscrição"):
                        dorsal_img = gerar_dorsal_a6(dados["nome"], processo, escalao, dados["turma"])
                        os.makedirs(DORSAL_DIR, exist_ok=True)
                        qr_path = f"{DORSAL_DIR}/{processo}_{escalao}_{dados['genero']}.png"
                        with open(qr_path, "wb") as f:
                            f.write(dorsal_img)

                        insert_inscricao(dados, escalao, qr_path)
                        st.success(f"✅ {dados['nome']} inscrito com sucesso!")
                        st.image(dorsal_img, width=300)
        except ValueError:
            st.error("⚠️ Parâmetro inválido.")

# --- Menu: Chegadas ---
elif menu == "Chegadas":
    st.subheader("🏁 Registo de Chegadas")
    inscritos = load_inscricoes()
    params = st.experimental_get_query_params()
    chegada = params.get("chegada", [None])[0]

    if chegada:
        try:
            processo = str(int(chegada))
            aluno = inscritos[inscritos["processo"].astype(str) == processo]
            if aluno.empty:
                st.error("❌ Número de processo não encontrado.")
            else:
                nome = aluno.iloc[0]["nome"]
                if aluno.iloc[0]["classificacao"]:
                    st.warning(f"⚠️ {nome} já foi registado: {aluno.iloc[0]['classificacao']}º lugar às {aluno.iloc[0]['hora']}.")
                else:
                    posicao = inscritos[inscritos["classificacao"].notnull()].shape[0] + 1
                    hora_agora = datetime.now().strftime("%H:%M:%S")
                    update_chegada(processo, posicao, hora_agora)
                    st.success(f"🏁 {nome} classificado em {posicao}º lugar!")
                    st.info(f"⏱ Hora de chegada: {hora_agora}")
        except ValueError:
            st.error("⚠️ Parâmetro inválido.")