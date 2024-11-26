from datetime import datetime

import backtrader as bt

from utils import preprocess


class MyStrategy(bt.Strategy):
    """
    主策略程序
    """
    params = (
        ('printlog', False),
    )

    def __init__(self):
        """
        初始化函数
        """
        # 记录最后一笔持仓的买入价格
        self.last_buy_price = None

    def next(self):
        # 开仓条件和买入条件
        open_condition = not self.position and self.data.low[0] <= self.data.open[0]*0.98
        buy_condition = self.data.low[0] <= self.data.close[0] <= self.position.price * 0.95 and self.broker.cash >= self.data.close[0]*100
        if open_condition or buy_condition:
            # 尾盘买入：在当天收盘价买入一手
            self.buy(size=100)
        else:
            # 检查是否达到预期涨幅或止损点
            stop_profit_condition = self.data.high[0] >= self.position.price * 1.05
            stop_loss_condition = self.data.close[0] < self.position.price * 0.8
            if stop_profit_condition or stop_loss_condition:
                self.sell(size=self.position.size)

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # 订单提交/接受状态，无需处理
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f'买单执行 @ {order.executed.price:.2f}, 当前成本 {self.position.price:.2f}'
                )
                self.last_buy_price = order.executed.price
            elif order.issell():
                self.log(
                    f'卖单执行 @ {order.executed.price:.2f}'
                )
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('订单取消/保证金不足/被拒绝')

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        self.log(f'盈利 {trade.pnl:.2f}, 现金 {self.broker.cash:.2f}')

    # def notify_cashvalue(self, cash, value):
    #     print(f"Notification - Cash: {cash:.2f}, Portfolio Value: {value:.2f}")

    def log(self, txt, dt=None):
        ''' 日志记录函数 '''
        if self.params.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()} {txt}')


if __name__ == '__main__':
    cerebro = bt.Cerebro()  # 初始化回测系统
    cerebro.addstrategy(MyStrategy, printlog=True)  # 将交易策略加载到回测系统中
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
    stock_df = preprocess(symbol="600036", adjust="qfq", start_date=start_date.strftime("%Y%m%d"), end_date=end_date.strftime("%Y%m%d"))
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
    print(f"夏普比率: {sharpe['sharperatio']:.4f}")
    print(f"最大回撤: {drawdown.max.drawdown:.2f}%")
    print(f"总交易数: {trade_stats.total.total}")
    print(f"胜率: {trade_stats.won.total / trade_stats.total.total * 100:.2f}%")
    print(f"年化收益率: {returns['rnorm100']:.2f}%")
    

    # plt.rcParams["axes.unicode_minus"] = False
    # cerebro.plot(style='candlestick')
    # plt.show()