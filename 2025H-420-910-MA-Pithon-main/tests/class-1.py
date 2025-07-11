class Person:
    def __init__(self, name):
        self.name = name

    def greet(self):
        print(self.name)

p = Person("Sébastien")
p.greet()
