from datetime import datetime, timedelta

import pandas as pd
from pyecharts import options as opts
from pyecharts.charts import Line

# 设置茅台股票代码
stock_code = "600519.SS"

# 获取当前日期
end_date = datetime.now().strftime('%Y-%m-%d')

# 计算三年前的日期
start_date = (datetime.now() - timedelta(days=3 * 365)).strftime('%Y-%m-%d')

# 使用yfinance获取股票数据
df = pd.read_csv('E:/code/binance/data/BTCUSDT_15MIN.csv')

# 提取数据中的日期和收盘价
dates = df['start_time'].values.tolist()
closing_prices = df['close'].values.tolist()

# 创建 Line 图表
line_chart = Line()
line_chart.add_xaxis(xaxis_data=dates)
line_chart.add_yaxis(series_name="茅台股价走势",
                     y_axis=closing_prices
                     # ,
                     # markline_opts=opts.MarkLineOpts(
                     #     data=[opts.MarkLineItem(type_="average", name="平均值")]
                     # )
                     )
line_chart.set_global_opts(
    title_opts=opts.TitleOpts(title="茅台股价走势图（近三年）"),
    xaxis_opts=opts.AxisOpts(type_="category"),
    yaxis_opts=opts.AxisOpts(is_scale=True),
    datazoom_opts=[
        opts.DataZoomOpts(
            pos_bottom="-2%",
            range_start=0,
            range_end=100,
            type_="inside"
        ),
        opts.DataZoomOpts(
            pos_bottom="-2%",
            range_start=0,
            range_end=100,
            type_="slider",
        ),
    ],
    toolbox_opts=opts.ToolboxOpts(
        feature={
            "dataZoom": {"yAxisIndex": "none"},
            "restore": {},
            "saveAsImage": {},
        }
    ),
)

# 渲染图表
line_chart.render("maotai_stock_trend_chart2.html")
