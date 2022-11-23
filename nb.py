# imports necessários
import requests
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from numpy import random as rd

"""
Hiperparams
"""

# parâmetros obtenção de dados:
days = 4 * 365
n_denom = 14

# médial móvel para análises gráficas:
mmovel = 30

# utilizado no último gráfico:
n_denom_plot = [0.50, 2.00, 20.00, 50.00, 100.00, 200.00]

"""
Endpoints and params
"""

# retorna série histórica de valores
total_values_endpoint = '/totals'
totals_params = [
    'pix',       # true ou false para incluir valores de pix
    'denoms',    # lista de denominações graficamente consideradas
    # quantidade de dias utilizada para média móvel (para valor nulo por default não é aplicada)
    'rolling',
    'startDate',  # data inicial de análise
    'endDate',   # data finaç de análise
    'sort',      # 'asc' ou 'desc' por data
]

denoms_distr_endpoint = '/denoms'
query_params = dict.fromkeys(totals_params)
query_params['pix'] = True
query_params['denoms'] = []
query_params['rolling'] = 30
query_params['startDate'] = '2017-01-01'
query_params['endDate'] = '2022-09-15'
query_params['sort'] = 'desc'

"""
Principal base
"""
# Consumindo JSON:
pix = requests.get(
    f"https://olinda.bcb.gov.br/olinda/servico/SPI/versao/v1/odata/PixLiquidadosAtual?$top={days}&$format=json&$orderby=Data%20desc")
print(pix.json()['value'][0])
print(pix.json()['value'][-1])

"""
Secondary base
"""
# Consumindo JSON:
dinheiro = requests.get(
    f"https://olinda.bcb.gov.br/olinda/servico/mecir_dinheiro_em_circulacao/versao/v1/odata/informacoes_diarias?$top={n_denom*days}&$format=json&$orderby=Data%20desc")
print(dinheiro.json()['value'][0])
print(dinheiro.json()['value'][-1])

"""
Dataframe
"""
# Cash
df_dinheiro = pd.DataFrame(dinheiro.json()['value'])
df_dinheiro.loc[:, "Data"] = pd.to_datetime(df_dinheiro["Data"])
df_dinheiro.head()

# Agrupando dados por data:
df_dinheiro_v2 = df_dinheiro.groupby(
    by="Data").sum().sort_index(ascending=False)
df_dinheiro_v2.index = pd.to_datetime(df_dinheiro_v2.index)

# teste de integridade
print(
    f"df_dinheiro_v2:\nValor faltante?\nQuantidade: {df_dinheiro_v2.isnull().Quantidade.unique()},", end=" ")
print(f"Valor: {df_dinheiro_v2.isnull().Valor.unique()}")

# Pix
df_pix = pd.DataFrame(pix.json()['value'])
df_pix.set_index("Data", inplace=True)
df_pix.index = pd.to_datetime(df_pix.index)
df_pix.loc[:, "Total"] = df_pix["Total"] * 1000  # convertendo para RS
df_pix.loc[:, "Media"] = df_pix["Media"] * 1000  # convertendo para RS
df_pix.head()

# teste de integridade
print(
    f"df_pix:\nValor faltante?\nQuantidade: {df_pix.isnull().Quantidade.unique()}, Total: {df_pix.isnull().Total.unique()}, Media: {df_pix.isnull().Media.unique()}")

"""
Graphics
"""
# temporal
fig, ax = plt.subplots(2, 1, sharex=True, figsize=(16, 9))
ax[0].plot(df_dinheiro_v2.index, df_dinheiro_v2["Valor"].rolling(
    mmovel).mean(), color="seagreen")
ax[1].plot(df_pix.index, df_pix["Total"].rolling(mmovel).mean(), color="blue")
ax[0].set_title(f"Dinheiro corrente: média móvel de {mmovel} dias")
ax[1].set_title(f"Transações SPI: média móvel de {mmovel} dias")
plt.show()

# barplot
sns.set(rc={'figure.figsize': (16, 9)})
sns.barplot(data=df_dinheiro, x="Denominacao", y="Quantidade")

# temporal series
fig, ax = plt.subplots(len(n_denom_plot), 1, sharex=True, figsize=(16, 9))
for i in range(len(n_denom_plot)):
    ax[i].plot(df_dinheiro[df_dinheiro["Denominacao"] == f"{n_denom_plot[i]:.2f}"]["Data"], df_dinheiro[df_dinheiro["Denominacao"] ==
               f"{n_denom_plot[i]:.2f}"]["Quantidade"].rolling(mmovel).mean(), color=(rd.uniform(0, 0.8), rd.uniform(0, 0.8), rd.uniform(0, 0.8)))
    ax[i].set_ylabel(f"{n_denom_plot[i]:.2f}")
plt.show()
