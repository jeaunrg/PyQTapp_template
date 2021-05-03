import time
import random
from src.model.utils import protector


class Model():
    @protector
    def function1(self, minimum=0, maximum=100, sleep_time=2, insert_error=False):
        """
        this function is an example
        """
        time.sleep(sleep_time)
        if insert_error:
            raise ValueError("ceci est une erreur test")
        return random.randint(minimum, maximum)
