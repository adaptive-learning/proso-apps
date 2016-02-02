from datetime import datetime, timedelta
import os
import pandas as pd
import pylab as plt
import seaborn as snb

snb.set_style()


def answers(directory):
    df = pd.read_csv(os.path.join(directory, "proso_models_answer.csv"), parse_dates=["time"])
    df.set_index("time", inplace=True)
    df["correct"] = df["item_asked"] == df["item_answered"]
    return df


def answer_count_all(df):
    fig = plt.figure()
    df.groupby(lambda t: (t.year, t.month)).size().plot(rot=70)
    plt.ylabel("Answers")
    plt.title("Total answer count per month")
    return fig


def answer_count_last_month(df):
    fig = plt.figure()
    from_date = datetime.now() - timedelta(days=30)
    if df.index.max() < from_date:
        return None
    df[df.index >= from_date].groupby(lambda t: (t.year, t.month, t.day)).size().plot(rot=90)
    plt.ylabel("Answers")
    plt.title("Total answer count per day in last 30 days")
    return fig


def answer_distribution_in_week(df):
    fig = plt.figure()
    df.groupby(lambda t: t.dayofweek).size().plot()
    plt.ylabel("Answers")
    plt.title("Answer distribution in week")
    plt.xticks(list(range(7)), ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"])
    plt.ylim(0)
    return fig


def answer_distribution_in_day(df):
    fig = plt.figure()
    df.groupby(lambda t: t.hour).size().plot()
    plt.ylabel("Answers")
    plt.xlabel("Hour")
    plt.title("Answer distribution in day")
    plt.ylim(0)
    return fig


def response_time_distribution(df):
    fig = plt.figure()
    (df["response_time"] / 1000).hist(bins=60, range=(0, 20))
    plt.title("Response time distribution")
    plt.xlabel("Seconds")
    return fig


def success_rate(df):
    fig = plt.figure()
    df.groupby(lambda t: (t.year, t.month, t.day))["correct"].mean().plot(rot=70)
    plt.title("Success rate")
    plt.ylabel("Success rate")
    return fig

DS2A_MAP = {
    answers: [
        answer_count_all,
        answer_count_last_month,
        answer_distribution_in_week,
        answer_distribution_in_day,
        response_time_distribution,
        success_rate,
    ],
}
