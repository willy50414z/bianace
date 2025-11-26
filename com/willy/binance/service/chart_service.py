from decimal import Decimal

import pandas as pd
from pandas import DataFrame
from pyecharts import options as opts
from pyecharts.charts import Line

from com.willy.binance.enums.trade_type import TradeType


def export_trade_point_chart(chart_name, df):
    # df = pd.read_csv('E:/code/binance/data/BTCUSDT_15MIN.csv')

    # 提取数据中的日期和收盘价
    date_list = df['start_time'].dt.strftime('%Y-%m-%d %H:%M:%S').tolist()
    # date_list = [(dt + relativedelta(**{"hours": 8})).strftime('%Y-%m-%d %H:%M:%S') for dt in date_list]
    close_list = df['close'].values.tolist()
    ma7_list = df["ma7"].values.tolist()
    ma25_list = df["ma25"].values.tolist()
    ma99_list = df["ma99"].values.tolist()

    buy_point_list = []
    sell_point_list = []
    stop_loss_point_list = []
    total_profit_list = []
    for row in df.itertuples(index=False):
        if not pd.isna(row.txn_detail):
            if row.txn_detail.trade_record.reason == "停損":
                stop_loss_point_list.append((row.start_time.strftime('%Y-%m-%d %H:%M:%S'), row.close, "STOP_LOSS"))
            else:
                if row.txn_detail.trade_record.type == TradeType.BUY:
                    buy_point_list.append((row.start_time.strftime('%Y-%m-%d %H:%M:%S'), row.close, "BUY"))
                else:
                    sell_point_list.append((row.start_time.strftime('%Y-%m-%d %H:%M:%S'), row.close, "SEll"))
            total_profit_list.append(row.txn_detail.total_profit)
        else:
            if len(total_profit_list) > 0:
                total_profit_list.append(total_profit_list[len(total_profit_list) - 1])
            else:
                total_profit_list.append(Decimal(0))

    line_chart = Line()
    line_chart.add_xaxis(xaxis_data=date_list)
    line_chart.add_yaxis(series_name="close", is_symbol_show=False,
                         y_axis=close_list, color='#000000', yaxis_index=0)
    line_chart.add_yaxis(series_name="ma7", is_symbol_show=False,
                         y_axis=ma7_list, color='#F19C38', yaxis_index=0)
    line_chart.add_yaxis(series_name="ma25", is_symbol_show=False,
                         y_axis=ma25_list, color='#EA3DF7', yaxis_index=0)
    line_chart.add_yaxis(series_name="ma99", is_symbol_show=False,
                         y_axis=ma99_list, color='#7A297B', yaxis_index=0)
    line_chart.add_yaxis(series_name="total_profit", is_symbol_show=False,
                         y_axis=total_profit_list, color='#138535', yaxis_index=1)
    line_chart.extend_axis(yaxis=opts.AxisOpts(type_="value", position="right"))
    line_chart.set_series_opts(
        markpoint_opts=opts.MarkPointOpts(
            data=[opts.MarkPointItem(name=f"{p[0]} {p[1]}", itemstyle_opts={"color": "#2EBD85"}, coord=[p[0], p[1]]) for
                  p in
                  buy_point_list]
                 + [opts.MarkPointItem(name=f"{p[0]} {p[1]}", itemstyle_opts={"color": "#F6465D"}, coord=[p[0], p[1]])
                    for p in
                    sell_point_list] + [
                     opts.MarkPointItem(name=f"{p[0]} {p[1]}", itemstyle_opts={"color": "#00A2E8"}, coord=[p[0], p[1]])
                     for p in
                     stop_loss_point_list]

        ))

    line_chart.set_global_opts(
        title_opts=opts.TitleOpts(title="ma_dca data"),
        xaxis_opts=opts.AxisOpts(type_="category"),
        yaxis_opts=opts.AxisOpts(type_="value", name="price", is_scale=True),
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
        tooltip_opts=opts.TooltipOpts(trigger="axis"),
        toolbox_opts=opts.ToolboxOpts(
            feature={
                "dataZoom": {"yAxisIndex": "none"},
                "restore": {},
                "saveAsImage": {},
            }
        ),
    )

    # line_chart.render(f"E:/code/binance/charts/{chart_name}.html")

    chart_html = line_chart.render_embed()

    # Convert DataFrame to HTML table
    txn_detail_df = df[df['txn_detail'].notna()][["start_time", "txn_detail"]]
    df2 = DataFrame()
    df2['date'] = txn_detail_df['txn_detail'].apply(lambda d: d.trade_record.date.strftime('%Y%m%d %H:%M:%S'))
    df2['units'] = txn_detail_df['txn_detail'].apply(lambda d: d.units)
    df2['price'] = txn_detail_df['txn_detail'].apply(lambda d: round(d.trade_record.price, 2))
    df2['profit'] = txn_detail_df['txn_detail'].apply(lambda d: d.profit)
    df2['total_profit'] = txn_detail_df['txn_detail'].apply(lambda d: d.total_profit)
    df2['reason'] = txn_detail_df['txn_detail'].apply(lambda d: d.trade_record.reason)
    table_html = df2.to_html(index=False, border=1)

    # Combine
    final_html = """
    <!DOCTYPE html>
    <meta charset="utf-8">
<html>
<head>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/echarts/5.4.0/echarts.min.js"></script>
    <style>
        /* 让 chart 和 table 在同一行 */
        .layout {
    display: flex;
            align-items: flex-start;
            justify-content: center;
            gap: 20px; /* 两边的间距，可以按需调整 */
        }

        /* chart 占据的宽度（可按需求调整） */
        .chart {
    width: 60%;   /* 例如占屏幕宽度的 60% */
            min-width: 300px;
        }

        /* 可滚动的表格容器 */
        .table-container {
    width: 40%;   /* 与 chart 相对 */
            min-width: 300px;
            max-height: 500px; /* 设定一个固定高度，超出就滚动 */
            overflow: auto;
            border: 1px solid #ddd;
        }

        /* 表格样式（保持原有样式） */
        table {margin: 0; border-collapse: collapse; width: 100%; }
        th, td {padding: 10px; text-align: left; border-bottom: 1px solid #eee; }
        /* 你原本的样式 */
        /* table {margin: 20px auto; border-collapse: collapse; }
           th, td {padding: 10px; text-align: left; } */
    </style>
</head>
<body>
    <div class="layout">
        <div class="chart" id="chart-container">
            """ + chart_html + """
        </div>

        <!-- 滚动表格区域 -->
        <div class="table-container" aria-label="滚动表格">
            """ + table_html + """
        </div>
    </div>
</body>
</html>
    """

    with open(f"E:/code/binance/charts/{chart_name}.html", "w", encoding="utf-8") as f:
        f.write(final_html)

    # line_chart2 = Line()
    # line_chart2.add_xaxis(xaxis_data=date_list)
    # line_chart2.add_yaxis(series_name="total_profit", is_symbol_show=False,
    #                       y_axis=total_profit_list, color='#000000')
    #
    # line_chart2.set_global_opts(
    #     title_opts=opts.TitleOpts(title="total_profit data"),
    #     xaxis_opts=opts.AxisOpts(type_="category"),
    #     yaxis_opts=opts.AxisOpts(is_scale=True),
    #     datazoom_opts=[
    #         opts.DataZoomOpts(
    #             pos_bottom="-2%",
    #             range_start=0,
    #             range_end=100,
    #             type_="inside"
    #         ),
    #         opts.DataZoomOpts(
    #             pos_bottom="-2%",
    #             range_start=0,
    #             range_end=100,
    #             type_="slider",
    #         ),
    #     ],
    #     toolbox_opts=opts.ToolboxOpts(
    #         feature={
    #             "dataZoom": {"yAxisIndex": "none"},
    #             "restore": {},
    #             "saveAsImage": {},
    #         }
    #     ),
    # )

    # grid = Grid()
    # grid.add(line_chart, grid_opts=opts.GridOpts(pos_left="5%", pos_right="55%", height="400px"))
    # grid.add(line_chart2, grid_opts=opts.GridOpts(pos_left="60%", pos_right="5%", height="400px"))
    #
    # # grid.set_global_opts(
    # #     title_opts=opts.TitleOpts(title="Two charts with shared X-axis"),
    # # )
    #
    # grid.render("two_charts_nested_grid.html")


