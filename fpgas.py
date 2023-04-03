import os.path
from types import SimpleNamespace

import subprocess


class FPGAs:
    def __init__(self):
        self.fpgas = []
        self.update()
        self.state = []

    def update(self):

        # get all
        output = subprocess.check_output("pnputil /enum-devices /class USB /connected").decode("utf-8").replace("\r\n",
                                                                                                                "\n")

        # process
        devices = []
        for device in output.split("\n\n")[1:-1]:
            lines = [line.split(':', 2)[1].strip() for line in device.split("\n")]
            devices.append(SimpleNamespace(
                id=lines[0],
                device_description=lines[1],
                status=lines[5],
            ))

        # filter
        fpgas = [device for device in devices if device.device_description == "USB Serial Converter A"]

        # modify
        prefix = len(os.path.commonprefix([fpga.id for fpga in fpgas]))
        suffix = len(os.path.commonprefix([fpga.id[::-1] for fpga in fpgas]))
        for fpga in fpgas:
            fpga.enabled = fpga.status in ["Started", "Iniciado", "Enabled"]
            fpga.name = fpga.id[prefix:-suffix] if len(fpgas) > 1 else fpga.id

        print("FPGAs found:")
        print("\n".join(map(str, fpgas)))
        self.fpgas = fpgas

    def enabled(self, i):
        return self.fpgas[i].enabled

    def allEnabled(self):
        return all(self.enabled(i) for i in self)

    def allDisabled(self):
        return all(not self.enabled(i) for i in self)

    def name(self, i, full=False):
        return self.fpgas[i].id if full else self.fpgas[i].name

    def enable(self, i):
        print("Enabling", self)
        print(subprocess.check_call(f"pnputil /enable-device {self.fpgas[i].id}"))
        self.fpgas[i].enabled = True

    def disable(self, i):
        print("Disabling", self)
        print(subprocess.check_call(f"pnputil /disable-device {self.fpgas[i].id}"))
        self.fpgas[i].enabled = False

    def disable_all(self):
        for i in self:
            self.disable(i)

    def enable_only(self, i):
        self.enable(i)
        for j in self:
            if j != i:
                self.disable(j)

    def save_state(self):
        self.state = [self.enabled(i) for i in self]

    def restore_state(self):
        for i, s in enumerate(self.state):
            self.enable(i) if s else self.disable(i)

    def __len__(self):
        return len(self.fpgas)

    def __iter__(self):
        return range(len(self)).__iter__()

    def __enter__(self):
        self.save_state()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.restore_state()
