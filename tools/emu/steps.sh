#!/bin/bash
# steps.sh prefix n [key] : press key (default x = A) n times, one screenshot after each
D=$(dirname "$0")
for i in $(seq 1 $2); do $D/press.sh $1_$(printf %03d $i).png ${3:-x}; done
