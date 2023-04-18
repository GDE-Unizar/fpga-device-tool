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

            # do nothing by default, override for custom
            self.refresh = lambda: None
            self.autoRefresh = lambda: None
            self.bitstream = lambda: None
            self.preScript = lambda: None
            self.postScript = lambda: None

        # def utils
        def do_program(self):
            preScript = self.get_value('preScript')
            if preScript != '':
                if self.get_value('prePrePause'):
                    self.wait("Paused before running pre-script")
                subprocess.call(preScript)
            if self.get_value('prePause'):
                self.wait("Paused before programming")
            vivado.program(self.get_value('bitstream'))
            if self.get_value('postPause'):
                self.wait("Paused after programming")
            postScript = self.get_value('postScript')
            if postScript != '':
                subprocess.call(postScript)
                if self.get_value('postPostPause'):
                    self.wait("Paused after running post-script")

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
                states = fpgas.get_state()
                for i in fpgas:
                    self.step(f"Enabling board {i + 1}")
                    fpgas.enable(i)
                    for j in fpgas:
                        if j != i:
                            self.step(f"Disabling board {j + 1}")
                            fpgas.disable(j)
                    if i == 0:
                        self.step("Initializing Vivado (may take a while)")
                        vivado.prepare()
                    self.step(f"Programming board {i + 1}")
                    self.do_program()
                for i, state in states:
                    self.step(f"Restoring {'enabled' if state else 'disabled'} board {i + 1}")
                    fpgas.toggle(i, state)

            self.background(f, len(fpgas) * (1 + (len(fpgas) - 1) + 1) + 1 + len(fpgas))

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

            self.background(lambda: f(int(i)), 1 + (len(fpgas) - 1))

        def program(self, i):
            def f(i):
                states = fpgas.get_state()
                self.step("Enabling board")
                fpgas.enable(i)
                for j in fpgas:
                    if j != i:
                        self.step(f"Disabling board {j + 1}")
                        fpgas.disable(j)
                self.step("Initializing Vivado (may take a while)")
                vivado.prepare()
                self.step("Programming board")
                self.do_program()

                for i, state in states:
                    self.step(f"Restoring {'enabled' if state else 'disabled'} board {i + 1}")
                    fpgas.toggle(i, state)

            self.background(lambda: f(int(i)), 1 + (len(fpgas) - 1) + 2 + len(fpgas))

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
