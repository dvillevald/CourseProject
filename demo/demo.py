#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Nov  7 21:22:41 2020
@author: dmitryv2@illinois.edu

This is a deno code which reads company's 10-Q and 10-K filings
from SEC EDGAR databse, calculates sentiment scores for each report 
and outputs results along with forward stock returns for analysis. In particular:
    
1) Downloads 10-Q and 10-K SEC filings for a given company over specified type period, 
2) Calculates term frequency for each term in each report,
3) Estimates sentiment scores (Positive, Negative, Uncertain and Litigious) for each report,
4) Loads company's stock prices and calculates weekly, quarterly and yearly 
   forward returns (starting from the filing date + execution_lag_days) for each report,
5) Combines together sentiment scores and foward returns and save resuls for analysis
"""

import os
import requests
import time
from bs4 import BeautifulSoup
import re
import json
import urllib
import yfinance as yf
import pandas as pd
import csv
import warnings
warnings.simplefilter("ignore")

# Absolute path to the project folder 
base_path = '/Users/dmitryvillevald/Documents/UIUC/CS 410 Text Information Systems/Final Project/demo'

# Company information - company's ticker and SEC's Central Index Key (CIK)
#Ticker = 'MCD'
#CIK = '0000063908'

# Time period: first and last year and quarter
# It covers SEC filings from start_qrt/start_year to end_quarter/end_year inclusive
start_year = 2016
end_year = 2020

start_qtr = 1
end_qtr = 2

# INPUT
# Name of the file with list of companies which has 3 columns - Ticker, CIK and Company (name)
ticker_cik_file_name = 'tickers_and_ciks.csv'

# Name of a folder where the file with a list of eligible stocks' tickers and CIKs is located
investment_universe_folder_name = 'investment_universe'

# Name of the folder with sentiment word lists
# Source: https://sraf.nd.edu/textual-analysis/resources/#LM%20Sentiment%20Word%20Lists
sent_word_list_folder_name = 'sentiment_word_lists'

# Names of files with LoughranMcDonald SentimentWordLists
positive_filename = 'positive.csv'
negative_filename = 'negative.csv'
uncertain_filename = 'uncertain.csv'
litigious_filename = 'litigious.csv'

# OUTPUT
# Name of output file containing the sentiment scores of SEC 10-Q and 10-K reports, 
# their filing dates refiling dates weekly, week, 1-month and 1-quarter
# forward total returns (starting from the date when the company filed 
# 10-Q or 10-K SEC report) along with sentiment scores
sentiment_with_stock_returns_filename = 'Sentiment scores of SEC filings with forward stock returns.csv'

# Name of output file containing the sentiment scores of SEC 10-Q and 10-K reports, 
# their filing dates refiling dates weekly, week, 1-month and 1-quarter
# forward total returns (starting from the date when the company filed 
# 10-Q or 10-K SEC report) along with sentiment scores
investment_strategy_results_filename = 'Investment strategies results.csv'


# Back up option - set True to write intermediate results to disk
back_up = True

# Execution lag in days - a lag (0ffset), in days, between the date when company files
# SEC report and and the date when a position in company stock was taken at the market close
# This offset is needed to mitigate a look-ahead bias (because it may not be
# possible to acquire a stock on the date of a filing
execution_lag_days = 1

# Placeholder for names of files with SEC reports which the loader or parser failed
# to load or parse
bad_filings = []

# File name to save names of files where the loader or parser failed
# for back up bad_filings
bad_filings_filename = 'bad_filings.txt'

# File name to save names of (json file, url) of SEC filings
# to back up sec_filings_url_list
sec_filings_url_list_filename = 'sec_filings_url_list.txt'

# List of stop words
stop_list = ['the', 'and', 'our', 'their', 'he', 'she', 'they', 'for', 'are', 'that', 'this', 'which', 
             'january', 'february', 'march', 'april', 'may', 'june', 
             'july', 'august', 'september', 'october', 'november', 'december',
             'company', 'fiscal', 'other', 'gaap', 'financial', 
             'with', 'tax', 'from', 'billion', 'million',
             'operations', 'assets', 'not', 'including', 'value', 'consolidated', 'such',
             'year', 'have', 'related', 'certain', 'statements', 'total', 'term',
             'these',  'share',  'rate', 'business', 'could', 'information',  'amounts', 
             'was', 'any', 'will', 'its', 'were', 'over', 
             'has', 'also', 'years', 'when', 'each', 'those', 'used', 'date', 'than', 
             'then', 'though', 'although']


### Step 1. Download quarterly EDGAR index files with urls of each SEC filing


# Function download_edgar_idx_files() downloads EDGAR index files 
# for specified years-quarters
# and stores them in subfolders of (automatically created) folder 'sec_index_files'
def download_edgar_idx_files():

    print('\nStep 1. Loading SEC index files ...')
    # Check if a designated forder for SEC index files exists
    # If not, then create it.
    sec_index_files_path_name = '/'.join([base_path, 'sec_index_files'])
    if 'sec_index_files' not in os.listdir(path=base_path):
        os.mkdir(sec_index_files_path_name)
        
    # Check if folder for a given year (i.e. 2015, 2016, etc) already exists
    # If not, then create it.
    for yr in range(start_year, end_year + 1):
        if str(yr) not in os.listdir(path=sec_index_files_path_name):
            os.mkdir('/'.join([sec_index_files_path_name, str(yr)]))

    # Load index files from specified years and quareters
    for yr in range(start_year, end_year + 1):
        
        # Get a list of the files inside the year folder.
        current_files = os.listdir('/'.join([sec_index_files_path_name, str(yr)]))

        for qtr in range(1, 5):
            if (10 * yr + qtr >= 10 * start_year + start_qtr and
                    10 * yr + qtr <= 10 * end_year + end_qtr): 
                local_filename = f'xbrl-index-{yr}-QTR{qtr}.txt'
                
                # Create the absolute path for storing the index file
                local_file_path = '/'.join([sec_index_files_path_name, str(yr), local_filename])
                
                # Check if file exists already
                if local_filename in current_files:
                    print(f'Skipping index file for {yr}, QTR{qtr} because it is already saved.')
                    continue
        
                # Define the url at which to get the index file.
                url = f'https://www.sec.gov/Archives/edgar/full-index/{yr}/QTR{qtr}/xbrl.idx'
               
                # Get the index file from EDGAR and save it to a text file. Note that to save a file
                # rather than bringing it into memory, set stream=True and use r.iter_content() 
                # to break the incoming stream into chunks (here arbitrarily of size 10240 bytes)
                r = requests.get(url, stream=True)
                with open(local_file_path, 'wb') as f:
                    print(f'Loading-{yr}-QTR{qtr}')
                    for chunk in r.iter_content(chunk_size=10240):
                        f.write(chunk)
                
                    # Wait one-tenth of a second before sending another request to EDGAR.
                    time.sleep(1.0)
                    
    print('Step 1 is completed. SEC index files are loaded.')              
 
#download_edgar_idx_files()


### Step 2. Build a list of tuples (file to store data, url, filing date) for
###         each 10-Q or 10-K SEC filing between start and end year/quarter
###         for a specified company (CIK)


# Function build_sec_filings_url_list builds a list of urls of two types of SEC filings
# - 10-Q and 10-K - for a given company (CIKs) for specified years-quarters
# It returns a list of (filing_file_name, filing url, filing date, filing_type) tuples
def build_sec_filings_url_list():
    
    print('\nStep 2. Locating 10-Q and 10-K filings for members of investment universe in SEC index files ...')

    # Check if a folder with investment universe members exists    
    if investment_universe_folder_name not in os.listdir(path=base_path):
        raise Exception('Folder with Tickers/CIKs of investment universe members does not exist')

    inv_universe_folder_path_name = '/'.join([base_path, investment_universe_folder_name])
    if ticker_cik_file_name not in os.listdir(path=inv_universe_folder_path_name):
            raise Exception(f'File {ticker_cik_file_name} does not exist')

    ticker_cik_file_path = '/'.join([inv_universe_folder_path_name, ticker_cik_file_name])

    ciks_and_tickers = {}
    with open(ticker_cik_file_path, 'r') as ciks_file:
        csvreader = csv.reader(ciks_file, delimiter=',')
        next(csvreader) # skip header row
        for row in csvreader:
            _ticker = str(row[0])
            _cik = int(row[1])
            ciks_and_tickers[_cik] = _ticker

    # Check if a folder with SEC index files exists
    sec_index_files_path_name = '/'.join([base_path, 'sec_index_files'])
    
    if 'sec_index_files' not in os.listdir(path=base_path):
        raise Exception('Folder with SEC index files does not exist')
    
    # Extract only required reports 10Q and 10K only for companies - index members
    sec_filings_url_list = []
   
    for yr in range(start_year, end_year + 1):
        if str(yr) not in os.listdir(path=sec_index_files_path_name):
            raise Exception(f'Folder {yr} does not exist')
        
        # Get a list of the files inside the year folder.
        current_files = os.listdir('/'.join([sec_index_files_path_name, str(yr)]))    
    
        for qtr in range(1, 5):
            if (10 * yr + qtr >= 10 * start_year + start_qtr and
                10 * yr + qtr <= 10 * end_year + end_qtr): 
                local_filename = f'xbrl-index-{yr}-QTR{qtr}.txt'
                
                # Create the absolute path for storing the index file
                local_file_path = '/'.join([sec_index_files_path_name, str(yr), local_filename])
                
                # Check if file exists (before processing)
                if local_filename not in current_files:
                    raise Exception(f'File for {yr}, QTR{qtr} does not exist.')

                with open(local_file_path, 'r', encoding='latin-1') as f:
                    for line in f:
                        if line.find('|10-Q|') > 0 or line.find('|10-K|') > 0:
                            items = line.split('|')
                            cik = int(items[0])
                            if int(cik) in ciks_and_tickers:
                                ciks_and_tickers[cik]
                                print(f'Found {ciks_and_tickers[cik]} filing for {yr}, QTR{qtr}')
                                filing_filename = f'CIK{cik}-{yr}-QTR{qtr}.json'
                                filing_file_url = items[4].rstrip()
                                filing_date = items[3].rstrip()
                                if line.find('|10-Q|') > 0:
                                    filing_type = '10-Q'
                                elif line.find('|10-K|') > 0:
                                    filing_type = '10-K'
                                else:
                                    raise Exception('Unknown filing type')
                                sec_filings_url_list.append((filing_filename, 
                                                             filing_file_url, 
                                                             filing_date,
                                                             filing_type))
    
    print('Step 2 is competed. The list of selected SEC filings is built.')
    print(f'{len(sec_filings_url_list)} 10-Q and 10-K SEC filings were found.')

    return sec_filings_url_list
            
#sec_filings_url_list = build_sec_filings_url_list()


### Step 3. Create a vocab file (terms and their frequency) for each 
###         10-Q and 10-K SEC filing.


# Function build_vocab() cleans the raw text from the SEC filings
# and builds a dictionary (vocabulary) with words as keys and word frequencies as values
# (sorted by values in descending order)
def build_vocab(raw_text, stop_list = stop_list):
    text = BeautifulSoup(raw_text, 'html.parser')
    text = re.sub('[^a-zA-Z]+', ' ', text.document.get_text())
    text = text.lower()
    text = text.split(' ')
    words = []
    for word in text:
        if len(word) > 2 and word not in stop_list:
            words.append(word)
    vocab = {}
    for word in words:
        if word not in vocab:
            vocab[word] = 1
        else:
            vocab[word] += 1
    vocab_sorted = {}      
    for word in sorted(vocab, key=vocab.get, reverse=True):
        vocab_sorted[word] = vocab[word]
    return vocab_sorted


# Function process_sec_filings() reads  
# 10-Q and 10-K SEC filings for specified company (CIK)
# and outputs a dictionary with term frequencies for each document
def process_sec_filings():
    
    print('\nStep 3. Create term frequency dictionary for each selected filing ...')
    # Create a folder for term frequency dictionaries from SEC filings named 'selected_filings'
    if 'selected_filings' not in os.listdir(path=base_path):
        os.mkdir('/'.join([base_path, 'selected_filings']))

    # Iterate over filings
    for filing_filename, filing_file_url, filing_date, filing_type in sec_filings_url_list:
        local_filing_file_path = '/'.join([base_path, 'selected_filings', filing_filename])
        url = f'https://www.sec.gov/Archives/{filing_file_url}'
        
        if filing_filename in bad_filings:
            print(f'Skipping file {filing_filename} - could not parse it.')
            continue
        
        current_files = os.listdir('/'.join([base_path, 'selected_filings']))
        
        # Check if file exists already
        if filing_filename in current_files:
            print(f'Skipping file {filing_filename} because it is already saved.')
            continue

        # Get the index file from EDGAR and save it to a text file. Note that to save a file
        # rather than bringing it into memory, set stream=True and use r.iter_content() 
        # to break the incoming stream into chunks (here arbitrarily of size 10240 bytes)
        with urllib.request.urlopen(url) as load:
            print(f'Building term frequency dictionary for {filing_filename}')
            raw_text = load.read()
            try:
                vocab = build_vocab(raw_text)
            except:
                bad_filings.append(filing_filename)
                print(f'Cannot parse {filing_filename}')
                continue
            with open(local_filing_file_path, 'w') as f:
                json.dump(vocab, f)
                            
                # Wait one second before sending another request to EDGAR.
                time.sleep(1.0)
    print('Step 3 is competed. Term frequency dictionaries is created for all filings. ')
    print(f'{len(bad_filings)} out of {len(sec_filings_url_list)} could not be loaded or parsed.\n')

#process_sec_filings()


### Step 4. (Optional) Back up bad_filings and sec_filings_url_list


# Function back_up_data() backs up data by saving them on disk
# in folder 'back_up' (if this folder does not exist, it is created)  
def back_up_data(data, filename):
    
    # Create a back up folder named 'back_up' for saving intermediate results
    back_up_folder_path = '/'.join([base_path, 'back_up'])
    if 'back_up' not in os.listdir(path=base_path):
        os.mkdir('/'.join([base_path, 'back_up']))
                
    back_up_filings_file_path = '/'.join([back_up_folder_path, filename])
    with open(back_up_filings_file_path, 'w') as f:
        for line in data:
            f.write(str(line) +"\n")
    
    print(f'Step 4 is completed. Data is backed up in {filename}')


### Step 5. Estimate sentiment of each SEC filing


# Function read_sentiment_list() reads a list of sentiment words
# and convert them into lower case
def read_sentiment_list(filename):
    
    # Check if folder with sentiment word names exist
    if sent_word_list_folder_name not in os.listdir(path=base_path):
        raise Exception(f'Folder {sent_word_list_folder_name} does not exist')

    sentiment_word_list = []
    file_path = '/'.join([base_path, sent_word_list_folder_name, filename])
    with open(file_path, 'r') as f:
        csvreader = csv.reader(f, delimiter=',')
        for word in csvreader:
            sentiment_word_list.append(word[0].lower())
    return sentiment_word_list

#positive_words = read_sentiment_list(positive_filename)
#negative_words = read_sentiment_list(negative_filename)
#uncertain_words = read_sentiment_list(uncertain_filename)
#litigious_words = read_sentiment_list(litigious_filename)


# Function estimate_sentiment() returns sentiment scores for each SEC filing:
# Pos = (a share of positive words in total # of words)
# Neg = (a share of negative words in total # of words)
# Unc = (a share of uncertain words in total # of words)
# Lit = (a share of litigious words in total # of words)
# along with CIK, Ticker, Filing Date and Filing Type (10-Q or 10-K), Year and Quarter
def estimate_sentiment():
    
    print('\nStep 5. Calculating sentiment scores for selected filings ...')
    
    # Build CIK-to-Ticker map for members of investment universe
    if investment_universe_folder_name not in os.listdir(path=base_path):
        raise Exception('Folder with Tickers/CIKs of investment universe members does not exist')

    inv_universe_folder_path_name = '/'.join([base_path, investment_universe_folder_name])
    if ticker_cik_file_name not in os.listdir(path=inv_universe_folder_path_name):
            raise Exception(f'File {ticker_cik_file_name} does not exist')

    ticker_cik_file_path = '/'.join([inv_universe_folder_path_name, ticker_cik_file_name])

    ciks_to_tickers = {}
    with open(ticker_cik_file_path, 'r') as ciks_file:
        csvreader = csv.reader(ciks_file, delimiter=',')
        next(csvreader) # skip header row
        for row in csvreader:
            _ticker = str(row[0])
            _cik = int(row[1])
            ciks_to_tickers[_cik] = _ticker
            
    sentiment_scores = []
    sentiment_scores_columns = ['CIK', 'Ticker', 'Filing Date', 'Filing Type',
                                'Year', 'Quarter',
                                'Pos', 'Neg', 'Unc', 'Lit']
    
    for filing_filename, filing_file_url, filing_date, filing_type in sec_filings_url_list:
        cik = filing_filename.split('-')[0][3:]
        year = int(filing_filename.split('-')[1][0:4])
        quarter = int(filing_filename.split('-')[2][3:4])
        if int(cik) not in ciks_to_tickers:
            raise Exception(f'CIK from the file:{cik} does not match any company CIK')

        filing_file_path = '/'.join([base_path, 'selected_filings', filing_filename])
        # Check if filing file exists        
        current_files = os.listdir('/'.join([base_path, 'selected_filings']))
        if filing_filename not in current_files:
            print(f'Filing {filing_filename} could not be parsed.')
            #sentiment_scores.append([cik, ticker, filing_date, filing_type,
            #                         year, quarter, 0., 0., 0., 0.])
        
        else:
            print(f'Computing sentiment scores for {filing_filename}.')
            tot = 0;
            pos = 0;
            neg = 0;
            unc = 0;
            lit = 0;
            with open(filing_file_path, 'r') as f:
                vocab = json.load(f)
                for word, cnt in vocab.items():
                    tot += cnt
                    if word in positive_words:
                        pos += cnt
                    if word in negative_words:
                        neg += cnt
                    if word in uncertain_words:
                        unc += cnt
                    if word in litigious_words:
                        lit += cnt
                sentiment_scores.append([cik, ciks_to_tickers[int(cik)], filing_date, 
                                         filing_type, year, quarter,
                                         round(100. * pos/tot,2), 
                                         round(100. * neg/tot,2), 
                                         round(100. * unc/tot,2), 
                                         round(100. * lit/tot,2)])
                
    print('Step 5 is completed. Sentiment scores are computed for each parsed filing.')
    return pd.DataFrame(sentiment_scores, columns = sentiment_scores_columns)

#sentiment_scores = estimate_sentiment()


### Step 6. Get stock prices, calculate forward stock return
###         and combine this data with sentiment variables


# Function get_stock_returns() reads stock prices for tickers of
# companies - members of specified stock index (e.g. DJIA_CIKs.csv)
def get_stock_returns():  
    
    print('\nStep 6. Get stock prices for members of investment universe ...')

    # Load proces and calculate weekly, monthly and quarterly forward returns
    # from Adj Close prices
    start_date = str(start_year) + '-01-01'
    end_date = str(end_year) + '-12-31'
    
    # Build list of tickers for members of investment universe
    if investment_universe_folder_name not in os.listdir(path=base_path):
        raise Exception('Folder with Tickers/CIKs of investment universe members does not exist')

    inv_universe_folder_path_name = '/'.join([base_path, investment_universe_folder_name])
    if ticker_cik_file_name not in os.listdir(path=inv_universe_folder_path_name):
            raise Exception(f'File {ticker_cik_file_name} does not exist')

    ticker_cik_file_path = '/'.join([inv_universe_folder_path_name, ticker_cik_file_name])

    list_of_tickers = []
    with open(ticker_cik_file_path, 'r') as ciks_file:
        csvreader = csv.reader(ciks_file, delimiter=',')
        next(csvreader) # skip header row
        for row in csvreader:
            _ticker = str(row[0])
            list_of_tickers.append(_ticker)
    list_of_tickers = list(set(list_of_tickers))
            
    for counter, ticker in enumerate(list_of_tickers):  
    
        # Load stock prices for ticker from Yahoo 
        print(f'Loading price history for ticker {ticker}...')
        price = yf.download(ticker, start=start_date, end=end_date, progress=False, interval="1d")
        price = price[['Adj Close']]
        
        # Implement execution lag in days
        price = price.shift(periods = -execution_lag_days, axis = 0)
        
        # Calculate total forward returns
        fprice_w = price.shift(periods = -5, axis = 0)
        fprice_w.columns = ['Adj Close W']
        fprice_m = price.shift(periods = -22, axis = 0)
        fprice_m.columns = ['Adj Close M']
        fprice_q = price.shift(periods = -65, axis = 0)
        fprice_q.columns = ['Adj Close Q']
        tot_return = pd.concat([price, fprice_w, fprice_m, fprice_q], axis = 1)
        tot_return['Fwd-1-Week Return'] = round(100. * (tot_return['Adj Close W']/tot_return['Adj Close']-1),2)
        tot_return['Fwd-1-Month Return'] = round(100. * (tot_return['Adj Close M']/tot_return['Adj Close']-1),2)
        tot_return['Fwd-1-Qtr Return'] = round(100. * (tot_return['Adj Close Q']/tot_return['Adj Close']-1),2)
        tot_return = tot_return[['Fwd-1-Week Return', 'Fwd-1-Month Return', 'Fwd-1-Qtr Return']]
        tot_return['Ticker'] = ticker
        tot_return = tot_return.loc[start_date : end_date]
                    
        # Wait one-tenth of a second before sending another request to Yahoo.
        time.sleep(0.1)
        
        if counter == 0:
            tot_returns = tot_return.copy()
        else:
            tot_returns = pd.concat([tot_returns, tot_return])
        
    print('Stock prices are loaded and forward returns are calculated.')
    return tot_returns[['Ticker', 'Fwd-1-Week Return', 'Fwd-1-Month Return', 'Fwd-1-Qtr Return']]  

#tot_returns = get_stock_returns()


# Function get_sentiment_with_stock_returns() merges 1-week, 1-month and 1-quarter
# forward stock returns with the sentiment scores calculated 
# for each 10-Q and 10-K SEC report filed by the company
def join_sentiment_with_stock_returns():
    sent_scores = sentiment_scores.copy()
    sent_scores['Date'] = pd.to_datetime(sent_scores['Filing Date'])
    sent_scores = sent_scores.drop('Filing Date', axis = 1)

    tot_rets = tot_returns.copy()
    tot_rets = tot_rets.reset_index(level=0)

    sentiment_w_rets = pd.merge(sent_scores, tot_rets, 
                                      on=['Ticker', 'Date'], 
                                      how='inner')
    sentiment_w_rets = sentiment_w_rets.rename(columns={'Date': 'Filing Date'})
    
    # Calculate sentiment data from previous quarter
    prev_qtr_sentiment_data = sentiment_w_rets[['Ticker', 'CIK', 'Year', 'Quarter',
                                           'Pos', 'Neg', 'Unc', 'Lit']]
    prev_qtr_sentiment_data = prev_qtr_sentiment_data.rename(
        columns={'Pos': 'Pos 1Q Ago','Neg': 'Neg 1Q Ago', 'Unc': 'Unc 1Q Ago', 'Lit': 'Lit 1Q Ago'})
    
    # Increment 'Quarter' for merging with the current sentiment data
    prev_qtr_sentiment_data['Quarter'] = prev_qtr_sentiment_data['Quarter'] + 1
    # Make adjustments for fourth quarter
    qtr4_adjustment = prev_qtr_sentiment_data['Quarter'] == 5
    prev_qtr_sentiment_data.loc[qtr4_adjustment, 'Year'] = prev_qtr_sentiment_data['Year'] + 1
    prev_qtr_sentiment_data.loc[qtr4_adjustment, 'Quarter'] = 1

    # Calculate sentiment data from previous year
    prev_year_sentiment_data = sentiment_w_rets[['Ticker', 'CIK', 'Year', 'Quarter',
                                           'Pos', 'Neg', 'Unc', 'Lit']]
    prev_year_sentiment_data = prev_year_sentiment_data.rename(
        columns={'Pos': 'Pos 1Y Ago', 'Neg': 'Neg 1Y Ago', 'Unc': 'Unc 1Y Ago', 'Lit': 'Lit 1Y Ago'})
    
    # Increment 'Year' for merging with the current sentiment data
    prev_year_sentiment_data['Year'] = prev_year_sentiment_data['Year'] + 1

    
    # Add sentiment from previous quarter and year to the data
    sentiment_w_rets1 = pd.merge(sentiment_w_rets, prev_qtr_sentiment_data, 
                                      on=['Ticker', 'CIK', 'Year', 'Quarter'], how='inner')
    
    sentiment_w_rets_final = pd.merge(sentiment_w_rets1, prev_year_sentiment_data, 
                                      on=['Ticker', 'CIK', 'Year', 'Quarter'], how='left')
    
    
    # Calculate Quarterly and Yearly Percent changes in the sentiment scores
    sentiment_w_rets_final['Pos Qtrly Pct Chng'] = round(100. * (sentiment_w_rets_final['Pos'] / 
                                                sentiment_w_rets_final['Pos 1Q Ago'] - 1.), 2)
    sentiment_w_rets_final['Neg Qtrly Pct Chng'] = round(100. * (sentiment_w_rets_final['Neg'] /
                                                sentiment_w_rets_final['Neg 1Q Ago'] - 1.), 2)
    sentiment_w_rets_final['Unc Qtrly Pct Chng'] = round(100. * (sentiment_w_rets_final['Unc'] / 
                                                sentiment_w_rets_final['Unc 1Q Ago'] - 1.), 2)
    sentiment_w_rets_final['Lit Qtrly Pct Chng'] = round(100. * (sentiment_w_rets_final['Lit'] / 
                                                sentiment_w_rets_final['Lit 1Q Ago'] - 1.), 2)

    sentiment_w_rets_final['Pos Yearly Pct Chng'] = round(100. * (sentiment_w_rets_final['Pos'] / 
                                                sentiment_w_rets_final['Pos 1Y Ago'] - 1.), 2)
    sentiment_w_rets_final['Neg Yearly Pct Chng'] = round(100. * (sentiment_w_rets_final['Neg'] /
                                                sentiment_w_rets_final['Neg 1Y Ago'] - 1.), 2)
    sentiment_w_rets_final['Unc Yearly Pct Chng'] = round(100. * (sentiment_w_rets_final['Unc'] / 
                                                sentiment_w_rets_final['Unc 1Y Ago'] - 1.), 2)
    sentiment_w_rets_final['Lit Yearly Pct Chng'] = round(100. * (sentiment_w_rets_final['Lit'] / 
                                                sentiment_w_rets_final['Lit 1Y Ago'] - 1.), 2)
    
    sentiment_w_rets_final = sentiment_w_rets_final[['Ticker', 'CIK', 'Filing Type',
            'Year', 'Quarter', 'Filing Date',
            'Pos', 'Neg', 'Unc', 'Lit',
            'Pos Qtrly Pct Chng', 'Neg Qtrly Pct Chng', 'Unc Qtrly Pct Chng', 'Lit Qtrly Pct Chng',
            'Pos Yearly Pct Chng', 'Neg Yearly Pct Chng', 'Unc Yearly Pct Chng', 'Lit Yearly Pct Chng',
            'Fwd-1-Week Return', 'Fwd-1-Month Return', 'Fwd-1-Qtr Return']]
      
    print('Step 6 is completed. Output file is created.')
    print(f'There were {len(sentiment_w_rets_final)} matching records in the output.')
    return sentiment_w_rets_final

#sentiment_with_stock_returns = get_sentiment_with_stock_returns()


### Step 7. Execute a simple sentiment-based investment strategy
###         by taking long or short position in a stock once the sentiment score's
###         percent change crosses a specific threshold value

# Function backtest_investment_strategies() backtests the sentiment-based investment 
# strategies by taking long or short position is a stock once Pct Chng of sentiment score
# crosses a specific threshold percent value and holding it for a week, month or quarter
#
# Inputs:
# - sentiment types - a tuple with sentimen types. 
#   Default: ('Pos', 'Neg', 'Unc' or 'Lit')
# - sentiment_change_periods = a tuple with values which determine if quarter-to-quarter ('Qtrly') 
#   or year-to-year ('Yearly') sentiment percent changes shoudl be used 
#   Default: ('Qtrly','Yearly')
#   Note: 'Yearly' helps to mitigate seasonality as 10-Q is filed quarterly but 10-K - annually 
#         so they are different reports.
# - long_thresholds = a tuple with min percent change in sentiment score 
#   to acquire a long position in a company stock. 
#   Default: (3, 5, 10, 25, None)
#   Example: if long_thresholds = (5) then a long position in a company stock will be
#            acquired once the percent change sentiment score is HIGHER than 5%
# - short_thresholds = a tuple with max percent change in sentiment score 
#   to acquire a short position in a company stock. 
#   Default: (-3, -5, -10, -25, None)
#   Example: if short_thresholds = (-5) then a short position in a company stock will be
#            taken once the percent change sentiment score is LOWER than -5%
#
# Outputs:
# - file with performance of each investment strategy containing average weekly, monthly 
#   and quarterly investment returns and a number of bets taken
#   (for long, short and combined portfolios)

def backtest_investment_strategies(sentiment_types = ('Pos', 'Neg', 'Unc', 'Lit'),
                                   sentiment_change_periods = ('Qtrly', 'Yearly'),
                                   long_thresholds = (3, 5, 10, 25, None),
                                   short_thresholds = (-3, -5, -10, -25, None)):
    
    print('\nStep 7. Executing sentiment-based investment strategies ...')
    
    strategies_results = []
    
    for sentiment_type in sentiment_types:
        for sentiment_change_period in sentiment_change_periods:
            sentiment_var = ' '.join([sentiment_type, sentiment_change_period, 'Pct Chng']) 
            for pct_thresh_to_invest_long in long_thresholds:
                for pct_thresh_to_invest_short in short_thresholds:
                    if pct_thresh_to_invest_long is not None:
                        rets_long = sentiment_with_stock_returns.loc[
                            sentiment_with_stock_returns[sentiment_var] > pct_thresh_to_invest_long]
                        if (len(rets_long) > 0):
                            n_long_bets = len(rets_long)
                            rets_long_w = round(rets_long['Fwd-1-Week Return'].mean(), 2)
                            rets_long_m = round(rets_long['Fwd-1-Month Return'].mean(), 2)
                            rets_long_q = round(rets_long['Fwd-1-Qtr Return'].mean(), 2)
                    else:
                        n_long_bets = rets_long_w = rets_long_m = rets_long_q = 0
                        
                    if pct_thresh_to_invest_short is not None:
                        rets_short = sentiment_with_stock_returns.loc[
                            sentiment_with_stock_returns[sentiment_var] < pct_thresh_to_invest_short]
                        if (len(rets_short) > 0):
                            n_short_bets = len(rets_short)                            
                            rets_short_w = -round(rets_short['Fwd-1-Week Return'].mean(), 2)
                            rets_short_m = -round(rets_short['Fwd-1-Month Return'].mean(), 2)
                            rets_short_q = -round(rets_short['Fwd-1-Qtr Return'].mean(), 2)
                    else:
                        n_short_bets = rets_short_w = rets_short_m = rets_short_q = 0
                    tot_srategy_ret_w = round(rets_long_w + rets_short_w, 2) 
                    tot_srategy_ret_m = round(rets_long_m + rets_short_m, 2) 
                    tot_srategy_ret_q = round(rets_long_q + rets_short_q, 2)
                    tot_bets = n_long_bets + n_short_bets
                    strategies_results.append([sentiment_type, sentiment_change_period,
                            pct_thresh_to_invest_long, pct_thresh_to_invest_short,
                            n_long_bets, rets_long_w, rets_long_m, rets_long_q,
                            n_short_bets, rets_short_w, rets_short_m, rets_short_q,
                            tot_bets, tot_srategy_ret_w, tot_srategy_ret_m, tot_srategy_ret_q])

    strategies_results_columns = ['Sentiment Type', 'Sentiment Score Change',
            'Sentment Pct Change to Invest Long', 'Sentment Pct Change to Invest Short',
            '# Long Bets', 'Avg Long Weekly Return', 'Avg Long Monthly Return', 'Avg Long Qtrly Return',
            '# Short Bets', 'Avg Short Weekly Return', 'Avg Short Monthly Return', 'Avg Short Qtrly Return',
            '# All Bets', 'Avg Strategy Weekly Return', 'Avg Strategy Monthly Return', 'Avg Strategy Qtrly Return']
    
    print('Step 7 is completed. Performance of each strategy is calculated.\n')
    return pd.DataFrame(strategies_results, 
                        columns = strategies_results_columns).sort_values(by=
                                'Avg Strategy Qtrly Return', ascending=False)

#strategies_results = backtest_investment_strategies()

# Function save_results() saves the data to csv file with name output_file_name
def save_results(data, output_file_name):
    
    # Check if output folder 'results' exists and create it if it idoes not
    results_folder_path = '/'.join([base_path, 'results'])
    if 'results' not in os.listdir(path=base_path):
        os.mkdir('/'.join([base_path, 'results']))
    
    # Save data to the disk
    data.to_csv('/'.join([results_folder_path, output_file_name]), index=False)        
    print(f'Data is saved in {output_file_name}')



if __name__ == '__main__':
    
    # Step 1. Download quarterly EDGAR index files with urls of each SEC filing
    download_edgar_idx_files()
   
    # Step 2. Build a list of tuples (file to store data, url, filing date) for
    # each 10-Q or 10-K company's SEC filing between start and end year/quarter
    sec_filings_url_list = build_sec_filings_url_list()

    # Step 3. Create a vocab file (term frequency) for each 10-Q and 10-K SEC filing
    process_sec_filings()

    # Step 4 (Optional). Backing up (saving to disk) bad_filings and sec_filings_url_list
    if back_up:
        back_up_data(bad_filings, bad_filings_filename)
        back_up_data(sec_filings_url_list, sec_filings_url_list_filename)

    # Step 5. Estimate sentiment of each 10-Q/10-K SEC filing    
    # Read lists of sentiment words
    positive_words = read_sentiment_list(positive_filename)
    negative_words = read_sentiment_list(negative_filename)
    uncertain_words = read_sentiment_list(uncertain_filename)
    litigious_words = read_sentiment_list(litigious_filename)
    
    sentiment_scores = estimate_sentiment()

    # Step 6. Get stock prices, calculate forward stock returns
    # and combine this data with sentiment variables
    tot_returns = get_stock_returns()
    sentiment_with_stock_returns = join_sentiment_with_stock_returns()

    # Step 7. Execute a set of simple sentiment-based investment strategies
    investment_strategy_results = backtest_investment_strategies()

    # Save the results
    save_results(sentiment_with_stock_returns, sentiment_with_stock_returns_filename)
    save_results(investment_strategy_results, investment_strategy_results_filename)        
    
  # End of code



