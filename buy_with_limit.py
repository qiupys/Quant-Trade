import argparse
from datetime import datetime, timedelta

import backtrader as bt
from backtrader import Order

from utils import preprocess


class LimitBuy(bt.Strategy):
    """
    主策略程序
    """

    params = (("printlog", False), ("rebound_ratio", 0.005), ("stop_profit_ratio", 0.05))

    def __init__(self):
        """
        初始化函数
        """
        self.last_buy_price = []
        self.last_position_price = []
        
    def next(self):
        # 开仓条件和买入条件
        open_condition = (
            not self.position and self.data.low[0] <= self.data.open[0] * 0.97
        )
        buy_condition = (self.broker.cash >= self.data.low[0] * (1 + self.params.rebound_ratio) * 100
            and self.last_buy_price[-1] * 0.97 >= 
            self.data.low[0] * (1 + self.params.rebound_ratio)
        ) if self.last_buy_price else None
        if open_condition:
            # 尾盘买入：在当天收盘价买入一手
            self.buy(size=100)
            return
        if buy_condition:
            # 尾盘买入：在当天收盘价买入一手
            self.buy(
                exectype=Order.Limit,
                price=self.data.low[0] * (1 + self.params.rebound_ratio),
                size=100,
                valid = self.data.datetime.date(0) + timedelta(days=1)
            )
            return
        if self.position.size >= 100:
            # 检查是否达到预期涨幅或止损点
            stop_grid_profit_condition = self.data.high[0] >= self.last_buy_price[-1] * (
                1 + self.params.stop_profit_ratio
            ) if self.last_buy_price else None
            stop_profit_condition = self.data.high[0] >= self.position.price * (
                1 + self.params.stop_profit_ratio
            )
            # stop_loss_condition = self.data.close[0] < self.position.price * 0.7
            if stop_grid_profit_condition:
                self.sell(
                    exectype=Order.Limit,
                    price=self.last_buy_price[-1] * (1 + self.params.stop_profit_ratio),
                    size=100,
                    valid = self.data.datetime.date(0) + timedelta(days=1)
                )
                return
            if stop_profit_condition:
                self.sell(
                    exectype=Order.Limit,
                    price=self.position.price * (1 + self.params.stop_profit_ratio),
                    size=self.position.size,
                    valid = self.data.datetime.date(0) + timedelta(days=1)
                )
                return

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # 订单提交/接受状态，无需处理
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f"买单执行 @ {order.executed.price:.2f}, 当前成本 {self.position.price:.2f}, 持股数量 {self.position.size}"
                )
                self.last_buy_price.append(order.executed.price)
                self.last_position_price.append(self.position.price)
            elif order.issell():
                if order.executed.size == -100:
                    self.last_buy_price.pop()
                    self.last_position_price.pop()
                    self.position.price = self.last_position_price[-1] if self.last_position_price else 0
                elif order.executed.size < -100:
                    self.last_buy_price.clear()
                    self.last_position_price.clear()
                self.log(f"卖单执行 @ {order.executed.price:.2f}, 当前成本 {self.position.price:.2f}, 持股数量 {self.position.size}")
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log("订单取消/保证金不足/被拒绝")

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        self.log(f"盈利 {trade.pnl:.2f}, 现金 {self.broker.cash:.2f}")

    # def notify_cashvalue(self, cash, value):
    #     print(f"Notification - Cash: {cash:.2f}, Portfolio Value: {value:.2f}")

    def log(self, txt, dt=None):
        """日志记录函数"""
        if self.params.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f"{dt.isoformat()} {txt}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="600036", type=str, help="stock code")
    parser.add_argument(
        "--start_date", default="20140101", help="start date of back test"
    )
    parser.add_argument(
        "--end_date", default="today", type=str, help="choose end date of back test"
    )
    args = parser.parse_args()

    cerebro = bt.Cerebro()  # 初始化回测系统
    cerebro.addstrategy(LimitBuy, printlog=True)  # 将交易策略加载到回测系统中
    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe")
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="tradeanalyzer")
    cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")

    start_cash = 100000
    cerebro.broker.setcash(start_cash)  # 设置初始资本为 100000
    cerebro.broker.setcommission(commission=0.002)  # 设置交易手续费为 0.2%

    date_format = "%Y%m%d"
    start_date = datetime.strptime(args.start_date, date_format)
    if args.end_date == "today":
        end_date = datetime.today()
    else:
        end_date = datetime.strptime(args.end_date, date_format)
    stock_df = preprocess(
        symbol=args.symbol,
        adjust="hfq",
        start_date=start_date.strftime("%Y%m%d"),
        end_date=end_date.strftime("%Y%m%d"),
    )
    if stock_df is None:
        exit()
    data = bt.feeds.PandasData(
        dataname=stock_df, fromdate=start_date, todate=end_date
    )  # 加载数据
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

    print(
        f"回测期间: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}"
    )
    print(f"初始资金: {start_cash}")
    print(f"总资金: {port_value:.2f}, 含现金 {cash:.2f}")
    print(f"净收益: {pnl:.2f}")
    print(
        f"夏普比率: {sharpe['sharperatio']:.4f}"
        if sharpe["sharperatio"] is not None
        else "夏普比率: 无法计算 (None)"
    )
    print(f"最大回撤: {drawdown.max.drawdown:.2f}%")
    print(f"总交易数: {trade_stats.total.total}")
    # 获取赢利交易总数，若不存在则为0
    won_total = trade_stats.get("won", {}).get("total", 0)
    # 获取总交易数，若不存在则为0
    total_total = trade_stats.get("total", {}).get("total", 0)
    if total_total > 0:
        win_rate = (won_total / total_total) * 100
        print(f"胜率: {win_rate:.2f}%")
    else:
        print("胜率: 无法计算 (None)")
    print(f"年化收益率: {returns['rnorm100']:.2f}%")
