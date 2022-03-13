#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# =============================================================================
# To run app, open terminal in folder containing main.py
# and run:
#     bokeh serve --show main.py
# =============================================================================

import yfinance as yf
import pandas as pd

from bokeh.layouts import column, row
from bokeh.models import HoverTool, CrosshairTool, Spinner
from bokeh.plotting import ColumnDataSource, figure
from bokeh.models import Panel, Tabs, DatePicker, Select
from bokeh.palettes import d3
from bokeh.io import curdoc

from datetime import date, timedelta

ticker_symbols = {
    'DJI': '^DJI',
    'S&P 500': '^GSPC'
}


def yf_fund(ticker, start_date, end_date, principal):
    ticker_label = ticker
    ticker = ticker_symbols[ticker]
    yf_fund_ticker = yf.Ticker(ticker)
    end_date += timedelta(1)
    end_date = str(end_date)
    start_date = str(start_date)

    df_yf_fund = pd.DataFrame()
    df_yf_fund = yf_fund_ticker.history(start=start_date, end=end_date)
    df_yf_fund = df_yf_fund.groupby(df_yf_fund.index).first() #drops duplicates dates from after hours trading

    yf_fund_cost_basis = df_yf_fund.iloc[0, 0]
    no_shares = principal/yf_fund_cost_basis

    df_yf_fund['Position'] = df_yf_fund.Close * no_shares
    df_yf_fund['legend'] = ticker_label
    df_yf_fund.columns = [f'Index {i}' for i in df_yf_fund.columns]

    return df_yf_fund, yf_fund_cost_basis


def managed_fund(principal, current_value, df_yf_fund):
    start_date = df_yf_fund.index[0]
    end_date = df_yf_fund.index[-1]
    period = (end_date - start_date).days
    period_years = period/365
    rate = ((current_value/principal)**(1/period_years)) - 1

    df_managed_fund = pd.DataFrame()
    df_managed_fund['Date'] = [(start_date + timedelta(i))
                               for i in range(period + 1)]
    df_managed_fund.Date = pd.to_datetime(df_managed_fund.Date)
    df_managed_fund['Position'] = [principal *
                                   (1 + rate) ** (i/365) for i in range(period + 1)]
    df_managed_fund = df_managed_fund[df_managed_fund.Date.isin(
        df_yf_fund.index.values)]
    df_managed_fund = df_managed_fund.set_index('Date')
    df_managed_fund['legend'] = 'Managed Fund'
    df_managed_fund.columns = [f'Managed {i}' for i in df_managed_fund.columns]

    return df_managed_fund, rate


def create_source(df_fund1, df_fund2):
    df_source = pd.DataFrame()
    df_fund1.index = pd.to_datetime(df_fund1.index)
    df_fund2.index = pd.to_datetime(df_fund2.index)

    df_source = df_fund1.join(df_fund2, how='inner')
    df_source['Difference'] = df_fund1['Managed Position'] - \
        df_fund2['Index Position']

    return df_source


def make_plot(df_source, title):
    source = ColumnDataSource(df_source)
    TOOLTIPS = [
        ('Date', '@Date{%Y-%m-%d}'),  # '@Date{%F}'),
        ('Managed Fund', '@{Managed Position}{$0,0}'),
        ('Index', '@{Index Position}{$0,0}'),
        ('Difference', '@Difference{$0,0}'),
    ]

    plot = figure(width_policy='fit', height_policy='fit',
                  x_axis_type='datetime', title=title)
    plot.line('Date', 'Managed Position', source=source,
              legend_field='Managed legend', color=d3['Category10'][10][0], line_width=3)
    plot.line('Date', 'Index Position', source=source,
              legend_field='Index legend', color=d3['Category10'][10][1], line_width=3)
    plot.add_tools(CrosshairTool())
    plot.add_tools(HoverTool(tooltips=TOOLTIPS,
                   formatters={'@Date': 'datetime'}))
    plot.legend.location = 'top_left'
    plot.legend.click_policy = 'hide'
    plot.xaxis.axis_label = 'Date'
    plot.yaxis.axis_label = 'USD ($)'

    return plot, source


def update(attr, old, new):
    start_date = pd.to_datetime(start_date_picker.value).date()
    end_date = pd.to_datetime(end_date_picker.value).date()
    principal = principal_spinner.value
    current_value = current_value_spinner.value
    ticker = ticker_symbols[fund_2.value]
    min_date = yf.Ticker(ticker).history(period='max').index[0].date()
    start_date_picker.min_date = min_date

    df_fund_2, index_cost_basis = yf_fund(
        fund_2.value, start_date, end_date, principal)
    df_fund_1, rate = managed_fund(principal, current_value, df_fund_2)
    df_source = create_source(df_fund_1, df_fund_2)

    new_source = ColumnDataSource(df_source)
    source.data.update(new_source.data)

# WIDGETS


principal = 1000.0
current_value = 3000.0
ticker = 'S&P 500'
start_date = date(2016, 5, 3)
end_date = date(2021, 5, 7)
min_date = yf.Ticker(ticker_symbols[ticker]).history(
    period='max').index[0].date()
max_date = yf.Ticker(ticker_symbols[ticker]).history(
    period='max').index[-1].date()

#     fund_1 is mananged fund
fund_2 = Select(title='Index', value='S&P 500', options=['DJI', 'S&P 500'])

start_date_picker = DatePicker(title='Start Date', value=start_date, min_date=min_date,
                               max_date=max_date)
end_date_picker = DatePicker(title='End Date', value=end_date, min_date=min_date,
                             max_date=max_date)
principal_spinner = Spinner(value=principal, step=1, title='Principal')
current_value_spinner = Spinner(
    value=current_value, step=1, title='Current Value')

# Tab 1
# Data

df_fund_2, index_cost_basis = yf_fund(
    fund_2.value, start_date, end_date, principal)
df_fund_1, rate = managed_fund(principal, current_value, df_fund_2)
df_source = create_source(df_fund_1, df_fund_2)

# Set-up Plots

plot1, source = make_plot(df_source, 'Managed Fund vs. Index')

# Layout
inputs = column(principal_spinner, current_value_spinner,
                fund_2, start_date_picker, end_date_picker)
row1 = row(plot1, inputs)
tab_managed = Panel(child=row1, title='Managed Fund vs Index')

layout = Tabs(tabs=[tab_managed])

start_date_picker.on_change('value', update)
end_date_picker.on_change('value', update)
principal_spinner.on_change('value', update)
current_value_spinner.on_change('value', update)
fund_2.on_change('value', update)

curdoc().add_root(layout)
