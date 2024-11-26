import backtrader as bt

class TailBuy(bt.Strategy):
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
                    f'买单执行 @ {order.executed.price:.2f}, 当前成本 {self.position.price:.2f}, 持股数量 {self.position.size}'
                )
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