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
As expected, while the changes in the sentiment of company's filings had some impact on the future stock returns, this impact was insufficient for building a viable investment strategy.

### Documented Source Code
The Python script **demo.py** 
1) Downloads 10-Q and 10-K SEC filings for selected companies. **Ticker**, **CIK** and **Company** (company name) should be provided, for each company one is interested in, in the input file **/investment_universe/tickers_and_ciks.csv** (Note that the input file for the demo contains this data for two companies - McDonalds Corp. and Apple Inc.) **Ticker** is used to load the historical company's stock prices to backtest investment strategy while **CIK** (the Central Index Key) is required to download company's filings from SEC's EDGAR database.  
2) Calculates term frequency for each filing,
3) Estimates sentiment scores (Positive, Negative, Uncertain and Litigious) for each report,
4) Loads company's stock prices and calculates weekly, quarterly and yearly 
   forward returns, starting from the filing date (+ execution_lag_days to mitigate a look-ahead bias via simulation of a more realistic and conservative scenario where the stocks were purchased/sold on the next business day after the filing date).
5) Combines together sentiment scores and foward returns, calculates returns of investment strategies and saves the results in **/results/Investment strategies results.csv**

### Demo (Video)
The video with demonstration of demo.py and the output can be found [here](www.youtube.com)
