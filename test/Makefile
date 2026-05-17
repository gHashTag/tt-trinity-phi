# cocotb Makefile — TRI-1 Nano
# Apache-2.0
#
# IMPORTANT: capture this Makefile's directory BEFORE the cocotb include,
# because $(MAKEFILE_LIST) grows as cocotb-config includes its own makefiles
# (then $(lastword …) points at cocotb internals instead of this file).
MAKEFILE_DIR       := $(dir $(abspath $(firstword $(MAKEFILE_LIST))))
SRC_DIR            := $(MAKEFILE_DIR)../src

SIM                ?= icarus
TOPLEVEL_LANG      ?= verilog
PROJECT_SOURCES     = tt_um_trinity_nano.v gf16_mul.v gf16_add.v gf16_dot4.v trinity_gf16_tile.v

ifneq ($(GATES),yes)
  SIM_BUILD         = sim_build/rtl
  VERILOG_SOURCES  += $(addprefix $(SRC_DIR)/,$(PROJECT_SOURCES))
else
  SIM_BUILD         = sim_build/gl
  COMPILE_ARGS     += -DGL_TEST -DFUNCTIONAL -DUSE_POWER_PINS -DSIM -DUNIT_DELAY=\#1
  VERILOG_SOURCES  += $(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/verilog/primitives.v
  VERILOG_SOURCES  += $(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/verilog/sky130_fd_sc_hd.v
  VERILOG_SOURCES  += $(MAKEFILE_DIR)gate_level_netlist.v
endif

COMPILE_ARGS       += -I$(SRC_DIR)
VERILOG_SOURCES    += $(MAKEFILE_DIR)tb.v
TOPLEVEL            = tb
MODULE              = test

include $(shell cocotb-config --makefiles)/Makefile.sim
