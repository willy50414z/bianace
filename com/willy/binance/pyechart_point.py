from pyecharts import options as opts
from pyecharts.charts import Line

x_data = ["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04", "2025-01-05"]
y1 = [10, 12, 11, 13, 12]
y2 = [8, 9, 7, 10, 9]

# 自定義買入/賣出點，示意用
points_y1 = [("2025-01-02", 12, "Buy A"), ("2025-01-04", 13, "Sell A"), ("2025-01-05", 12, "Sell A")]
points_y2 = [("2025-01-03", 11, "Buy B"), ("2025-01-05", 9, "Sell B")]

line = (
    Line()
    .add_xaxis(x_data)
    .add_yaxis("數據 A", y1, symbol="emptyCircle", is_symbol_show=True)
    .add_yaxis("數據 B", y2, symbol="emptyCircle", is_symbol_show=True, color="#3470C6")
    .set_series_opts(
        markpoint_opts=opts.MarkPointOpts(
            data=[opts.MarkPointItem(name="Buy A", coord=[p[0], p[1]]) for p in points_y1] +
                 [opts.MarkPointItem(name="Sell A", coord=[p[0], p[1]]) for p in points_y1[0:1]]  # 依需求調整
        ),
        # TODO color
    )
    .set_global_opts(
        title_opts=opts.TitleOpts(title="多折線 + 自訂標註點"),
        xaxis_opts=opts.AxisOpts(type_="category"),
        yaxis_opts=opts.AxisOpts(name="價格")
    )
)

line.render("multi_line_with_points.html")
