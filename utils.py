import akshare as ak
import pandas as pd

def preprocess(symbol:str, adjust:str, start_date:str, end_date:str):
    # 利用 AKShare 获取股票的后复权数据，这里只获取前 7 列
    try:
        stock_df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust=adjust, start_date=start_date, end_date=end_date).iloc[:, :7]
        # 删除 `股票代码` 列
        del stock_df['股票代码']
        # 处理字段命名，以符合 Backtrader 的要求
        stock_df.columns = [
            'date',
            'open',
            'close',
            'high',
            'low',
            'volume',
        ]
        # 把 date 作为日期索引，以符合 Backtrader 的要求
        stock_df.index = pd.to_datetime(stock_df['date'])
        return stock_df
    except Exception as e:
        print(f"获取股票数据时出错: {e}")
        return None