# Importações
from urllib.request import urlopen
import os
import json
import pandas as pd
from datetime import date, timedelta
import streamlit as st

# CSS Injection para alterar a cor de fundo do warning
st.markdown("""
<style>
.st-emotion-cache-1warn {
   background-color=#FFC7CE;
   color=#9C0006
}
</style>
""", unsafe_allow_html=True)

# Título da página
st.title('Proposições - Câmara dos Deputados')

st.write('Este projeto busca permitir a visualização de dados sobre proposições legislativas apresentadas à Câmara dos Deputados. Para tanto, são utilizadas as seguintes variáveis: (i) data de apresentação; (ii) tipo de proposição; e (iii) o Partido Político do autor da proposição.')

# Filtro inicial: ano de busca
st.write('Em benefício da eficiência na execução do código, a definição do período de apresentação é realizada em duas etapas. Primeiro, deve-se definir o ano de apresentação da proposição:')
years = ['2001', '2002', '2003', '2004', '2005', '2006', '2007', '2008', '2009', '2010', '2011', '2012', '2013', '2014', '2015', '2016', '2017', '2018', '2019', '2020', '2021', '2022', '2023', '2024', '2025']
anoBusca = st.select_slider(
   "Selecione o ano de busca:",
   years,
   value='2018'
)

# Com base no ano selecionado, fazemos uma requisição para download dos respectivos dados
st.write("Com base no ano selecionado, é feita uma requisição HTTP para download dos respectivos dados.")

with st.spinner('Realizando download dos dados...'):
  file = f"proposicoes-{anoBusca}.xlsx"
  url = f"http://dadosabertos.camara.leg.br/arquivos/proposicoes/xlsx/{file}"
  save_folder = './downloads'
  os.makedirs(save_folder, exist_ok=True)
  save_path = os.path.join(save_folder, file)

  res = urlopen(url)
  data = res.read()

  with open(save_path, 'wb') as f:
      f.write(data)

# Após o download, importamos a base de dados para o contexto do código
with st.spinner('Carregando a base de dados...'):
    df_proposicoes = pd.read_excel(f"./downloads/{file}")
    df_proposicoes = df_proposicoes[df_proposicoes['descricaoTipo'].str.contains('Projeto de Lei|Proposta de Emenda à Constituição')]

# Formatação da coluna "dataApresentacao", que antes também incluía horários (agora, apenas a data)
with st.spinner('Formatando e consolidando as informações encontradas...'):
    df_proposicoes['dataApresentacao'] = pd.to_datetime(df_proposicoes['dataApresentacao']).dt.date

# No ano selecionado no filtro inicial, o usuário seleciona o marco inical de um período de 30 dias
st.write('A segunda etapa do filtro temporal envolve a especificação do marco inicial do período de 30 (trinta) dias que será analisado:')
dataInicio = st.date_input(
        "Selecione a data inicial da busca:",
        value = date(int(anoBusca), 3, 1), # Devido ao recesso do Poder Legislativo, por padrão, colocamos a dataInicio em março
        min_value = date(int(anoBusca), 1, 1),
        max_value = date(int(anoBusca), 12, 1)
    )

dataFim = dataInicio + timedelta(days=30) # Período de 30 dias

st.write(f"Desse modo, foi definido o seguinte período de busca: {dataInicio} - {dataFim}")

# Aplicando o novo filtro
with st.spinner('Filtrando informações com base no período selecionado...'):
    df_proposicoesPeriodo = df_proposicoes[(df_proposicoes['dataApresentacao'] >= dataInicio) & (df_proposicoes['dataApresentacao'] <= dataFim)]

# Implementando a verificação da existência de proposições para o período selecionado
if df_proposicoesPeriodo.empty == True:
   st.warning('Não foram encontradas proposições para os filtros selecionados! Isso pode ocorrer, por exemplo, quando o período pesquisado coincide com o recesso parlamentar, que se inicia no dia 23 de dezembro de cada ano e se encerra no dia 02 de fevereiro do ano seguinte. Por favor, tente alterar o marco inicial da pesquisa.', icon="⚠️")
