#!/usr/bin/env bash

container install
pip install --upgrade pip
pip install -r requirements-dev.txt
pre-commit install
pre-commit install-hooks
chmod +x /workspaces/ha-cyclepay/.devcontainer/post-set-version-hook.sh

lib_dir="/workspaces/pylaundry"
repo_url="https://github.com/elahd/pylaundry.git"

if [ ! -d $lib_dir ]; then
    echo "Cloning pylaundry repository..."
    git clone "$repo_url" "$lib_dir"
else
    echo "pylaundry repository directory already exists."
fi

cd /workspaces/pylaundry
python setup.py develop

pip install -r /workspaces/pylaundry/requirements-dev.txt
