class RecognitinonHistoryWorker:
    def __init__(self):
        with open('./source/data/recognitions.txt', 'r', encoding='utf-8') as f:
            self.recog_history = [[elem for elem in line.strip().split(';')] for line in f.readlines()]
            # [[name, date_time recognized, date_time saved image, camera index, 1 or 0], ...]

    
    def get_full(self, *args):
        '''
        Arguments:
            *args: a list of integers, representing an element index.\n
            (0) name, (1) date_time recognized, (2) date_time saved image, (3) camera index, (4) 1 or 0
        >>> get_full(0, 3, 4)
        >>> [[name(0), camera index(3), 1 or 0(4)], ...]

        '''