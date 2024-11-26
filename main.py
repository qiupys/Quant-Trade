import akshare as ak

# 当日上交所汇总信息
stock_sse_summary_df = ak.stock_sse_summary()
print(stock_sse_summary_df)

# 当日个股信息
# 参考信息
# 招商银行：600036
# 宇通客车：600066
# 中国核电：601985
# 浙江鼎力：603338
# 海信家电：000921
stock_individual_info_em_df = ak.stock_individual_info_em(symbol="600036")
print(stock_individual_info_em_df)

# 历史数据查询
# adjust：‘’ 不复权，‘qfq’ 前复权（保持现在价格不变，调整历史股价），‘hfq’ 后复权（保持历史价格不变，调整现价，一般用于量化策略研究）
# period='daily'; choice of {'daily', 'weekly', 'monthly'}
stock_zh_a_hist_df = ak.stock_zh_a_hist(symbol="600036", period="daily", start_date="20170101", end_date='20241122', adjust="qfq")
print(stock_zh_a_hist_df)

# 股票代码获取
stocks = ak.stock_info_sh_name_code()
print(stocks.head())

