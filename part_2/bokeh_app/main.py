#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Dec  4 14:50:30 2021

@author: katyhagerty
"""

import pandas as pd

import yfinance as yf
import bokeh

from functools import partial

from bokeh.layouts import column, row
from bokeh.models import CustomJS, Slider, HoverTool,CrosshairTool, Div,Paragraph, Spinner, Dropdown 
from bokeh.plotting import ColumnDataSource, figure, output_file, show, curdoc
from bokeh.models import Panel, Tabs, DatePicker, Select, TextInput 
from bokeh.palettes import d3

from datetime import datetime, date, timedelta

from bokeh.io import curdoc

from functools import partial

ticker_symbols = {
    'DJI': '^DJI',
    'S&P 500': '^GSPC'
}

def yf_fund(ticker, start_date, end_date, principal):
    ticker_label = ticker
    
    if ticker in ticker_symbols.keys():
        ticker = ticker_symbols[ticker]
    
    yf_fund_ticker = yf.Ticker(ticker)
    end_date2 = end_date + timedelta(1)
    end_date2 = str(end_date2)
    start_date = str(start_date)
    
    df_yf_fund = pd.DataFrame()
    df_yf_fund = yf_fund_ticker.history(start=start_date, end=end_date2)
    
    yf_fund_cost_basis = df_yf_fund.iloc[0, 3]
    no_shares = principal/yf_fund_cost_basis
    
    df_yf_fund['Position'] = df_yf_fund['Close'] * no_shares            
    df_yf_fund['legend'] = ticker_label            
    df_yf_fund.columns = [f'Stock {i}' for i in df_yf_fund.columns]
            
    return df_yf_fund, yf_fund_cost_basis

def managed_fund(principal, current_value, df_yf_fund):
    df_managed_fund = pd.DataFrame()
    start_date = pd.to_datetime(df_yf_fund.index[0]) 
    end_date = pd.to_datetime(df_yf_fund.index[-1]) 
    period = (end_date - start_date).days
    period_years = period/365.25
    rate = ((current_value/principal)**(1/period_years)) - 1
    
    df_managed_fund = pd.DataFrame()
    df_managed_fund['Date'] = [(start_date + timedelta(i)) for i in range(period + 1)]
    df_managed_fund['Date'] = pd.to_datetime(df_managed_fund['Date'])
    df_managed_fund['Position'] = [principal * (1 + rate) ** (i/365.25) for i in range(period + 1)]
    df_managed_fund = df_managed_fund[df_managed_fund['Date'].isin(df_yf_fund.index.values)]
    df_managed_fund = df_managed_fund.set_index('Date')
    df_managed_fund['legend'] = 'Managed Fund'
    df_managed_fund.columns = [f'Managed {i}' for i in df_managed_fund.columns]
    return df_managed_fund, rate
    
def create_source(df_fund1, df_fund2):
    df_source = pd.DataFrame()
    df_fund1.index = pd.to_datetime(df_fund1.index)
    df_fund2.index = pd.to_datetime(df_fund2.index)
 
    legend1 = next(i for i in df_fund1.columns if 'legend' in i)
    legend2 = next(i for i in df_fund2.columns if 'legend' in i)
    
    df_fund1 = df_fund1.rename(columns={legend1:'legend1'})
    df_fund2 = df_fund2.rename(columns={legend2:'legend2'})
    
    col1 = next(i for i in df_fund1.columns if 'Position' in i)
    col2 = next(i for i in df_fund2.columns if 'Position' in i)
    
    df_source = df_fund1.join(df_fund2, how='inner', rsuffix='_2')    
    df_source['Difference'] = df_fund1[col1] - df_fund2[col2]
    return df_source

def make_plot(df_source, title):
    source = ColumnDataSource(df_source)
    position_col = [i for i in df_source.columns if 'Position' in i]

    line1 = position_col[0]
    line2 = position_col[1]
    
    labels = [x.strip() for x in title.split('vs.')]
    label1 = labels[0]
    label2 = labels[1]
    
    TOOLTIPS = [
            ('Date', '@Date{%F}'),
            (f'{label1}', f'@{{{line1}}}{{$0,0}}'),        
            (f'{label2}', f'@{{{line2}}}{{$0,0}}'),
            ('Difference', '@Difference{$0,0}'),                
            ]
      
    plot = figure(width_policy = 'fit', height_policy = 'fit', x_axis_type='datetime', title = title)
    plot.line('Date', line1, source = source, legend_field = 'legend1', color = d3['Category10'][10][0], line_width = 3)
    plot.line('Date', line2, source = source, legend_field = 'legend2', color = d3['Category10'][10][1], line_width = 3)
    plot.add_tools(CrosshairTool())
    plot.add_tools(HoverTool(tooltips = TOOLTIPS, formatters={'@Date': 'datetime'}))
    plot.legend.location = 'top_left'
    plot.legend.click_policy = 'hide'
    plot.xaxis.axis_label = 'Date'
    plot.yaxis.axis_label = 'USD ($)'

    return plot, source        

def update(attr, old, new, i):
    start_date = pd.to_datetime(start_date_picker[i].value).date()
    end_date = pd.to_datetime(end_date_picker[i].value).date()
    principal = principal_spinner[i].value
    current_value = current_value_spinner[i].value
    min_date = find_min_date(i)
    start_date_picker[i].min_date = min_date
    
    if start_date < min_date:
        start_date_picker[i].value = min_date
        start_date = min_date
    
    if i == 1:
        df_fund_1[1], index_cost_basis = yf_fund(fund_1[1].value, start_date, end_date, principal)
        df_fund_2[1], rate = managed_fund(principal, current_value, df_fund_1[1])
        df_source[1] = create_source(df_fund_1[1], df_fund_2[1])
        
        new_source = ColumnDataSource(df_source[1])
        source[i].data.update(new_source.data)
    
    else:
        df_fund_1[i], stock_cost_basis = yf_fund(fund_1[i].value, start_date, end_date, principal)
        df_fund_2[i], stock2_cost_basis = yf_fund(fund_2[i].value, start_date, end_date, principal)
        df_source[i] = create_source(df_fund_1[i], df_fund_2[i])
        
        new_source = ColumnDataSource(df_source[i])
        source[i].data.update(new_source.data)        
            
def find_min_date(i):
    if i == 1:
        ticker = ticker_symbols[fund_1[i].value]
        min_date = yf.Ticker(ticker).history(period='max').head(1).index[0].date()
    else:
        min_date_top = yf.Ticker(fund_1[i].value).history(period='max').head(1).index[0].date()

        if fund_2[i].value in [i for i in ticker_symbols.keys()]:
            ticker = ticker_symbols[fund_2[i].value]
            min_date_bottom = yf.Ticker(ticker).history(period='max').head(1).index[0].date()
        else:
            min_date_bottom = yf.Ticker(fund_2[i].value).history(period='max').head(1).index[0].date()
        
        min_date = max(min_date_top, min_date_bottom)
    
    return min_date
          
#WIDGETS

principal = 1000.0
current_value = 3000.0
ticker = 'S&P 500'
start_date = date(2016, 5, 3)
end_date = date(2021, 5, 7)
max_date = yf.Ticker(ticker_symbols[ticker]).history(period='max').index[-1].date()

start_date_picker = {}
end_date_picker = {}
principal_spinner = {}
current_value_spinner = {}
fund_1 = {}
fund_2 = {}

fund_1[1] = Select(title='Index Fund', value = 'S&P 500', options = ['DJI', 'S&P 500'])
fund_2[1] = None

fund_1[2] = TextInput(value="AMZN", title="Stock Ticker Symbol")
fund_2[2] = Select(title='Index Fund', value = 'S&P 500', options = ['DJI', 'S&P 500'])

fund_1[3] = TextInput(value="AMZN", title="Stock Ticker Symbol")
fund_2[3] = TextInput(value="GOOG", title="Stock 2 Ticker Symbol")

for i in [1,2,3]:
    start_date_picker[i] = DatePicker(title = 'Start Date', value = start_date, min_date = find_min_date(i), 
                                      max_date = max_date)#, min_date="2019-08-01", max_date="2019-10-30")
    end_date_picker[i] = DatePicker(title = 'End Date', value = end_date, min_date = find_min_date(i), 
                                    max_date = max_date) 
    principal_spinner[i] = Spinner(value=principal, step=1, title='Principal')
    current_value_spinner[i] = Spinner(value=current_value, step=1, title='Current Value')

df_fund_1 = {}
df_fund_2 = {}
df_source = {}
source = {}

# Tab 1
# Data
    
df_fund_1[1], index_cost_basis = yf_fund(fund_1[1].value, start_date, end_date, principal)
df_fund_2[1], rate = managed_fund(principal, current_value, df_fund_1[1])
df_source[1] = create_source(df_fund_1[1], df_fund_2[1])

#Set-up Plots

plot1, source[1] = make_plot(df_source[1], 'Managed Fund vs. Index Fund')
      
# Layout

inputs = column(principal_spinner[1], current_value_spinner[1], fund_1[1], start_date_picker[1], 
                end_date_picker[1])
tab_managed = Panel(child = row(plot1, inputs), title = 'Managed Fund vs Index Fund')
  
# Tab2
# Data

df_fund_1[2], index_cost_basis = yf_fund(fund_1[2].value, start_date, end_date, principal)
df_fund_2[2], stock_cost_basis = yf_fund(fund_2[2].value, start_date, end_date, principal)    
df_source[2] = create_source(df_fund_1[2], df_fund_2[2])

# Plots

plot2, source[2] = make_plot(df_source[2], 'Stock vs. Index Fund')
current_value_stock = df_source[2]['Stock Position'][-1]

# Layout

inputs_stock = column(principal_spinner[2], fund_1[2], fund_2[2], start_date_picker[2], 
                      end_date_picker[2])
tab_stock = Panel(child = row(plot2, inputs_stock), title = 'Stock vs Index Fund')

layout = Tabs(tabs=[tab_managed, tab_stock])
    
for i in [1, 2]:
    test = start_date_picker[i]
    start_date_picker[i].on_change('value', partial(update, i = i))
    end_date_picker[i].on_change('value', partial(update, i = i))
    principal_spinner[i].on_change('value', partial(update, i = i))
    current_value_spinner[i].on_change('value', partial(update, i = i))
    
    fund_1[i].on_change('value', partial(update, i = i))    
    if i != 1:
        fund_2[i].on_change('value', partial(update, i = i))        

curdoc().add_root(layout)
    