#     line = (
#         Line()
#         .add_xaxis(date_list)
#         .add_yaxis("close", y_axis=close_list, symbol="emptyCircle", is_symbol_show=True)
#         # .add_yaxis("ma7", ma7_list, symbol="emptyCircle", is_symbol_show=True, color="#3470C6")
#         # .add_yaxis("ma25", ma25_list, symbol="emptyCircle", is_symbol_show=True, color="#5470C6")
#         # .set_series_opts(
#         #     markpoint_opts=opts.MarkPointOpts(
#         #         data=[opts.MarkPointItem(name="BUY", coord=[p[0], p[1]]) for p in buy_point_list] +
#         #              [opts.MarkPointItem(name="SELL", coord=[p[0], p[1]]) for p in sell_point_list]  # 依需求調整
#         #     )
#         #     # TODO color
#         # )
#         .set_global_opts(
#             title_opts=opts.TitleOpts(title="多折線 + 自訂標註點" if chart_name is None else chart_name),
#             xaxis_opts=opts.AxisOpts(type_="date"),
#             yaxis_opts=opts.AxisOpts(name="price")
#         )
#     )
#
#     line.render(f"E:/code/binance/charts/{chart_name}.html")
#
#
if __name__ == '__main__':
    export_trade_point_chart("xxx", None)
