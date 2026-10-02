#!/usr/bin/env bash
# Launch the patched game in DOSBox-X.
#
# Needs two *real* floppy images: the game refuses to leave its first menu
# when drive A: is a mounted host directory -- it checks the BPB. imgmake
# builds them, and BDISK.VER on A: is what the game looks for.
#
#   tools/dosbox/run.sh            play (mouse works, click through menus)
#   tools/dosbox/run.sh 90         record 90s to build/captures/ and exit
#
# Patch into build/ first; this script never touches game/.
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
limit=${1:-}
conf=$(mktemp -t kami-conf)

{
  sed "s|@ROOT@|$root|" "$root/tools/dosbox/kami.conf"
  echo "mount c $root/build"
  echo "c:"
  echo "imgmake da.img -t fd_1440 > nul"
  echo "imgmake db.img -t fd_1440 > nul"
  echo 'imgmount a c:\da.img -t floppy'
  echo 'imgmount b c:\db.img -t floppy'
  echo 'copy c:\KAMI\BDISK.VER a:\ > nul'
  echo "cd KAMI"
  [ -n "$limit" ] && echo "config -avistart"
  echo "KAMI.COM"
} > "$conf"

args=(-conf "$conf" -nopromptfolder -fastlaunch -nolog)
[ -n "$limit" ] && args+=(-time-limit "$limit" -exit)

dosbox-x "${args[@]}"
