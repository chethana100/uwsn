#!/usr/bin/env bash
# usage: runargs.sh <outdir> <args...>   (tag fixed to v1, run fixed by caller args)
set -u
out="$1"; shift
mkdir -p "$out" && cd "$out" || exit 1
LD_LIBRARY_PATH=/home/aswinlaks/ns-allinone-3.41/ns-3.41/build/lib \
  /home/aswinlaks/ns-allinone-3.41/ns-3.41/build/scratch/ns3.41-uwsn-trustq-attack-default \
  --tag=v1 "$@" > stdout.log 2> stderr.log
echo "$out exit=$?"
