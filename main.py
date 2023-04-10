import os
import subprocess

from UI import UI
from admin import run_as_admin
from fpgas import FPGAs
from vivado import Vivado


def main():
    # init
    vivado = Vivado()
    fpgas = FPGAs()

    class CustomUI(UI):
        def __init__(self):
            super().__init__()

            # do nothing
            self.refresh = lambda: None
            self.autoRefresh = lambda: None
            self.bitstream = lambda: None
            self.preScript = lambda: None
            self.postScript = lambda: None

        # def utils
        def do_program(self):
            preScript = self.get_value('preScript')
            if preScript != '':
                subprocess.call(preScript)
            vivado.program(self.get_value('bitstream'))
            postScript = self.get_value('postScript')
            if postScript != '':
                subprocess.call(postScript)

        def enableAll(self):
            def f():
                for i in fpgas:
                    self.step(f"Enabling board {i + 1}")
                    fpgas.enable(i)

            self.background(f, len(fpgas))

        def disableAll(self):
            def f():
                for i in fpgas:
                    self.step(f"Disabling board {i + 1}")
                    fpgas.disable(i)

            self.background(f, len(fpgas))

        def programAll(self):
            def f():
                with fpgas:
                    for i in fpgas:
                        self.step(f"Enabling board {i + 1}")
                        fpgas.enable(i)
                        for j in fpgas:
                            if j != i:
                                self.step(f"Disabling board {j + 1}")
                                fpgas.disable(j)
                        if i == 0:
                            self.step("Initializing Vivado")
                            vivado.prepare()
                        self.step(f"Programming board {i + 1}")
                        self.do_program()

            self.background(f, 1 + len(fpgas) * (2 + len(fpgas) - 1))

        def toggle(self, i):
            def f(i):
                if fpgas.enabled(i):
                    self.step("Disabling")
                    fpgas.disable(i)
                else:
                    self.step("Enabling")
                    fpgas.enable(i)

            self.background(lambda: f(int(i)), 1)

        def enableOnly(self, i):
            def f(i):
                self.step("Enabling board")
                fpgas.enable(i)
                for j in fpgas:
                    if j != i:
                        self.step(f"Disabling board {j + 1}")
                        fpgas.disable(j)

            self.background(lambda: f(int(i)), len(fpgas))

        def program(self, i):
            def f(i):
                with fpgas:
                    self.step("Enabling board")
                    fpgas.enable(i)
                    for j in fpgas:
                        if j != i:
                            self.step(f"Disabling board {j + 1}")
                            fpgas.disable(j)
                    self.step("Initializing Vivado")
                    vivado.prepare()
                    self.step("Programming board")
                    self.do_program()


            self.background(lambda: f(int(i)), len(fpgas) + 3)

    ui = CustomUI()

    # loop
    while ui.is_shown():
        # update
        fpgas.update()
        ui.update(fpgas)

        # tick
        ui.tick()


@run_as_admin
def main_admin():
    try:
        main()
    except Exception as e:
        print("An exception ocurred:")
        print(e)
        input("Press enter to exit")


if __name__ == '__main__':
    if 'no_admin' in os.environ:
        main()
    else:
        main_admin()
