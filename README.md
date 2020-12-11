## CS 410 Course Project

## Using the sentiment analysis of companys' SEC filings to predict future stock returns
### CS410 Final Project (Individual project)
### Project coordinator/Author: Dmitry Villevald (dmitryv2@illinois.edu)

### Goal
For my final project I chose a free topic (Option 5) and explored the impact of the sentiment extracted from company's 10-Q and 10-k SEC filings on the company's stock price. My expectation was that while there could be a minor impact from the sentiment changes in the filings on the stock price for some companies, this impact is likely too small and statistically insignificant for building stock investment strategy based on the sentiment only. 

### Project Proposal
File [Project Proposal dmitryv2.pdf](https://github.com/dvillevald/CourseProject/blob/main/Project%20Proposal%20dmitryv2.pdf) contains the project proposal.

### Project Progress Report
File [Project Progress Report dmitryv2.pdf](https://github.com/dvillevald/CourseProject/blob/main/Project%20Progress%20Report%20dmitryv2.pdf) is a project progress report.

### Self-Evaluation
I completed most of what I planned. I was able to download from the SEC EDGAR database the index files with the titles and types of the public companies' filings and then extract the quarterly (10-Q) and annual (10-K) report for the selected companies. Originally I planned to extract only Management Analysis and Discussion (MD&A) section of 10-Q and 10-K filings for the sentiment analysis. However, after I learned that in many reports the MD&A is a list of links to the other sections of the document, I decided that a better approach would be to use the entire SEC filing for the sentiment analysis. I managed to parse those filings and build a bad-of-words (unigram) representation of each filing with the term frequencies. Then, by comparing these representations with [LoughranMcDonald sentiment lists](https://sraf.nd.edu/textual-analysis/resources/#LM%20Sentiment%20Word%20Lists) I was able to calculate four sentiment scores (Positive, Negative, Uncertain and Litigious) for each company's filing. Finally, after I loaded historical stock prices from Yahoo Finance, I calculated the forward returns (which include the dividents and are adjusted for stock splits) and joined them with the sentiment data. Finally, I was able to estimate expected returns for a few sentiment-based investment strategies. 

### Main Results
Although I only explored a few years (2016-2020) of filings for about 30 large US companies, I was able to observe some interesting results. For example, I found that Negative, Uncertain and Litigious sentiments are strongly correlated which suggests that if we use one of there three sentiments in out investment strategy, the incremental impact from including the other two will probably be marginal if any.

![](https://github.com/dvillevald/CourseProject/blob/main/demo/images/Correlations%20between%20qtrly%20changes%20in%20stock%20sentiments.png)

Regarding the correlation between the future returns and changes in the sentiment scores of SEC filings, I observed some positive correlation between 1-month-forward returns from the date of filing and the quarterly changes in Negative, Uncertain and Litigious sentiment scores. For example, as the chart below shows, for MCD and APPL stocks the *increase* in negative/uncertain/litigious sentiment scores was followed by *larger positive* stock returns over the following month which is probably contrary to what most would expect. 
     
![](https://github.com/dvillevald/CourseProject/blob/main/demo/images/Monthy%20forward%20stock%20returns%20for%20different%20quarterly%20changes%20in%20Uncertain%20sentiment%20score.png)

In conclusion, while the changes in the sentiment of company's filings seem to have some impact on the future stock returns, this impact is not large and, given a small data sample, is likely statistically insignificant. Additional research with more companies and longer time period is needed to build a viable stock investment strategy based on a sentiment of companies' SEC filings.

Note that the charts above were built from the output of Python script **demo.py** - file **Sentiment scores of SEC filings with forward stock returns.csv** - referenced below in subsection **Outputs**.

### Demo (Video)
The video with demonstration of demo.py and the output can be found [here](www.youtube.com)

### Documented Source Code
The Python script **demo.py** 
1) Downloads 10-Q and 10-K SEC filings for selected companies. **Ticker**, **CIK** and **Company** (company name) should be provided (for each companies one is interested in) in the input file **/investment_universe/tickers_and_ciks.csv** (Note that the input file for the demo contains this data for two companies - McDonalds Corp. and Apple Inc.) **Ticker** is used to load the historical company's stock prices to backtest investment strategy while **CIK** (the Central Index Key) is required to download company's filings from SEC's EDGAR database.  
2) Build a bag-of-words representation and calculates term frequency for each SEC filing.
3) Calculates sentiment scores (Positive, Negative, Uncertain and Litigious) for each report.
4) Downloads historical company's stock prices and calculates weekly, quarterly and yearly forward returns, starting from the filing date (+ *execution_lag_days* to mitigate a look-ahead bias via simulation of a more realistic and conservative scenario where the stocks are purchased/sold on the next business day after the filing date).
5) Combines together sentiment scores and foward returns, calculates returns of a few simple investment strategies and saves the results in folder **/results**.

#### Instructions
1) Before running the script *demo.py*, please assign to variable **base_path** the location of (path to) the project folder.

Example: `base_path = '/Users/dmitryvillevald/Documents/UIUC/CS 410 Text Information Systems/Final Project/demo'`

2) The following packages have to be installed to run the script: **requests**, **BeautifulSoup**, **json**, **urllib**, **yfinance**, **pandas**, and **csv**

#### Inputs
The script *demo.py* takes the following inputs:
1) Input file **/investment_universe/tickers_and_ciks.csv** with a list of companies (stocks) you want to test the investment strategy on. For each company one has to provide:
- **Ticker** - the exchange ticker of a company's stock. Ticker is used to load the historical company's stock prices to backtest the investment strategy
- **CIK** - the Central Index Key of a company in SEC EDGAR database. CIK is used to download the company's filings from SEC's EDGAR database for sentiment analysis
- **Company** - the Company's name which is used for reference only
Note that the input file for the demo contains this data for two companies - McDonalds Corp. and Apple Inc.
2) Four files with LoughranMcDonald sentiment lists (**positive.csv**, **negative.csv**, **uncertain.csv** and **litigious.csv**) which are located in folder **/sentiment_word_lists** 

#### Outputs
The script *demo.py* outputs two files and places them in folder **/results**:
1) File **Sentiment scores of SEC filings with forward stock returns.csv** contains (1) a history of the sentiment scores extracted from SEC filings of the selected companies, (2) the changes (quarterly and yearly) of those sentiment scores and (3) one-week, one-month and one-quarter forward total stock returns (including dividends and adjusted for stock splits and spinoffs) starting from the date of SEC filing.
2) File **Investment strategies results.csv** contains the results of testing simple investment strategy where one takes a long position in a stock (i.e buys it) when the sentiment percent change value exceeds the *long* threshold and takes a short position in a stock (i.e. sells it short) when the sentiment percent change falls below the *short* threshold.  

### Credits
1) https://gist.github.com/madewitt/29bceb51c494ef9ea1d34f9474aa4b3c
2) https://github.com/weiwangchun/cs410
3) https://www.sec.gov/edgar/searchedgar/accessing-edgar-data.htm
