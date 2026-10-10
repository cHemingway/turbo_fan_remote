all : flash

TARGET:=remote
TARGET_MCU:=CH32L103
TARGET_MCU_PACKAGE:=CH32L103F8P6

# ch32v003fun is a git submodule: git submodule update --init
CH32FUN_DIR?=ch32v003fun/ch32fun

include $(CH32FUN_DIR)/ch32fun.mk

flash : cv_flash

clean : cv_clean

# Battery-life design calcs (marimo notebook, deps inline via PEP 723)
CALCS:=../calcs/battery_life

calcs : $(CALCS).html

$(CALCS).html : $(CALCS).py
	uvx marimo export html --sandbox $< -o $@

.PHONY : calcs
