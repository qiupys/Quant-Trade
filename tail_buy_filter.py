from datetime import datetime

import akshare as ak
import backtrader as bt

from utils import preprocess
from strategy import TailBuy


if __name__ == '__main__':
    stocks = ak.stock_info_sh_name_code()
    ranks = dict()
    for symbol in stocks['证券代码'][:3000]:
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

        start_date = datetime(2014, 1, 1)  
        # end_date = datetime.today()
        end_date = datetime(2024, 1, 1)
        stock_df = preprocess(symbol=symbol, adjust="qfq", start_date=start_date.strftime("%Y%m%d"), end_date=end_date.strftime("%Y%m%d"))
        if stock_df is None:
            continue
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
        # 获取赢利交易总数，若不存在则为0
        won_total = trade_stats.get('won', {}).get('total', 0)
        # 获取总交易数，若不存在则为0
        total_total = trade_stats.get('total', {}).get('total', 0)
        if total_total > 0:
            win_rate = (won_total / total_total) * 100
            print(f"胜率: {win_rate:.2f}%")
        else:
            print("胜率: 无法计算 (None)")
        print(f"年化收益率: {returns['rnorm100']:.2f}%")
        
        ranks[symbol] = returns['rnorm100']
        # plt.rcParams["axes.unicode_minus"] = False
        # cerebro.plot(style='candlestick')
        # plt.show()
    
    print("该策略的合适标的为如下十只股票:")
    sorted_items = sorted(ranks.items(), key=lambda item: item[1], reverse=True)
    # 打印前10项
    for i, (key, value) in enumerate(sorted_items[:10], start=1):
        print(f"{i}. {key}: {value:.2f}")