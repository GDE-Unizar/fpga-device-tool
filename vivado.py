import subprocess
from time import sleep


class Vivado:
    def __init__(self):
        self._instance: subprocess.Popen | None = None

    def prepare(self):
        if self._instance is not None: return

        print("launching cmd...")
        self._instance = subprocess.Popen('cmd.exe',
                                          universal_newlines=True,
                                          stdin=subprocess.PIPE,
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.STDOUT,
                                          )
        # TODO find vivado version programmatically
        print("launching Vivado...")
        self._run("C:/Xilinx/Vivado/2022.1/bin/vivado.bat -mode tcl -nolog -nojournal -verbose")

        # initialize hardware manager
        self._run("load_features labtools")
        self._run("if { [catch {open_hw_manager} error] } { open_hw }")
        self._run("connect_hw_server -url TCP:localhost:3121")

        # connect to first available target
        self._run("set targu [get_hw_targets *]")
        self._run("current_hw_target $targu")
        self._run("open_hw_target")
        self._run("set hw_device [lindex [get_hw_devices] 1]")
        self._run("current_hw_device $hw_device")
        self._run('puts "vivado is now ready"')
        self._waitUntil("vivado is now ready")

    def _run(self, command):
        print("Running:", command)
        self._instance.stdin.write(command)
        self._instance.stdin.write('\n')
        self._instance.stdin.flush()

    def _waitUntil(self, expected):
        print("Waiting for:", expected)
        while True:
            try:
                line = self._instance.stdout.readline()
            except KeyboardInterrupt:
                exit()
            print("   >", line, end='')
            if expected in line: return line

    def program(self, bitfile):
        self.prepare()

        # configure program
        self._run(f'set_property PROGRAM.FILE "{bitfile}" $hw_device')
        # if ila included: run("set_property PROBES.FILE {C:/design.ltx} $hw_device")

        while True:
            self._run("program_hw_devices $hw_device")
            result = self._waitUntil("End of startup status")
            if 'HIGH' in result: break
            sleep(1)

    def close(self):
        if self._instance is None: return

        print("Closing vivado")
        self._instance.communicate("exit")
