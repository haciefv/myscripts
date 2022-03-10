from os import path

class TXTfile:

    def __init__(self, path: str, count_str: int = 10):
        self.path = path
        self.count_str = count_str

    def get_data(self):
        lst = []
        with open(self.path) as file1:
           for line in file1:
               lst.append(line)
        return lst

    def count_lines(self):
        try:
            with open(self.path) as fl:
                return len(fl.readlines())
        except Exception:
            return 0

    def print_file(self):
        lines = self.count_lines()
        if lines < 1:
            raise TXTfile ('The file is empty.')
        name_type = self.get_name_and_type()

        new_file= open(name_type[0]+f'_res{name_type[1]}','w+')



        data = self.get_data()
        count = 0

        for line in range(0, len(data)):
            if line != 0:
                count += 1
            if count <= self.count_str:
                new_file.write(data[line])
        new_file.close()


    def get_name_and_type(self):
        full_name = path.basename(self.path)
        name_type = path.splitext(full_name)
        return name_type



p = 'C:\\Users\\Friday\\Desktop\\myscripts\\self_education\\level 1\\OOP\\check\\1.txt'
file = TXTfile(p,2)
file.print_file()


