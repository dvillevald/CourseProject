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
Ticker = 'MCD'
CIK = '0000063908'

# Time period: first and last year and quarter
# It covers SEC filings from start_qrt/start_year to end_quarter/end_year inclusive
start_year = 2016
end_year = 2020

start_qtr = 1
end_qtr = 2

# INPUT
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
sentiment_with_stock_returns_filename = Ticker + '_sent_with_stock_returns.csv'

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
def download_edgar_idx_files(start_year = start_year, 
                             end_year = end_year, 
                             start_qtr = start_qtr, 
                             end_qtr = end_qtr):

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


# Function build_sec_filings_url_list builds a list of urls of 
# 10Q and 10K SEC filings for companies (CIKs) - members of stock index (e.g. DJIA)
# for specified years-quarters
# It returns a list of (filing_file_name, filing url, filing date) tuples
def build_sec_filings_url_list(company_cik = CIK, 
                           start_year = start_year, 
                           end_year = end_year, 
                           start_qtr = start_qtr, 
                           end_qtr = end_qtr):
    
    print(f'\nStep 2. Locating 10-Q and 10-K filings for ticker {Ticker} in SEC index files ...')
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

                print(f'Found {Ticker} filing for {yr}, QTR{qtr}')
                with open(local_file_path, 'r', encoding='latin-1') as f:
                    for line in f:
                        if line.find('|10-Q|') > 0 or line.find('|10-K|') > 0:
                            items = line.split('|')
                            cik = int(items[0])
                            if cik == int(company_cik):
                                filing_filename = f'CIK{cik}-{yr}-QTR{qtr}.json'
                                filing_file_url = items[4].rstrip()
                                filing_date = items[3].rstrip()
                                sec_filings_url_list.append((filing_filename, 
                                                             filing_file_url, 
                                                             filing_date))
    
    print('Step 2 is competed. The list of selected SEC filings is built.')
    print(f'{len(sec_filings_url_list)} 10-Q and 10-K SEC filings for {Ticker} were found.')

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
    for filing_filename, filing_file_url, filing_date in  sec_filings_url_list:
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
# along with CIK, Ticker and Filing Date

def estimate_sentiment():
    
    print('\nStep 5. Calculating sentiment scores for selected filings ...')
    ticker = Ticker
    sentiment_scores = []
    sentiment_scores_columns = ['CIK', 'Ticker', 'Filing Date', 'Pos', 'Neg', 'Unc', 'Lit']
    
    for filing_filename, filing_file_url, filing_date in sec_filings_url_list:
        cik = filing_filename.split('-')[0][3:]
        if int(cik) != int(CIK):
            raise Exception(f'CIK from the file:{cik} does not match company CIK {CIK}')

        filing_file_path = '/'.join([base_path, 'selected_filings', filing_filename])
        # Check if filing file exists        
        current_files = os.listdir('/'.join([base_path, 'selected_filings']))
        if filing_filename not in current_files:
            print(f'Filing {filing_filename} could not be parsed.')
            sentiment_scores.append([cik, ticker, filing_date, 0., 0., 0., 0.])
        
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
                sentiment_scores.append([cik, ticker, filing_date,
                                         round(100. * pos/tot,2), 
                                         round(100. * neg/tot,2), 
                                         round(100. * unc/tot,2), 
                                         round(100. * lit/tot,2)])
                
    print('Step 5 is completed. Sentiment scores are computed for each report.')
    return pd.DataFrame(sentiment_scores, columns = sentiment_scores_columns)

#sentiment_scores = estimate_sentiment()


### Step 6. Get stock prices, calculate forward stock return
###         and combine this data with sentiment variables


# Function get_stock_returns() reads stock prices for tickers of
# companies - members of specified stock index (e.g. DJIA_CIKs.csv)
def get_stock_returns(ticker = Ticker):  
    
    print(f'\nStep 6. Get stock prices for ticker {Ticker} ...')

    # Load proces and calculate weekly, monthly and quarterly forward returns
    # from Adj Close prices
    start_date = str(start_year) + '-01-01'
    end_date = str(end_year) + '-12-31'
    
    # Load stock prices for Ticker    
    print(f'Loading price history for ticker {Ticker}...')
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
    tot_return['Fret_w'] = 100. * (tot_return['Adj Close W']/tot_return['Adj Close']-1)
    tot_return['Fret_m'] = 100. * (tot_return['Adj Close M']/tot_return['Adj Close']-1)
    tot_return['Fret_q'] = 100. * (tot_return['Adj Close Q']/tot_return['Adj Close']-1)
    tot_return = tot_return[['Fret_w', 'Fret_m', 'Fret_q']]
    tot_return['Ticker'] = ticker
    tot_return = tot_return.loc[start_date : end_date]
                    
    # Wait one-tenth of a second before sending another request to Yahoo.
    time.sleep(0.1)
    print('Stock prices are loaded.')
    return tot_return[['Ticker', 'Fret_w', 'Fret_m', 'Fret_q']]  

#tot_returns = get_stock_returns()


# Function get_sentiment_with_stock_returns() merges 1-week, 1-month and 1-quarter
# forward stock returns with the sentiment scores calculated 
# for each 10-Q and 10-K SEC report filed by the company
def get_sentiment_with_stock_returns():
    sent_scores = sentiment_scores.copy()
    sent_scores['Date'] = pd.to_datetime(sent_scores['Filing Date'])
    sent_scores = sent_scores.drop('Filing Date', axis = 1)

    tot_rets = tot_returns.copy()
    tot_rets = tot_rets.reset_index(level=0)

    sent_scores_w_tot_rets = pd.merge(sent_scores, tot_rets, 
                                      on=['Ticker', 'Date'], 
                                      how='left')
    print('Step 6 is completed. Output file is created.')
    return sent_scores_w_tot_rets

#sentiment_with_stock_returns = get_sentiment_with_stock_returns()



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

    # Step 6. Get stock prices, calculate forward stock return
    # and combine this data with sentiment variables
    tot_returns = get_stock_returns()
    sentiment_with_stock_returns = get_sentiment_with_stock_returns()

    # Save the results
    sentiment_with_stock_returns.to_csv('/'.join([base_path,
                                               sentiment_with_stock_returns_filename]), 
                                               index=False)        
    
  # End of code



