from pyecharts import options as opts
from pyecharts.charts import Kline

# 准备数据
data = [
    [2320.26, 2320.26, 2287.3, 2362.94],
    [2300, 2291.3, 2288.26, 2308.38],
    [2295.35, 2346.5, 2295.35, 2345.92],
    [2347.22, 2358.98, 2337.35, 2363.8],
    # ... more data
]

# 配置 Kline 图
kline = (
    Kline()
    .add_xaxis(xaxis_data=["2017-10-24", "2017-10-25", "2017-10-26", "2017-10-27"])
    .add_yaxis(series_name="Kline", y_axis=data)
    .set_global_opts(
        xaxis_opts=opts.AxisOpts(is_scale=True),
        yaxis_opts=opts.AxisOpts(is_scale=True),
        title_opts=opts.TitleOpts(title="Kline 示例"),
    )
)

# 渲染图表
kline.render("kline_chart.html")
