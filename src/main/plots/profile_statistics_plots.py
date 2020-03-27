# Copyright (c) 2020 Anastasiia Birillo, Elena Lyulina

import logging
from typing import Dict, Any

import pandas as pd
import plotly.express as px

from src.main.util import consts
from src.main.plots.util.plotly_util import save_plot
from src.main.util.log_util import log_and_raise_error
from src.main.util.file_util import get_parent_folder, deserialize_data_from_file
from src.main.plots.util.plots_common import to_filter_rare_values, get_readable_key
from src.main.plots.util.consts import PLOTTY_CATEGORY_ORDER, PLOT_TYPE, STATISTICS_FREQ, STATISTICS_SHOWING_KEY, \
    STATISTICS_KEY, STATISTICS_COLORS

log = logging.getLogger(consts.LOGGER_NAME)


def __read_statistics_from_file(path: str, default_value: consts.DEFAULT_VALUE) -> Dict[str, Any]:
    statistics_dict = deserialize_data_from_file(path)
    readable_statistics_dict = {}
    for key in statistics_dict.keys():
        readable_statistics_dict[get_readable_key(key, default_value)] = statistics_dict[key]
    return readable_statistics_dict


def __get_statistics_df_from_file(path: str, column: STATISTICS_KEY, default_value: consts.DEFAULT_VALUE,
                                  to_union_rare: bool = False) -> pd.DataFrame:
    statistics_dict = __read_statistics_from_file(path, default_value)
    statistics_df = pd.DataFrame(statistics_dict.items(), columns=[column.value, STATISTICS_FREQ])
    # If we want to union rare values
    if to_union_rare:
        statistics_df.loc[to_filter_rare_values(statistics_df), column.value] = STATISTICS_SHOWING_KEY.OTHERS.value
    return statistics_df


def __get_labels_for_plots(column: STATISTICS_KEY) -> Dict[str, str]:
    return {
        STATISTICS_FREQ: STATISTICS_SHOWING_KEY.FREQ.value,
        column.value: get_readable_key(column.value)
    }


def __get_title_for_plots(column: STATISTICS_KEY) -> str:
    return get_readable_key(column.value) + ' distribution'


def __plot_pie_chart(statistics_df: pd.DataFrame, title: str, path: str, column: STATISTICS_KEY,
                     labels: Dict[str, str], plot_name: str = 'distribution_plot',
                     format: consts.EXTENSION = consts.EXTENSION.HTML, auto_open: bool = False) -> None:
    fig = px.pie(statistics_df, values=STATISTICS_FREQ, names=column.value, title=title,
                 color_discrete_sequence=STATISTICS_COLORS.PIE_CHART.value,
                 hover_data=[STATISTICS_FREQ],
                 labels=labels)
    fig.update_traces(textposition='inside', textinfo='percent')
    save_plot(fig, path, PLOT_TYPE.PIE, plot_name, format, auto_open)


def __plot_bar_chart(statistics_df: pd.DataFrame, column: STATISTICS_KEY,
                     title: str, labels: Dict[str, str], path: str, plot_name: str = 'distribution_plot',
                     format: consts.EXTENSION = consts.EXTENSION.HTML, auto_open: bool = False,
                     x_category_order: PLOTTY_CATEGORY_ORDER = PLOTTY_CATEGORY_ORDER.TOTAL_ASCENDING) -> None:
    # x_category_order='total ascending' means: in order of increasing values in Y
    # x_category_order='category ascending' means: in order of increasing values in X
    fig = px.bar(statistics_df, x=column, y=STATISTICS_FREQ, title=title, labels=labels,
                 hover_data=[column.value, STATISTICS_FREQ])
    fig.update_layout(
        yaxis=dict(
            title_text=STATISTICS_SHOWING_KEY.FREQ.value
        ),
        xaxis=dict(
            title_text=get_readable_key(column.value),
            # We use type = 'category' because we want to display all values (numbers and strings)
            type='category',
            categoryorder=x_category_order.value
        ),
        plot_bgcolor=STATISTICS_COLORS.BAR_CHART_BG.value
    )
    fig.update_yaxes(automargin=True)
    save_plot(fig, path, PLOT_TYPE.BAR, plot_name, format, auto_open)


def plot_profile_statistics(file: str, column: STATISTICS_KEY, plot_type: PLOT_TYPE, to_union_rare: bool = False,
                            format: consts.EXTENSION = consts.EXTENSION.HTML, auto_open: bool = False,
                            x_category_order: PLOTTY_CATEGORY_ORDER = PLOTTY_CATEGORY_ORDER.TOTAL_ASCENDING) -> None:
    default_value = column.get_default()
    statistics_df = __get_statistics_df_from_file(file, column, default_value, to_union_rare)
    path = get_parent_folder(file)
    labels = __get_labels_for_plots(column)
    title = __get_title_for_plots(column)
    if plot_type == PLOT_TYPE.PIE:
        __plot_pie_chart(statistics_df, title, path, column, labels, plot_name=column.value, format=format,
                         auto_open=auto_open)
    elif plot_type == PLOT_TYPE.BAR:
        __plot_bar_chart(statistics_df, column, title, labels, path, plot_name=column.value, format=format,
                         auto_open=auto_open, x_category_order=x_category_order)
    else:
        log_and_raise_error(f'Plot type {plot_type} is incorrect!', log)