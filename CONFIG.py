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