#!/usr/bin/env bash
# Install Framewright's Lua scripts and Fusion templates into DaVinci Resolve.
#
#   resolve/install.sh                 install
#   resolve/install.sh --uninstall     remove only the files this repo installs
#   resolve/install.sh --dry-run       print actions, change nothing
#   resolve/install.sh --dest <path>   custom Fusion folder
set -euo pipefail

src="$(cd "$(dirname "$0")" && pwd)"
uninstall=0
dry=0
dest=""

while [ $# -gt 0 ]; do
    case "$1" in
        --uninstall) uninstall=1 ;;
        --dry-run) dry=1 ;;
        --dest) dest="${2:?--dest needs a path}"; shift ;;
        -h|--help) sed -n '2,7p' "$0"; exit 0 ;;
        *) echo "Unknown option: $1" >&2; exit 2 ;;
    esac
    shift
done

if [ -z "$dest" ]; then
    case "$(uname -s)" in
        Darwin) dest="$HOME/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion" ;;
        Linux)  dest="$HOME/.local/share/DaVinciResolve/Fusion" ;;
        *) echo "On Windows use resolve/install.ps1, or pass --dest." >&2; exit 2 ;;
    esac
fi

if [ ! -d "$dest" ] && [ "$uninstall" -eq 0 ]; then
    echo "Fusion folder not found: $dest"
    echo "Start DaVinci Resolve once so it creates the folder, or pass --dest <path>."
    exit 1
fi

mode="Installing"; [ "$uninstall" -eq 1 ] && mode="Removing"
[ "$dry" -eq 1 ] && mode="[dry run] $mode"
echo "$mode -> $dest"

# source folder:target folder under the Fusion folder
map="scripts/Edit:Scripts/Edit
scripts/Utility:Scripts/Utility
templates/Titles:Templates/Edit/Titles
templates/Effects:Templates/Edit/Effects
templates/Transitions:Templates/Edit/Transitions
templates/Generators:Templates/Edit/Generators"

count=0
while IFS=: read -r from to; do
    [ -d "$src/$from" ] || continue
    [ "$uninstall" -eq 0 ] && [ "$dry" -eq 0 ] && mkdir -p "$dest/$to"
    for f in "$src/$from"/*; do
        [ -f "$f" ] || continue
        target="$dest/$to/$(basename "$f")"
        if [ "$uninstall" -eq 1 ]; then
            if [ -e "$target" ]; then
                [ "$dry" -eq 0 ] && rm -f "$target"
                count=$((count + 1))
            fi
        else
            [ "$dry" -eq 0 ] && cp -f "$f" "$target"
            count=$((count + 1))
        fi
    done
done <<< "$map"

if [ "$uninstall" -eq 1 ]; then
    echo "$count files $([ "$dry" -eq 1 ] && echo "would be ")removed."
else
    echo "$count files $([ "$dry" -eq 1 ] && echo "would be ")installed."
    echo "Restart DaVinci Resolve to see them (Workspace > Scripts, Effects panel)."
fi
