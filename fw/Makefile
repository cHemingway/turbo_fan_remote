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
SCH:=../turbo_fan_remote
KICAD_CLI?=kicad-cli

calcs : $(CALCS).html $(CALCS).pdf

$(CALCS).html : $(CALCS).py
	uvx marimo export html --sandbox -f $< -o $@

$(CALCS).pdf : $(CALCS).py
	uvx marimo export pdf --sandbox -f $< -o $@

# Schematic PDF
schematic : $(SCH).pdf

$(SCH).pdf : $(SCH).kicad_sch
	$(KICAD_CLI) sch export pdf -o $@ $<

# Calcs and schematic, all as PDF
pdf : $(CALCS).pdf $(SCH).pdf

.PHONY : calcs schematic pdf
