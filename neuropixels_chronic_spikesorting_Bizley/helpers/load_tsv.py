### this is a wrapper on a csv reader that allows one to read some bombcell files.

import numpy as np
import pandas as pd
import os


def load_tsv(path):
    """
    Loadsa .tsv file as a numpy array, with the headers removed

    Parameters
    ----------
    path : str
        The path to the tsv to load

    Returns
    -------
    ndarray
        The tsv as a ndarray
    """
    df  = pd.read_csv(path, sep='\t', skiprows = 0)
    return df.values