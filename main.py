import requests
import pandas as pd
from datetime import date, timedelta
from typing import List
from fastapi import FastAPI, Query

app = FastAPI()

n_denoms = 14


@app.get("/")
async def root():
    return {"message": "I'm alive!"}


@app.get("/totals")
async def totals(
    pix: bool = Query(
        default=False,
        description="Boolean to indicate if pix values should be included",
    ),
    denoms: List[str] = Query(
        default=[],
        description="List of denominations to be included in the totals",
    ),
    rolling: int = Query(
        default=0,
        description="Number of days to apply the rolling mean. If none is provided, it is not applied",
    ),
    startDate: str = Query(
        default="",
        description="Fist date to consider. If none is provided, it is assumed to be today",
    ),
    endDate: str = Query(
        default="",
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
    # print('params', 'top', top, 'skip', skip, 'asc?', (sort == 'asc'))

    """
    Cash base (bcb.gov.br)
    """
    cash_response = requests.get(
        f"https://olinda.bcb.gov.br/olinda/servico/mecir_dinheiro_em_circulacao/versao/v1/odata/informacoes_diarias?$top={n_denoms*top}&$format=json&$orderby=Data%20desc"
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
