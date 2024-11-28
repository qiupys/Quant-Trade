import argparse
from collections import deque
from datetime import datetime, timedelta

import backtrader as bt

from utils import preprocess


class LimitBuy(bt.Strategy):
    """
    优化后的主策略程序
    """
    
    params = (
        ("printlog", False),
        ("open_ratio", 0.03),
        ("grid_ratio", 0.05),
        ("stop_profit_ratio", 0.05),
        ("order_size", 100),  # 新增参数：订单大小
        ("valid_days", 1),  # 订单有效天数
    )

    def __init__(self):
        """
        初始化函数
        """
        self.last_buy_price = deque(maxlen=10)  # 限制最大长度，防止内存增长
        self.last_position_price = deque(maxlen=10)
        self.order = None  # 当前订单
        self.stop_order = None  # 当前止损订单

    def next(self):
        # 检查是否有挂单
        if self.order:
            return  # 订单尚未完成
        
        # 开仓条件：无持仓且当日最低价跌破开盘价95%
        if self.position.size == 0:
            open_price = self.data.open[0] * (1 - self.params.open_ratio)
            if self.data.low[0] <= open_price:
                self.log(f"尝试以限价 {open_price:.2f} 买入 {self.params.order_size} 股")
                self.order = self.buy(
                    exectype=bt.Order.Limit,
                    price=open_price,
                    size=self.params.order_size,
                    valid=self.data.datetime.datetime(0) + timedelta(days=self.params.valid_days)
                )
                return

        # 持仓情况下的策略
        if self.position.size > 0:
            high_price = self.data.high[0]
            low_price = self.data.low[0]
            entry_price = self.position.price

            # 止盈条件
            target_profit_price = entry_price * (1 + self.params.stop_profit_ratio)
            if high_price >= target_profit_price:
                self.log(f"达到止盈条件，最高价格 {high_price:.2f} >= 止盈价 {target_profit_price:.2f}")
                self.order = self.sell(
                    exectype=bt.Order.Limit,
                    price=target_profit_price,
                    size=self.position.size,
                    valid=self.data.datetime.datetime(0) + timedelta(days=self.params.valid_days)
                )
                return

            # 网格止盈条件
            if self.last_buy_price and high_price >= self.last_buy_price[-1] * (1 + self.params.grid_ratio):
                sell_price = self.last_buy_price[-1] * (1 + self.params.grid_ratio)
                self.log(f"触发网格减仓，尝试以限价 {sell_price:.2f} 卖出 {self.params.order_size} 股")
                self.order = self.sell(
                    exectype=bt.Order.Limit,
                    price=sell_price,
                    size=self.params.order_size,
                    valid=self.data.datetime.datetime(0) + timedelta(days=self.params.valid_days)
                )
                return
                
            # 网格加仓条件
            target_add_price = self.last_buy_price[-1] * (1 - self.params.grid_ratio)
            if self.last_buy_price and low_price <= self.last_buy_price[-1] * (1 - self.params.grid_ratio):
                if self.broker.cash >= target_add_price * self.params.order_size:
                    self.log(f"触发网格加仓，尝试以限价 {target_add_price:.2f} 买入 {self.params.order_size} 股")
                    self.order = self.buy(
                        exectype=bt.Order.Limit,
                        price=target_add_price,
                        size=self.params.order_size,
                        valid=self.data.datetime.datetime(0) + timedelta(days=self.params.valid_days)
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
                if order.executed.size == -self.params.order_size:
                    # 清除相应的网格记录
                    if self.last_buy_price:
                        self.last_buy_price.pop()
                    if self.last_position_price:
                        self.last_position_price.pop()
                else:
                    # 清除相应的买入记录
                    if self.last_buy_price:
                        self.last_buy_price.clear()
                    if self.last_position_price:
                        self.last_position_price.clear()
                self.position.price = self.last_position_price[-1] if self.last_position_price else 0
                self.log(
                    f"卖单执行 @ {order.executed.price:.2f}, 当前成本 {self.position.price:.2f}, 持股数量 {self.position.size}"
                )   
            self.order = None  # 重置当前订单
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log("订单取消/保证金不足/被拒绝")
            self.order = None  # 重置当前订单
        
        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        self.log(f"盈利 {trade.pnl:.2f}, 现金 {self.broker.cash:.2f}")

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
