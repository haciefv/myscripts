class RMass:

    def __init__(self, mass1: list, mass2: list):
        self.mass1 = mass1
        self.mass2 = mass2

    def r1(self):
        mass3 = []
        for item1 in self.mass1:
            found = False
            for item2 in self.mass2:
                if item1 == item2:
                    found = True

            if not found:
                mass3.append(item1)
        print('Реализация 1, без индексации: ', mass3)

    def r2(self):
        mass3 = []
        for item1 in range(0, len(self.mass1)):
            found = False
            for item2 in range(len(self.mass2)):
                if self.mass1[item1] == self.mass2[item2]:
                    found = True
            if not found:
                mass3.append(self.mass1[item1])
        print('Реализация 2, с индексацией: ', mass3)


ms1 = ["Alex", "Dima", "Kate", "Galina", "Ivan"]
ms2 = ["Dima", "Ivan", "Kate"]

rms = RMass(ms1, ms2)
rms.r1()
rms.r2()

