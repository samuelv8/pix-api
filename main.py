from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from typing import Optional, Literal, List
import requests
import pandas as pd
import matplotlib.pyplot as plt

import seaborn as sns
from numpy import random as rd
from datetime import datetime, date, timedelta

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "I'm alive!"}

@app.get("/totals")
async def totals(
    pix: bool = Query(
        default=False,
        description="Boolean to indicate if pix values should be included",
    ),
    startDate: str = Query(
        default='2017-01-01',
        description="Fist date to consider. If none is provided, it is assumed to be today",
    ),
    endDate: str = Query(
        default='2022-09-15',
        description="Last date to consider. If none is provided, it is assumed to be today",
    ),
    sort: str = Query(
        default="desc",
        description="Sorting order (asc or desc)",
        regex="^(asc)|(desc)$",
    )
):
    """
    Params setup
    """
    start_date = date.fromisoformat(
        startDate) if len(startDate) else date.today()
    final_date = date.fromisoformat(endDate) if len(endDate) else date.today()
    top = (final_date - start_date).days + 1
    skip = max((date.today() - final_date).days, 0)

    """
    Cash base (bcb.gov.br)
    """
    cash_response = requests.get(
        f"https://olinda.bcb.gov.br/olinda/servico/mecir_dinheiro_em_circulacao/versao/v1/odata/informacoes_diarias?$top={14*top}&$format=json&$orderby=Data%20desc"
    )
    # init dataframe
    df_cash = pd.DataFrame(cash_response.json()['value'])
    df_cash.loc[:, "Data"] = pd.to_datetime(df_cash["Data"])
    # group by date with values sum
    df_cash = df_cash.groupby(by="Data").sum()
    # remove unused columns
    df_cash.drop(["Quantidade"], axis=1, inplace=True)
    # rename columns to return
    df_cash.rename(columns={"Valor": "Total Dinheiro"}, inplace=True)
    # set index and sort, filter by date
    df_cash.index = pd.to_datetime(df_cash.index)
    df_cash.sort_index(ascending=(sort == "asc"), inplace=True)
    df_cash = df_cash.loc[start_date:final_date] if sort == "asc" else df_cash.loc[final_date:start_date]

    if pix:
        """
        Pix base (bcb.gov.br)
        """
        pix_response = requests.get(
            f"https://olinda.bcb.gov.br/olinda/servico/SPI/versao/v1/odata/PixLiquidadosAtual?$top={top}&$format=json&$orderby=Data%20desc"
        )
        # init dataframe
        df_pix = pd.DataFrame(pix_response.json()['value'])
        # remove unused columns
        df_pix.drop(["Quantidade", "Media"], axis=1, inplace=True)
        # fix values to base unit
        df_pix.loc[:, "Total"] = df_pix["Total"] * 1000
        # rename columns to return
        df_pix.rename(columns={"Total": "Total Pix"}, inplace=True)
        # set index and sort, filter by date
        df_pix.set_index("Data", inplace=True)
        df_pix.index = pd.to_datetime(df_pix.index)
        df_pix.sort_index(ascending=True, inplace=True)
        df_pix = df_pix[start_date:final_date]
        # join cash dataframe
        df_all = pd.concat([df_pix, df_cash], axis=1, join="outer")
        df_all.sort_index(ascending=(sort == "asc"), inplace=True)
        # remove index and convert dates back to string
        df_all.reset_index(inplace=True)
        df_all.loc[:, "Data"] = df_all["Data"].dt.strftime('%Y-%m-%d')
        df_all.fillna(0, inplace=True)
        # generate values list and return
        all_values = df_all.to_dict('records')
        return {"docs": all_values}

    # remove index and convert dates back to string
    df_cash.reset_index(inplace=True)
    df_cash.loc[:, "Data"] = df_cash["Data"].dt.strftime('%Y-%m-%d')
    # generate values list and return
    cash_values = df_cash.to_dict('records')
    return {"docs": cash_values}
    
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

