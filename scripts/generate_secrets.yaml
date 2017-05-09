#!/bin/sh
#
# Extracts all uses of !secrets and generates an empty base file

find homeassistant/ -name '*.yaml' -exec grep \!secret {}  \; | awk '{print $3 ": "}' | sort
