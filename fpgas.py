import os.path
import subprocess
from types import SimpleNamespace


class FPGAs:
    def __init__(self):
        self.fpgas = []
        self.update()
        self.state = []

    def update(self):
        """
        Updates the state of the fpgas
        """

        # get all
        output = subprocess.check_output(
            "pnputil /enum-devices /class USB /connected",
            universal_newlines=True
        )

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
            fpga.enabled = (
                True if fpga.status in ["Started", "Iniciado"]
                else False if fpga.status in ["Disabled", "Disabled"]
                else None
            )
            fpga.name = fpga.id[prefix:-suffix] if len(fpgas) > 1 else fpga.id

        # log
        print("FPGAs found:")
        for fpga in fpgas:
            print(">", fpga)
        self.fpgas = fpgas

    def enabled(self, i):
        """
        returns true if board 'i' is enabled, false if isn't, None if undefined/error
        """
        return self.fpgas[i].enabled

    def allEnabled(self):
        """
        returns true iff all boards are enabled (and can be disabled)
        """
        return all(self.enabled(i) is not False for i in self)

    def allDisabled(self):
        """
        returns true iff all boards are disabled (and can be enabled)
        """
        return all(self.enabled(i) is not True for i in self)

    def name(self, i):
        """
        returns the name of board 'i'
        """
        return self.fpgas[i].name

    def id(self, i):
        """
        Returns the id of board 'i'
        """
        return self.fpgas[i].id

    def toggle(self, i, state=None):
        """
        Sets the state of board 'i'
        Call without parameters to toggle
        """
        if self.enabled(i) is None: return
        if state is None: state = not self.enabled(i)
        self.enable(i) if state else self.disable(i)

    def enable(self, i):
        """
        Enables board 'i'
        """
        if self.enabled(i) is not False: return

        print("Enabling", i)
        for _ in range(10):
            try:
                print(subprocess.check_call(f"pnputil /enable-device {self.fpgas[i].id}"))
                break
            except Exception:
                pass
        else:
            print("Unable to enable the device")
        self.fpgas[i].enabled = True

    def disable(self, i):
        """
        Disable board 'i'
        """
        if self.enabled(i) is not True: return

        print("Disabling", i)
        for _ in range(10):
            try:
                print(subprocess.check_call(f"pnputil /disable-device {self.fpgas[i].id}"))
                break
            except Exception:
                pass
        else:
            print("Unable to disable the device")
        self.fpgas[i].enabled = False

    def get_state(self):
        """
        returns all the current states of all boards
        """
        return [(i, self.enabled(i)) for i in self]

    def __len__(self):
        """
        the length of this object is the number of available fpgas
        for convenience
        """
        return len(self.fpgas)

    def __iter__(self):
        """
        Iterating this object is the same as iterating range(len(self))
        for convenience
        """
        return range(len(self)).__iter__()
