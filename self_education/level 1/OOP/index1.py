import fnmatch
import os


class SFile:

    def __init__(self, path: str, type: str):
        self.path = path
        self.type = type

    def list_of_file(self) -> list:
        """
        :return: list of files from the path
        """
        return [os.path.join(self.path, x) for x in os.listdir(self.path)]

    def collect_type(self) -> list:
        """
        find in list if files , the file with enter type
        and collect it in list
        :return: list of file with enter type
        """

        dir_list = self.list_of_file()
        your_files = []

        for filename in fnmatch.filter(dir_list, self.type):
            your_files.append(filename)

        if not your_files:
            raise Exception(f'No Found files with the type {type}')

        return your_files

    def fast_created_file(self) -> str:
        list_of_files = self.collect_type()
        date_list = [[x, os.path.getctime(x)] for x in list_of_files]
        # Отсортируем список по дате создания в обратном порядке
        sort_date_list = sorted(date_list, key=lambda x: x[1], reverse=True)
        # Выведем первый элемент списка. Он и будет самым последним по дате
        return sort_date_list[0][0]

    def other_files(self) -> list:
        # получаем список файлов с дир по определенному типу
        list_of_files = self.collect_type()
        fast_created_file_name = self.fast_created_file()

        file_dt = 0
        dt_tensec = 10

        files = []
        for file in list_of_files:
            dictt = {}
            if file == fast_created_file_name:
                file_dt = round(os.path.getctime(file))
                continue
            dictt['path'] = file
            dictt['datetime'] = round(os.path.getctime(file))
            files.append(dictt)
        # print(files)

        difference = file_dt - dt_tensec
        last_files = []

        for item in files:
            if item['datetime'] >= difference and item['datetime'] <= file_dt:
                last_files.append(item['path'])
        print('Файл(ы) созданы после последнего файла, не позднее 10 сек:', end='\n')
        print(last_files)

# C:\Users\Friday\Desktop\myscripts\self_education\level 1\OOP\check
path = input('Введите путь к папке: ')
type = input('Введите тип искаемых файлов, например txt:')

File = SFile(path=path, type=f'*.{type}')
last_file = File.fast_created_file()

print("Последний созданый файл заданного типа: ", end='\n')
print(last_file)
File.other_files()
