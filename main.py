from fastapi import FastAPI
from fastapi.responses import FileResponse
from typing import Optional, Literal
import requests
import pandas as pd
import matplotlib.pyplot as plt

import seaborn as sns
from numpy import random as rd
from datetime import datetime

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "I'm alive!"}

    
@app.put("/graphic")
async def read_denoms(graph_type: Literal['Temporal', 'Barplot', 'Series'], rolling: Optional[int] = 30, 
    startDate: Optional[str] = '2017-01-01', endDate: Optional[str] = '2022-09-15', 
    denoms: Optional[list] = [0.50, 2.00, 20.00, 50.00, 100.00, 200.00]):
    
    """
    Retorna série histórica de valores
    """

    """
    Parâmetros
    """
    totals_params = [
        'denoms',     # lista de denominações graficamente consideradas
        'rolling',    # quantidade de dias utilizada para média móvel (para valor nulo por default não é aplicada)
        'startDate',  # data inicial de análise
        'endDate',    # data finaç de análise
    ]

    query_params = dict.fromkeys(totals_params)
    query_params['denoms'] = denoms
    query_params['rolling'] = rolling
    query_params['startDate'] = startDate
    query_params['endDate'] = endDate

    """
    Parâmetros derivados
    """
    # parâmetros obtenção de dados:
    days = datetime.strptime(endDate, "%Y-%m-%d") - datetime.strptime(startDate, "%Y-%m-%d")
    days = days.days

    n_denom = 14

    """
    Principal base
    """
    # Consumindo JSON:
    pix = requests.get(
        f"https://olinda.bcb.gov.br/olinda/servico/SPI/versao/v1/odata/PixLiquidadosAtual?$top={days}&$format=json&$orderby=Data%20desc")

    """
    Secondary base
    """
    # Consumindo JSON:
    dinheiro = requests.get(
        f"https://olinda.bcb.gov.br/olinda/servico/mecir_dinheiro_em_circulacao/versao/v1/odata/informacoes_diarias?$top={n_denom*days}&$format=json&$orderby=Data%20desc")

    """
    Dataframe
    """
    # Cash
    df_dinheiro = pd.DataFrame(dinheiro.json()['value'])
    df_dinheiro.loc[:, "Data"] = pd.to_datetime(df_dinheiro["Data"])

    # Agrupando dados por data:
    df_dinheiro_v2 = df_dinheiro.groupby(
        by="Data").sum().sort_index(ascending=False)
    df_dinheiro_v2.index = pd.to_datetime(df_dinheiro_v2.index)

    # teste de integridade 1
    print(
        f"df_dinheiro_v2:\nValor faltante?\nQuantidade: {df_dinheiro_v2.isnull().Quantidade.unique()},", end=" ")
    print(f"Valor: {df_dinheiro_v2.isnull().Valor.unique()}")

    # Pix
    df_pix = pd.DataFrame(pix.json()['value'])
    df_pix.set_index("Data", inplace=True)
    df_pix.index = pd.to_datetime(df_pix.index)
    df_pix.loc[:, "Total"] = df_pix["Total"] * 1000  # convertendo para RS
    df_pix.loc[:, "Media"] = df_pix["Media"] * 1000  # convertendo para RS

    # teste de integridade 2
    print(
        f"df_pix:\nValor faltante?\nQuantidade: {df_pix.isnull().Quantidade.unique()}, Total: {df_pix.isnull().Total.unique()}, Media: {df_pix.isnull().Media.unique()}")
    
   

    """
    Graphics
    """
    # temporal
    if(graph_type == "Temporal"):
        fig, ax = plt.subplots(2, 1, sharex=True, figsize=(16, 9))
        ax[0].plot(df_dinheiro_v2.index, df_dinheiro_v2["Valor"].rolling(
            rolling).mean(), color="seagreen")
        ax[1].plot(df_pix.index, df_pix["Total"].rolling(rolling).mean(), color="blue")
        ax[0].set_title(f"Dinheiro corrente: média móvel de {rolling} dias")
        ax[1].set_title(f"Transações SPI: média móvel de {rolling} dias")
        plt.savefig("Temporal.png")

    # barplot
    if(graph_type == "Barplot"):
        fig, ax = plt.subplots(1, 1, sharex=True, figsize=(16, 9))
        sns.set(rc={'figure.figsize': (16, 9)})
        sns.barplot(data=df_dinheiro, x="Denominacao", y="Quantidade")
        plt.savefig("Barplot.png")

    # temporal series
    if(graph_type == "Series"):
        fig, ax = plt.subplots(len(denoms), 1, sharex=True, figsize=(16, 9))
        for i in range(len(denoms)):
            ax[i].plot(df_dinheiro[df_dinheiro["Denominacao"] == f"{denoms[i]:.2f}"]["Data"], df_dinheiro[df_dinheiro["Denominacao"] ==
                    f"{denoms[i]:.2f}"]["Quantidade"].rolling(rolling).mean(), color=(rd.uniform(0, 0.8), rd.uniform(0, 0.8), rd.uniform(0, 0.8)))
            ax[i].set_ylabel(f"{denoms[i]:.2f}")
        plt.savefig("Series.png")

    graphic_path = graph_type + '.png'
    return FileResponse(graphic_path)

