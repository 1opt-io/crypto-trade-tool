# crypto-exchange-tool

币安ETH永续合约 1800usd-3600usd价格区间网格交易：

	•	基于现价，假设2700 ，高于此点做空，低于此点做多；

	•	1800-3600拆成100格，等比数列，监测币安成交价格，到达每个点时做出交易，高频网格交易，每个网格0.1 ETH；
2635.71    2656.973    2678.4    2700    2721.6    2743.3    2765.32    2787.42

	•	基本场景：2700开始，每分钟检测成交价格，下一分钟2660，市价买入0.1eth，下例：
 
 交易次序    	 检测市场成交价   		 操作
 
   1                2660                   call 0.1ETH
   2                2710                    put 0.1ETH
   3                2780                   PUT 0.3ETH
   4                2725                   call 0.1ETH

特殊情况：
	•	下单未成交，需识别后再次确认成交条件再下单
	•	实时确认仓位，做多或者空总仓位不超过10eth(防错)
	•	到达边际（1800或者3600时）停止运行
数据分析
	•	盈利分析：导出过去3-5年成交数据，以此方式交易的收益情况（币安交易费率按0.05%计算）
	•	更换变量（如调整网格密度，调整起始价格，调整读取成交价格的频率）来判断最佳策略
	•	对比一下对币安网格机器人是否有优势，币安机器人-挂单交易费率0.02%，币安机器人不追踪实时价格，提前在所有点位挂上买单和卖单，策略较为简单。

进阶
1急剧下跌和拉升识别：判断市场下跌和拉升情况，在急剧变化期不下单，在平台期成交
2自动转入转出保证金，保证仓位安全
3 数据分析进阶：复盘在上升和下降K线中，此交易策略在哪个位置盈利概率最大.
