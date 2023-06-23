FPGA_COMMAND_LIST = "pnputil /enum-devices /class USB /connected"
FPGA_COMMAND_ENABLE = "pnputil /enable-device %s"
FPGA_COMMAND_DISABLE = "pnputil /disable-device %s"
FPGA_COMMAND_DISABLE_RETRY = 10
FPGA_COMMAND_ENABLE_RETRY = 10

FPGA_DESCRIPTION = "USB Serial Converter A"

FPGA_STATUS_DISABLED = ["Disabled", "Deshabilitado"]
FPGA_STATUS_ENABLED = ["Started", "Iniciado"]

# --- #

VIVADO_PATH = "C:/Xilinx/Vivado*/*/bin/vivado.bat"
VIVADO_STARTUP_LOAD = False
VIVADO_BITSTREAM_LOAD = True

VIVADO_PROGRAM_RETRY = 10

# --- #

UI_THEME = 'SystemDefaultForReal'
UI_REFRESH_TIMEOUT = 2000

# ------------------------- #

# replace with parameters if found
# to specify a parameter just add it as the command line:
# $> program_tool.exe UI_REFRESH_TIMEOUT=500 "FPGA_DESCRIPTION=USB board"

import sys

for _parameter in sys.argv[1:]:
    try:
        _key, _value = _parameter.split("=")
        _current = locals()[_key]
        _type = type(_current)
        _new = _type(_value)
        locals()[_key] = _new  # parse new value to same type
        print(f'Replaced {_key} from {repr(_current)} to {repr(_new)} (converted from "{_value}" as {_type})')
    except Exception:
        print("Can't replace parameter", _parameter)
