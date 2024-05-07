from fastquant import get_stock_data
from hmmlearn import hmm
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import math
import time
from multiprocessing import Pool
import sys


class GmmHMM:
    def __init__(self,n_components,n_mix,algorithm,n_iter,d):
        self.n_components = n_components
        self.n_mix = n_mix
        self.algorithm = algorithm
        self.n_iter = n_iter
        self.d = d

        self.model = None
    
    def get_data(self, ticker, start_date, end_date):
        return get_stock_data(ticker, start_date, end_date)

    def data_prep(self, data):

        df = pd.DataFrame(data=None, columns=['fracChange','fracHigh','fracLow'])
        df['fracChange'] = (data['close']-data['open'])/data['open']
        df['fracHigh'] = (data['high']-data['open'])/data['open']
        df['fracLow'] = (data['open']-data['low'])/data['open']

        return df

    def plot_results(self, preds, actual, title):
        fig, ax = plt.subplots(figsize=(15,5))
        ax.set_title(title)
        time = range(len(preds))
        ax.plot(time,preds,color='tab:red',marker='s',markersize=2,linestyle='-',linewidth=1,label='forcast')
        ax.plot(time,actual,color='tab:blue',marker='s',markersize=2,linestyle='-',linewidth=1,label='actual')
        ax.set_xlabel('time')
        ax.set_ylabel('stock price ($)')
        ax.set_xticks(np.arange(0,len(preds)+10,10))
        ax.set_xlim(0,len(preds)+10)
        ax.xaxis.grid(True,ls='--')
        ax.yaxis.grid(True,ls='--')
        ax.legend()
        plt.savefig(f'../imgs/{title}.png')
    
    def mean_abs_percent_error(self, y_pred, y_true):
        return (1.0)/(len(y_pred))*((np.abs(y_pred-y_true)/np.abs(y_true))*100).sum()
    
    def train(self, train_data):
        train_obs = self.data_prep(train_data)
        self.model = hmm.GMMHMM(n_components=self.n_components,
                                n_mix=self.n_mix,
                                algorithm=self.algorithm,
                                n_iter=self.n_iter)

        self.model.fit(train_obs)

        return train_obs
    
    def log_lik_calc(self, observed, observations):
        log_liks = []
        for o in observations:
            obs = np.vstack((observed,o))
            log_lik = self.model.score(obs)
            log_liks.append((o,log_lik))

        return log_liks
    
    def test(self,test_data, train_obs):
        
        test_obs = self.data_prep(test_data)
        
        test_close_prices = test_data['close'].values
        
        open_price = test_data['open'][0]

        # use a latency of d days. So observations start as training data
        observed = train_obs.iloc[-self.d:].values
        
        # list to hold predictions
        preds = []
        
        # loop through all points we want to test
        for i in range(len(test_data)):
            # try 50x10x10 possible values for O_d+1
            change = np.arange(-0.1,0.1,0.2/50)
            high = np.arange(0,0.1,0.1/10)
            low = np.arange(0,0.1,0.1/10)

            observations = [np.array([c,h,l]) for l in low for h in high for c in change]
            
            # compute all log likelihoods w/ their observations in parallel
            jump = int(len(observations)/20)
            with Pool(processes=20) as pool:
                results = pool.starmap(self.log_lik_calc, [(observed, observations[i:i+jump]) for i in range(0,len(observations),jump)])

            best = {'obs':None, 'log_lik':-math.inf}
            for log_liks in results:
                for obs,log_lik in log_liks:
                    if log_lik > best['log_lik']:
                        best['obs'],best['log_lik'] = obs,log_lik

            # stack our prediction onto the observation list in attempt at true forecasting
            # drop the first thing in observed to shift our latency window `d`
            observed = np.vstack((observed,best['obs']))
            observed = observed[1:]

            #calculate the close value from best
            pred_close = best['obs'][0]*open_price+open_price
            preds.append(pred_close)

            # use next days open price as the predicted close
            open_price = pred_close

            print(f'{i+1}/{len(test_data)}',end='\r')
        print('DONE')
        return preds,test_close_prices
            

if __name__ == "__main__":
    # training with apple feb-10-2003 -> sep-10-2004
    # testing with apple sep-13-2004 -> jan-21-2005
    
    model = GmmHMM(n_components=4,
                   n_mix=5,
                   algorithm="map",
                   n_iter=100,
                   d=10)
    
    train_data = model.get_data(ticker='AAPL',start_date='2003-02-10',end_date='2004-09-10')
    test_data = model.get_data(ticker='AAPL',start_date='2004-09-13',end_date='2005-01-21')
    
    train_obs = model.train(train_data=train_data)

    start = time.time()
    preds,actual = model.test(test_data=test_data, train_obs=train_obs)
    end = time.time()
    print(f'model tested in {round((end-start)/60,2)} minutes')
    error = model.mean_abs_percent_error(y_pred=preds, y_true=actual)
    print(f'AAPL error: {error}')

    model.plot_results(preds=preds, actual=actual, 
                       title='GMM HMM True preds AAPL forcasted vs actual stock prices Sep 2004 - Jan 2005')
    
    # training with IBM feb-10-2003 -> sep-10-2004
    # testing with IBM sep-13-2004 -> jan-21-2005

    model = GmmHMM(n_components=4,
                   n_mix=5,
                   algorithm="map",
                   n_iter=100,
                   d=10)
    
    train_data = model.get_data(ticker='IBM',start_date='2003-02-10',end_date='2004-09-10')
    test_data = model.get_data(ticker='IBM',start_date='2004-09-13',end_date='2005-01-21')

    train_obs = model.train(train_data=train_data)

    start = time.time()
    preds,actual = model.test(test_data=test_data, train_obs=train_obs)
    end = time.time()
    print(f'model tested in {round((end-start)/60,2)} minutes')
    error = model.mean_abs_percent_error(y_pred=preds, y_true=actual)
    print(f'IBM error: {error}')

    model.plot_results(preds=preds, actual=actual, 
                       title='GMM HMM True preds IBM forcasted vs actual stock prices Sep 2004 - Jan 2005')