import logging
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

from typing import Union

sns.set()


def plot_bar_chart(df: pd.DataFrame, chart_title: Union[str, None] = None, top: int = 10, plot_max: bool = True) -> None:
    """Plot a bar Chart with the top values from the dictionary

    Args:
        df (pd.DataFrame): DataFrame to be plotted
        chart_title (str, optional): label of the chart. Defaults to None
        top (int, optional): numbers of values to be in the chart. Defaults to 10
        plot_max (bool, optional): Flag to plot the 'total' which is just the total number of songs, just as a comparison between each value and the total
    """

    if plot_max:
        df = df.query("name != ''")[:top + 1]
    else:
        logging.info(f'Total number of songs: {df["number of songs"][0]}')
        df = df.query("name != ''")[1:top + 1]

    plt.figure(figsize=(15, 10))

    sns.color_palette('bright')

    sns.barplot(x='name', y='number of songs', data=df, label=chart_title)

    plt.xticks(
        rotation=45,
        horizontalalignment='right',
        fontweight='light',
        fontsize='x-large'
    )

    plt.show()
