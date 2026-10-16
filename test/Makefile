# cocotb Makefile - Trinity Phi, TT SKY26d GF16 DOT4 (1x1)
# Apache-2.0
#
# One pin-level test set (test/test.py) for RTL and for the gate-level netlist:
#   RTL: make              GL (official gl_test action, CI): make -B GATES=yes
# cocotb is pinned in test/requirements.txt (cocotb==2.0.1), the same version the official
# gl_test action installs when that file exists.
#
# IMPORTANT: capture this Makefile's directory BEFORE the cocotb include,
# because $(MAKEFILE_LIST) grows as cocotb-config includes its own makefiles.
MAKEFILE_DIR       := $(dir $(abspath $(firstword $(MAKEFILE_LIST))))
# SRC_DIR can be overridden (the mutation runner points it at a mutated temporary copy).
SRC_DIR            ?= $(MAKEFILE_DIR)../src

SIM                ?= icarus
TOPLEVEL_LANG      ?= verilog
# One source list: this must equal info.yaml source_files and the files the top really
# instantiates (checked fail-closed by test/check_project.py).
PROJECT_SOURCES     = tt_um_trinity_nano.v \
                      gf16_v2_mul.v \
                      gf16_v2_add.v \
                      gf16_sig_mul10.v

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
# cocotb 2.x name, and the 1.x name for older runners
COCOTB_TEST_MODULES = test
MODULE              = test

include $(shell cocotb-config --makefiles)/Makefile.sim