else:
   # Construindo a visualização dos gráficos
   st.write('Com base nos filtros selecionados, é possível consolidar as seguintes informações:')
   
   # Gráfico 1: Proposições por Semana
   st.subheader('1. Quantidade de proposições apresentadas a cada semana')
   
   df_plot = df_proposicoesPeriodo.copy()
   
   df_plot['dataApresentacao'] = pd.to_datetime(df_plot['dataApresentacao'])
   df_temp = df_plot.set_index('dataApresentacao')
   df_proposicoesSemanal = df_temp.resample('1W').size().reset_index(name='quantidade_proposicoes') # Aqui, a contagem é realizada semanalmente
   
   st.write('\n\n') # Pulando duas linhas
   
   # Gráfico de linhas
   st.line_chart(df_proposicoesSemanal, x='dataApresentacao', y='quantidade_proposicoes', x_label='Semana de Apresentação', y_label='Proposições', width='stretch')
   
   # Gráfico 2: Proposições por Tipo (Projeto de Lei, Medida Provisória ou Proposta de Emenda à Constituição)
   st.subheader('2. Quantidade de proposições apresentadas de acordo com o tipo de proposição')
   
   df_tipo = df_plot['descricaoTipo'].value_counts().reset_index()
   df_tipo.columns = ['Tipo de Proposição', 'Quantidade']
   
   st.write('\n\n') # Pulando duas linhas
   
   st.bar_chart(df_tipo, x='Tipo de Proposição', y='Quantidade', x_label='Tipo de Proposição', y_label='Proposições', width='stretch')
   
   # Gráfico 3: Proposição por Partido (em um período de 7 dias)
   with st.spinner('Consolidando informações sobre os partidos políticos dos autores de cada proposição...'):
       dataFinal = dataInicio + timedelta(days=7) # Em benefício do tempo, utilizamos um período mais curto (7 dias)
   
       df_proposicoesPeriodo2 = df_proposicoes[(df_proposicoes['dataApresentacao'] >= dataInicio) & (df_proposicoes['dataApresentacao'] <= dataFinal)]
       
       df_plot2 = df_proposicoesPeriodo2.copy()
       df_plot2['dataApresentacao'] = pd.to_datetime(df_plot2['dataApresentacao'])
   
       res = urlopen('https://dadosabertos.camara.leg.br/api/v2/deputados')
       data = json.loads(res.read().decode('utf-8'))
       df_deputados = pd.DataFrame(data['dados'])
       
       dadosAutores = []
   
       for index, value in df_plot2.iterrows():
           proposicao_id = value['id']
           
           res = urlopen(f"https://dadosabertos.camara.leg.br/api/v2/proposicoes/{proposicao_id}/autores")    
           data = json.loads(res.read().decode('utf-8'))
   
           dadosAutores.append({'proposicao_id': proposicao_id, 'nome': data['dados'][0]['nome']})
           
       df_autores = pd.DataFrame(dadosAutores)
       df_autores = pd.merge(df_autores, df_deputados[['nome', 'siglaPartido', 'siglaUf']], on='nome', how='left')
       df_autores = df_autores[['proposicao_id', 'nome', 'siglaPartido', 'siglaUf']]
       df_autores = df_autores.rename(columns={'proposicao_id': 'proposicaoId'})
   
   st.subheader('3. Quantidade de proposições apresentadas por partido político')
   
   df_partido = df_autores['siglaPartido'].value_counts().reset_index()
   df_partido.columns = ['Partido Político', 'Quantidade']
   
   st.write('\n\n') # Pulando duas linhas
   
   st.bar_chart(df_partido, x='Partido Político', y='Quantidade', x_label='Partido Político', y_label='Proposições', width='stretch')
   
   
   st.write(f"*Nota: em benefício do tempo, utiliza-se um período mais curto (7 dias): {dataInicio} - {dataFinal}*")
   
   




