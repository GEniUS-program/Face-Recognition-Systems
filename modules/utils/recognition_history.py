class RecognitinonHistoryWorker:
    def __init__(self):
        self.update_history()

    def get(self, name=None, is_suf_clearance=None, camera_index=None, date=None, is_img=None):
        self.update_history()
        args = {0: name, 3: is_suf_clearance, 4: camera_index, 1: date}
        output = self.recog_history
        if is_img is not None and is_img == '1':
            output = [line for line in output if 'placeholder-image.png' not in line[2]]
        elif is_img is not None and is_img == '0':
            output = [line for line in output if 'placeholder-image.png' in line[2]]
        for key, value in args.items():
            if value is not None:
                output = [line for line in output if value in line[key]]
        return output

    def search(self, search):
        return [line for line in self.recog_history if search in ''.join(line)]

    def update_history(self):
        with open('./source/data/recognition.txt', 'r', encoding='utf-8') as f:
            self.recog_history = [
                [elem for elem in line.strip().split(';')] for line in f.readlines()]
            # [[name, date_time recognized, saved image location, 1 or 0, camera index], ...]
