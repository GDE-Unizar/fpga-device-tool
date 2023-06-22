import subprocess
from glob import glob
from time import sleep

from CONFIG import VIVADO_PATH, VIVADO_STARTUP_LOAD, VIVADO_PROGRAM_RETRY


class Vivado:
    def __init__(self):
        self._instance: subprocess.Popen | None = None
        self.ready = False

        # TODO allow user to choose version
        self.launcher = ([None] + sorted(glob(VIVADO_PATH)))[-1]

        # preload
        if VIVADO_STARTUP_LOAD:
            print("Preloading Vivado")
            self.prepare(wait_ready=False)

    def is_vivado_available(self):
        return self.launcher is not None

    def prepare(self, wait_ready=True):
        if self.ready: return  # already ready
        if self.launcher is None: return  # cant launch

        if self._instance is None:
            print("Launching cmd...")
            self._instance = subprocess.Popen('cmd.exe',
                                              universal_newlines=True,
                                              stdin=subprocess.PIPE,
                                              stdout=subprocess.PIPE,
                                              stderr=subprocess.STDOUT,
                                              )
            print("launching Vivado", self.launcher, "...")
            self._run(self.launcher + " -mode tcl -nolog -nojournal -verbose")

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

        if wait_ready:
            print("Waiting until Vivado is ready")
            self._waitUntil("vivado is now ready")
            self.ready = True

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
        if self.launcher is None: return
        self.prepare()

        # configure program
        self._run(f'set_property PROGRAM.FILE "{bitfile}" $hw_device')
        # if ila included: run("set_property PROBES.FILE {C:/design.ltx} $hw_device")

        for _ in range(VIVADO_PROGRAM_RETRY):
            self._run("program_hw_devices $hw_device")
            result = self._waitUntil("End of startup status")
            if 'HIGH' in result: break
            sleep(1)
        else:
            print("Unable to program the device")

    def close(self):
        if self._instance is None: return

        try:
            print("Closing Vivado")
            self._instance.communicate("exit", timeout=2)
        except subprocess.TimeoutExpired:
            print("Killing Vivado")
            self._instance.kill()
            self._instance.communicate()
