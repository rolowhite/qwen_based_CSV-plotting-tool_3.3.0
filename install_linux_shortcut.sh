#!/usr/bin/env bash
# Adds "CSV Plot Studio" to the Linux Mint / Ubuntu application menu.
# Run ./run_linux.sh once from a terminal first, so the packages are installed.
cd "$(dirname "$0")" || exit 1
HERE="$(pwd)"
APPS="$HOME/.local/share/applications"
mkdir -p "$APPS"
cat > "$APPS/csv-plot-studio.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=CSV Plot Studio
Comment=Plot CSV files with matplotlib and seaborn, and get the code
Exec=bash "$HERE/run_linux.sh" %f
Icon=$HERE/plotstudio/assets/icon.png
Terminal=false
Categories=Science;DataVisualization;
MimeType=text/csv;
EOF
chmod +x "$APPS/csv-plot-studio.desktop"
command -v update-desktop-database >/dev/null && update-desktop-database "$APPS" 2>/dev/null
echo "Done: look for 'CSV Plot Studio' in your applications menu."
echo "(You can also right-click a .csv file > Open With > CSV Plot Studio.)"
