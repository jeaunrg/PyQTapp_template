import time
import random
from src.model.utils import protector
import pandas as pd


class Model():
    @protector
    def function1(self, minimum=0, maximum=100, sleep_time=2, insert_error=False):
        """
        this function is an example
        """
        time.sleep(sleep_time)
        if insert_error:
            raise ValueError("ceci est une erreur test")
        df = pd.DataFrame()
        df.loc['a', 1] = random.randint(minimum, maximum)
        df.loc['b', 2] = random.randint(minimum, maximum)
        return 68
