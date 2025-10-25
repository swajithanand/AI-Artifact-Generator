# build.sh

# Exit immediately if any command fails
set -e

# Upgrade pip and install the dependencies
echo "--- Installing Python dependencies from requirements.txt ---"
pip install --upgrade pip
pip install -r requirements.txt

# (Optional) Log the installed packages for debugging
# pip freeze

echo "--- Build script finished successfully ---"