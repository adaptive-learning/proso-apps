import os
import pandas as pd
import pylab as plt
import seaborn as snb

snb.set_style()


def users(directory):
    users = pd.read_csv(
        os.path.join(directory, "auth_user.csv"),
        index_col="date_joined",
        usecols=["id", "date_joined"],
        parse_dates=["date_joined"],
        )
    users = users.join(pd.read_csv(
        os.path.join(directory, "proso_user_userprofile.csv"), index_col="user"), on="id", rsuffix="_profile")
    return users


def new_user_count(df):
    fig = plt.figure()
    df.groupby(lambda t: (t.year, t.month)).size().plot(rot=70)
    plt.ylabel("Users")
    plt.title("New users")
    return fig


def registred_user_count(df):
    fig = plt.figure()
    df[(df["id_profile"].notnull())].groupby(lambda t: (t.year, t.month)).size().plot()
    plt.ylabel("Users")
    plt.title("Registred users")
    return fig

DS2A_MAP = {
    users: [
        new_user_count,
        registred_user_count,
    ],
}
