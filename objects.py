# -*- coding: utf-8 -*-
"""
Created on Thu Mar 27 07:59:02 2014
"""

import pandas as pd
import datetime as dt
from pandas.tseries.offsets import DateOffset

OriginOfTime = dt.datetime(2013,12,30)

class CashFlow(object):
    """Base CashFlow object, allowing for quicker & intuitive NPV and IRR calculations."""
    def __init__(self,CashFlowSeries):
        """Create a new CashFlow object, from another CashFlow object"""
        self.CFs = CashFlowSeries.copy()
        self.CropPastOrigin()
        self.SetDefaults()
    def CropPastOrigin(self):
        self.CFs = self.CFs[OriginOfTime:].resample(rule='A',how='sum')
    def SetDefaults(self,rate=0.1,threshold=0.05):
        self.DiscountRate = rate
        self.EqualityThreshold = threshold
    def NPV(self):
        temp = 0.0
        for i in range(len(self.CFs)-1,0,-1):
            temp = (temp + self.CFs[i]) / (1 + self.DiscountRate)
        return temp + self.CFs[0]
    def __add__(self,o):
        if type(o) in [float,int]:
            return CashFlow(self.CFs + o)
        else:
            return CashFlow(self.CFs.add(o.CFs,fill_value=0))
    def __mul__(self,o):
        if type(o) in [float,int]:
            return CashFlow(self.CFs * o)
        else:
            return CashFlow(self.CFs * o.CFs)
    def __div__(self,o):
        if type(o) in [float,int]:
            return CashFlow(self.CFs / o)
        else:
            return CashFlow(self.CFs / o.CFs)
    def __repr__(self):
        return "Cashflow NPV = " + str(self.NPV()) + " on " + str(self.CFs.index[0])
    def _basic_equality_check(self,o):
        if len(self.CFs) != len(o.CFs):
            print "Lengths not equal"
            return False

        if self.CFs.index[0] != o.CFs.index[0]:
            print "Start of CF is not on same date"
            return False

        if self.CFs.index[-1] != o.CFs.index[-1]:
            print "End of CF is not on same date"
            return False
        return True
    def __eq__(self,o):
        #TODO : Check for trailing or leading CFs of zero or marginal value.
        
        if not self._basic_equality_check(o):
            return False

        Merged = self.CFs / o.CFs
        
        for value in Merged.values:
            if value > (1.0 + self.EqualityThreshold):
                print "Found a CF that is greater than threshold."
                return False
            if value < (1.0 - self.EqualityThreshold):
                print "Found a CF that is less than than threshold."
                return False
        return True
    def __mod__(self,o):
        if not self._basic_equality_check(o):
            return False

        Merged = self.CFs / o.CFs        
        
        MaxScale = max(Merged)
        MinScale = min(Merged)
        
        MidPointScale = ((MaxScale + MinScale) / 2.0)
        
        if ((MaxScale - MinScale) / MidPointScale) < (self.EqualityThreshold * 2.0):
            return True
        else:
            return False
    def SwitchSign(self):
        self.CFs = self.CFs * -1.0

class CashFlowFirstPrinciples(CashFlow):
    """
    Create a CashFlow object from a list of dates and values.
    """
    def __init__(self,dates,values):
        """
        Create a CashFlow object from a list of dates and values.
        """
        self.CFs = pd.Series(index=pd.to_datetime(dates),data=values)
        self.CFs = self.CFs.resample('A',how='sum')
        self.CropPastOrigin()
        self.SetDefaults()

class CashFlowFromSeries(CashFlow):
    def __init__(self,PandasSeries):
        """
        Create a CashFlow object from a Pandas.Series object
        """
        self.CFs = PandasSeries.copy(deep=True)
        self.CFs = self.CFs.resample('A',how='sum')
        self.CropPastOrigin()
        self.SetDefaults()
        
class DividendInstrument(CashFlow):
    def __init__(self,DividendRate,ScaleBy=1.0,TerminalMaturity=30):
        """
        Create a CashFlow object by specifying a Dividend Rate, an optional scaler, and number of years
        to simulate a "terminal" year.  Defaults to 30.
        """
        rng = pd.date_range(OriginOfTime, periods=TerminalMaturity, freq='A',normalize=True)
        self.CFs = pd.Series(index=rng,data=[DividendRate]*30)
        self.CFs[-1] = 1.0 + DividendRate
        self.CFs = self.CFs * ScaleBy
        self.SetDefaults()

class CouponInstrument(CashFlow):
    def __init__(self,CouponRate,Maturity,N=2,ScaleBy=1.0):
        """
        Create a CashFlow object by specifying a Coupon (per coupon period), Maturity (date), number of periods per year (defaults to 2), and an optional scaler (defaults to 1.0)
        """    
        do = DateOffset(months=12/N)
        rng = pd.date_range(end=Maturity, periods=100*N, freq=do)
        self.CFs = pd.Series(index=rng,data=[CouponRate]*len(rng))
        self.CFs[-1] = 1.0 + CouponRate
        self.CropPastOrigin()
        self.CFs = self.CFs * ScaleBy
        self.SetDefaults()

class CashFlowSet(CashFlow):
    def __init__(self,DictOfCashFlowObjects,DictOfWeights):
        """
        Create a CashFlow object as an aggregation of one or more other cashflow objects.
        A dictionary of CashFlow objects and a corresponding dictionary of weights is required.
        """
        DictionaryOfCFs = {}
        for keys in DictOfCashFlowObjects.iterkeys():
            DictionaryOfCFs[keys] = DictOfCashFlowObjects[keys].CFs
        AllCFs = pd.DataFrame.from_dict(DictionaryOfCFs)
        WeightedCFs = AllCFs * pd.Series(DictOfWeights)
        self.CFs = WeightedCFs.sum(axis=1,skipna=True)
        self.SetDefaults()

if __name__ == '__main__':        
    Stock = DividendInstrument(0.025,ScaleBy=1000)
    Bond = CouponInstrument(0.025,dt.datetime(2024,3,14),ScaleBy=2000)

    Stock2 = DividendInstrument(0.025,ScaleBy=2000)
    Bond2 = CouponInstrument(0.025,dt.datetime(2024,3,14),ScaleBy=4000)

    Weights = {'Stock' : 0.4, 'Bond' : 0.6}
    Weights2 = {'Stock' : 0.402, 'Bond' : 0.598}
    
    CFs = {'Stock' : Stock, 'Bond' : Bond}
    CFs2 = {'Stock' : Stock2, 'Bond' : Bond2}
    
    Finished = CashFlowSet(CFs,Weights)
    Finished2 = CashFlowSet(CFs2,Weights2)
    print Finished % Finished2
