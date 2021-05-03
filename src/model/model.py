import time
from src.model.utils import protector
import pandas as pd
import numpy as np


class Model():
    @protector
    def function1(self, minimum=0, maximum=100, sleep_time=2, insert_error=False):
        """
        this function is an example
        """
        time.sleep(sleep_time)
        if insert_error:
            raise ValueError("ceci est une erreur test")
        size = (100, 100)
        df = pd.DataFrame(index=np.arange(0, size[0]),
                          columns=np.arange(0, size[1]),
                          data=np.random.rand(*size)*10)
        return df
