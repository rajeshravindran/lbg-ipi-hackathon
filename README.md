# lbg-ipi-hackathon
## Install uv
https://docs.astral.sh/uv/getting-started/installation/

## Install version of Python using uv 
uv python install (installs latest version of python)
uv python install 3.12 (installs version 3.12)

## setup venv
git clone https://github.com/rajeshravindran/lbg-ipi-hackathon.git
cd lbg-ipi-hackathon
uv init 
source .venv/bin/activate
uv add -r requirements.txt (to install packages from requirements.txt)
uv add requests (install a particular package)
uv remove requests (uninstall a particular package)
uv sync (helps sync the packages mentioned in pyproject.toml file in a new env)


