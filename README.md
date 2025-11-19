# Corta-Mato ESM

Aplicação web para gestão de inscrições, geração de dorsais com QR Code e registo de chegadas para eventos de Corta-Mato na Escola Secundária ESM.

---

## Funcionalidades

A aplicação permite:

1. **Nova Inscrição**
   - Pesquisa alunos na base de dados Excel (`ListagemAlunos_25_26.xlsx`).
   - Criação de inscrição com geração automática de dorsal A6 com QR Code.
   - Detecção e divisão automática de nomes longos em duas linhas.
   - Armazenamento da inscrição em CSV (`data/inscricoes.csv`).

2. **Lista de Inscritos**
   - Visualização da lista de inscritos.
   - Pesquisa por número de processo.
   - Download da lista em CSV.
   - Impressão do dorsal do aluno.

3. **Lista de Inscritos (admin)**
   - Todas as funcionalidades da lista de inscritos.
   - Eliminação de inscrições individuais ou todas de uma vez.
   - Download de todos os dorsais em formato ZIP.

4. **Registo de Chegadas**
   - Atualização automática da classificação e hora de chegada via QR Code.
   - Visualização de classificações por escalão e género.

5. **Classificações (admin)**
   - Visualização de classificações detalhadas filtradas por escalão.
   - Apenas disponível para administradores.

---

## Pré-requisitos

- Python 3.9 ou superior
- Bibliotecas Python:
  - `streamlit`
  - `pandas`
  - `qrcode`
  - `Pillow`
- Excel com lista de alunos: `ListagemAlunos_25_26.xlsx`
