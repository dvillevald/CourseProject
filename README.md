## CS 410 Course Project

## Using the sentiment analysis of companys' SEC filings to predict future stock returns
### CS410 Final Project (Individual project)
### Project coordinator/Author: Dmitry Villevald (dmitryv2@illinois.edu)

### Goal
For my final project I chose a free topic (Option 5) and explores the impact of the sentiment extracted from company's 10-Q and 10-k SEC filings on the company's stock price. My expectation is while there could be a minor impact from the sentiment changes in the filings on the stock price for some companies, this impact is too small to use sentiment as an investment strategy. 

### Project Proposal
File [Project Proposal dmitryv2.pdf](https://github.com/dvillevald/CourseProject/blob/main/Project%20Proposal%20dmitryv2.pdf) contains the project proposal.

### Project Progress Report
File [Project Progress Report dmitryv2.pdf](https://github.com/dvillevald/CourseProject/blob/main/Project%20Progress%20Report%20dmitryv2.pdf) is a project progress report.

### Self-Evaluation
I completed most of what I planned. I was able to load from SEC database the index files with the filings and extract the quarterly (10-Q) and annual (10-K) filings for the selected companies. Originally I planned to extract only Management Analysis and Discussion (MD&A) section of 10-Q and 10-K filings for the sentiment analysis. However, after I learned that in many filings MD&A is a list of links to the other sections of the document, I decided that a better approach would be to use the entire SEC filing for the sentiment analysis. I managed to parse those filings into single words and built a bad-of-words (unigram) representation with calculated term frequencies for each filing. Then, by comparing these representations with [LoughranMcDonald sentiment lists](https://sraf.nd.edu/textual-analysis/resources/#LM%20Sentiment%20Word%20Lists) I was able to calculate four sentiment scores (Positive, Negative, Uncertain and Litigious) for each company's report. Finally, I successfully loaded stock prices from Yahoo, calculated forward returns adjsuted for stock splits and joined them data with the sentiment data. Finally, I was able to estimate expected returns for a few sentiment-based investment strategies. 

### Main Results
Although I only explored a small sample of data for a few companies (about 20 large companies in total), I was able to observe some interesting results. For example, I found that Negative, Uncertain and Litigious sentiments are strongly correlated which suggests that if we use one of there three sentiments in out investment strategy, the incremental impact from including the other two will probably be marginal if any:

Regarding the correlation between future returns and changes in sentiment scores of SEC filings, I observed some positive correlation between 1-month-forward returns from the date of filing and positive quarterly changes in Negative, Uncertain and Litigious sentiment scores. For example, for MCD and APPL stocks the increase in negative/uncertain/litigious sentiment scores followed by *larger* stock returns over the following month which is probably contrary to what most would expect. However, given a small size of the data sample, this result is likely statistically insignificant. 
     
In conclusion, while the changes in the sentiment of company's filings seems to have some impact on the future stock returns, this impact is not large and, given the small data sample, is likely statistically insignificant. Additional research with more companies and different time periods is needed to build a viable stock investment strategy using a sentiment analysis of companies SEC filings.

Note that the chart above were built from the output of Python script **demo.py** - file **Sentiment scores of SEC filings with forward stock returns.csv** referenced below in subsection *Outputs*.

### Documented Source Code
The Python script **demo.py** 
1) Downloads 10-Q and 10-K SEC filings for selected companies. **Ticker**, **CIK** and **Company** (company name) should be provided, for each company one is interested in, in the input file **/investment_universe/tickers_and_ciks.csv** (Note that the input file for the demo contains this data for two companies - McDonalds Corp. and Apple Inc.) **Ticker** is used to load the historical company's stock prices to backtest investment strategy while **CIK** (the Central Index Key) is required to download company's filings from SEC's EDGAR database.  
2) Calculates term frequency for each filing,
3) Estimates sentiment scores (Positive, Negative, Uncertain and Litigious) for each report,
4) Loads company's stock prices and calculates weekly, quarterly and yearly 
   forward returns, starting from the filing date (+ execution_lag_days to mitigate a look-ahead bias via simulation of a more realistic and conservative scenario where the stocks were purchased/sold on the next business day after the filing date).
5) Combines together sentiment scores and foward returns, calculates returns of investment strategies and saves the results in **/results/Investment strategies results.csv**

#### Instructions
1) To run the script, please assign to variable **base_path** the location of (path to) the project folder.

Example: `base_path = '/Users/dmitryvillevald/Documents/UIUC/CS 410 Text Information Systems/Final Project/demo'`

2) The following packages have to be installed to run the script: requests, BeautifulSoup, json, urllib, yfinance, pandas, csv

#### Inputs
The script *demo.py* takes the following inputs:
1) Input file **/investment_universe/tickers_and_ciks.csv** with a list of companies (stocks) you want to test the investment strategy on. For each company ones has provide:
- **Ticker** - the exchange ticker of company's stock. Ticker is used to load the historical company's stock prices to backtest investment strategy
- **CIK** - the Central Index Key of a company in SEC database. CIK is required to download company's filings from SEC's EDGAR database for sentiment analysis
- **Company** - the Company's name which is used for reference only

(Note that the input file for the demo contains this data for two companies - McDonalds Corp. and Apple Inc.)

2) Four files with LoughranMcDonald sentiment lists (**positive.csv**, **negative.csv**, **uncertain.csv** and **litigious.csv**) located in folder named **/sentiment_word_lists** 

#### Outputs
The script *demo.py* outputs two files stored in the folder **/results**:
1) File **Sentiment scores of SEC filings with forward stock returns.csv** contains a history of the sentiment scores for the selected companies, the changes (quarterly and yearly) of those sentiment scores and forward weekly, monthly and quarterly total stock returns (including dividends) adjusted for stock splits and spinoffs
2) File **Investment strategies results.csv** contains the results of test testing simple investment strategy where one takes a long position in a stock (i.e buys) when the sentiment percent change value exceeds the *long* threshold and takes a short position in a stock (i.e. sell short) when the sentiment percent change falls below the *short* threshold.  

### Demo (Video)
The video with demonstration of demo.py and the output can be found [here](www.youtube.com)

### Credits
