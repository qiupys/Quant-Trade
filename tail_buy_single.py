import argparse
from datetime import datetime

import backtrader as bt

from utils import preprocess
from strategy import TailBuy

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', default="600036", type=str, help='stock code')
    parser.add_argument('--start_date', default="20240101", help='start date of back test')
    parser.add_argument('--end_date', default='today', type=str, help='choose end date of back test')
    args = parser.parse_args()
    
    cerebro = bt.Cerebro()  # 初始化回测系统
    cerebro.addstrategy(TailBuy, printlog=True)  # 将交易策略加载到回测系统中
    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='tradeanalyzer')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')

    start_cash = 100000
    cerebro.broker.setcash(start_cash)  # 设置初始资本为 100000
    cerebro.broker.setcommission(commission=0.002)  # 设置交易手续费为 0.2%

    date_format = "%Y%m%d"
    start_date = datetime.strptime(args.start_date, date_format)
    if args.end_date == "today": 
        end_date = datetime.today()
    else:
        end_date = datetime.strptime(args.start_date, date_format)
    stock_df = preprocess(symbol=args.symbol, adjust="qfq", start_date=start_date.strftime("%Y%m%d"), end_date=end_date.strftime("%Y%m%d"))
    if stock_df is None:
        exit()
    data = bt.feeds.PandasData(dataname=stock_df, fromdate=start_date, todate=end_date)  # 加载数据
    cerebro.adddata(data)  # 将数据传入回测系统

    results = cerebro.run()  # 运行回测系统
    strategy_stats = results[0]

    # 获取分析结果
    port_value = cerebro.broker.getvalue()  # 获取回测结束后的总资金
    cash = cerebro.broker.getcash()
    pnl = port_value - start_cash  # 盈亏统计
    sharpe = strategy_stats.analyzers.sharpe.get_analysis()
    drawdown = strategy_stats.analyzers.drawdown.get_analysis()
    trade_stats = strategy_stats.analyzers.tradeanalyzer.get_analysis()
    returns = strategy_stats.analyzers.returns.get_analysis()

    print(f"回测期间: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    print(f"初始资金: {start_cash}")
    print(f"总资金: {port_value:.2f}, 含现金 {cash:.2f}")
    print(f"净收益: {pnl:.2f}")
    print(f"夏普比率: {sharpe['sharperatio']:.4f}" if sharpe['sharperatio'] is not None else "夏普比率: 无法计算 (None)")
    print(f"最大回撤: {drawdown.max.drawdown:.2f}%")
    print(f"总交易数: {trade_stats.total.total}")
    print(f"胜率: {trade_stats.won.total / trade_stats.total.total * 100:.2f}% " if trade_stats.won.total else "胜率: 无法计算 (None)")
    print(f"年化收益率: {returns['rnorm100']:.2f}%")        