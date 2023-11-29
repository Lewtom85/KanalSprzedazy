import os
import datetime as dt
import pandas as pd
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import tab1
import tab2

class DB:
    def __init__(self):
        self.transactions = self.transation_init()
        self.cc = pd.read_csv(os.path.join('db', 'country_codes.csv'), index_col=0)
        self.customers = pd.read_csv(os.path.join('db', 'customers.csv'), index_col=0)
        self.prod_info = pd.read_csv(os.path.join('db', 'prod_cat_info.csv'))
        self.merged = None

    @staticmethod
    def transation_init():
        transactions = pd.DataFrame()
        src = os.path.join('db', 'transactions')
        for filename in os.listdir(src):
            transactions = transactions._append(pd.read_csv(os.path.join(src, filename), index_col=0))

        def convert_dates(x):
            try:
                return dt.datetime.strptime(x, '%d-%m-%Y')
            except ValueError:
                return dt.datetime.strptime(x, '%d/%m/%Y')  # Obsługa błędów parsowania daty

        transactions['tran_date'] = transactions['tran_date'].apply(lambda x: convert_dates(x))
        return transactions

    def merge(self):
        df = self.transactions.join(self.prod_info.drop_duplicates(subset=['prod_cat_code'])
            .set_index('prod_cat_code')['prod_cat'], on='prod_cat_code', how='left')

        df = df.join(self.prod_info.drop_duplicates(subset=['prod_sub_cat_code']).set_index('prod_sub_cat_code')['prod_subcat'], on='prod_subcat_code', how='left', rsuffix='_prod_info')

        df = df.join(self.customers.join(self.cc, on='country_code').set_index('customer_Id'), on='cust_id')

        self.merged = df

df = DB()
df.merge()

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div([
    html.Div([
        dcc.Tabs(id='tabs', value='tab-1', children=[
            dcc.Tab(label='Sprzedaż globalna', value='tab-1'),
            dcc.Tab(label='Produkty', value='tab-2')
        ]),
        html.Div(id='tabs-content')
    ], style={'width': '80%', 'margin': 'auto'})
], style={'height': '100%'})

@app.callback(Output('tabs-content', 'children'), [Input('tabs', 'value')])
def render_content(tab):
    if tab == 'tab-1':
        return tab1.render_tab(df.merged)
    elif tab == 'tab-2':
        return tab2.render_tab(df.merged)

# 1
grouped = df.merged.groupby([df.merged['tran_date'].dt.day_name(), 'Store_type']).count().reset_index()
weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
grouped.tran_date = pd.Categorical(grouped.tran_date, categories=weekdays)
grouped = grouped.sort_values('tran_date')

data = px.bar(grouped, x="tran_date", y="total_amt", color="Store_type", barmode="group",
              color_discrete_map={"Flagship store": "MediumSlateBlue", "e-Shop": "LightBlue", "TeleShop": "LightGray", "MBR": "MediumPurple"},
              labels={"tran_date": "Dzień tygodnia", "total_amt": "Sprzedaż", "Store_type": "Kanał sprzedaży"},
              title="Sprzedaż w poszczególnych dniach tygodnia z podziałem na kanały sprzedaży")

data.update_yaxes(tickprefix="$", showgrid=True)
data.update_layout(
    font_family="Arial",
    legend=dict(title=None, orientation="h", y=1, yanchor="bottom", x=0.5, xanchor="center")
)

fig = go.Figure(data=data, layout=go.Layout(title='Sprzedaż w poszczególnych dniach tygodnia z podziałem na kanały sprzedaży'))

# 2
df.merged['DOB'] = pd.to_datetime(df.merged['DOB'])
df.merged['Age'] = round((df.merged['tran_date'] - df.merged['DOB']) / np.timedelta64(1, 'Y'))
age_by_store = df.merged[['Store_type', 'Age']].groupby('Store_type').value_counts().to_frame().reset_index()

data1 = px.histogram(data_frame=age_by_store, x='Age', y=0, color='Store_type', nbins=20,
                     color_discrete_map={"Flagship store": "MediumSlateBlue", "e-Shop": "LightBlue", "TeleShop": "LightGray", "MBR": "MediumPurple"},
                     labels={"Age": "Wiek klientów", "Store_type": "Kanał sprzedaży", "0": "Ilość klientów"},
                     title="Wiek klientów w poszczególnych kanałach sprzedaży")

data1.update_yaxes(title='Ilość klientów')
data1.update_layout(
    font_family="Arial",
    legend=dict(title=None, orientation="h", y=1, yanchor="bottom", x=0.5, xanchor="center")
)

fig1 = go.Figure(data=data1, layout=go.Layout(title='Wiek klientów w poszczególnych kanałach sprzedaży'))

app.layout = html.Div(children=[
    html.H1('Kanały sprzedaży', style={'text-align': 'center'}),
    html.Div([html.Div([dcc.Graph(id='first', figure=fig)], style={'width': '50%'}),
              html.Div([dcc.Graph(id='second', figure=fig1)], style={'width': '50%'})], style={'display': 'flex'})
])

if __name__ == '__main__':
    app.run_server(debug=True)


