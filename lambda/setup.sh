#!/bin/bash

# Check if the argument is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <path_storage>"
  exit 1
fi

# Exit immediately if a command exits with a non-zero status
set -e

PATH_STORAGE=$1

# Check if Miniconda is already installed
if [ ! -d "/home/ubuntu/miniconda3" ]; then
    # Download and install Miniconda
    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh
    bash /tmp/miniconda.sh -b -p /home/ubuntu/miniconda3 -u
    /home/ubuntu/miniconda3/bin/conda init bash
    echo 'export PATH="/home/ubuntu/miniconda3/bin:$PATH"' >> ~/.bashrc
    source ~/.bashrc
else
    /home/ubuntu/miniconda3/bin/conda init bash
    echo 'export PATH="/home/ubuntu/miniconda3/bin:$PATH"' >> ~/.bashrc
    source ~/.bashrc
fi

# Configure Conda and create PyTorch environment
/home/ubuntu/miniconda3/bin/conda remove -n pytorch --all -y
/home/ubuntu/miniconda3/bin/conda install python=3.11 -y
/home/ubuntu/miniconda3/bin/conda install -c conda-forge libstdcxx-ng -y
/home/ubuntu/miniconda3/bin/conda create -n pytorch python=3.11 -y
echo 'conda activate pytorch' >> ~/.bashrc

# Install PyTorch
/home/ubuntu/miniconda3/bin/conda run -n pytorch conda install pytorch==2.3.1 torchvision torchaudio pytorch-cuda=12.1 -c pytorch -c nvidia -y

# Verify PyTorch installation
/home/ubuntu/miniconda3/bin/conda run -n pytorch python -c "import torch; print(torch.__version__); print(torch.cuda.is_available())"

# Add Git LFS repository and install
sudo add-apt-repository -y ppa:git-core/ppa
sudo apt-get update
sudo apt-get install -y git-lfs
git lfs install --skip-repo

# Install awscli and pydantic in PyTorch environment
/home/ubuntu/miniconda3/bin/conda run -n pytorch pip install awscli==1.33.13 packaging
/home/ubuntu/miniconda3/bin/conda run -n pytorch pip install -U --no-cache-dir pydantic==1.10.10

# Install system packages
sudo apt-get install -y vim curl nano rsync s3fs net-tools nvtop infiniband-diags pdsh libaio-dev

# Add ubuntu user to root group
sudo usermod -aG root ubuntu

mkdir -p ${PATH_STORAGE}/axolotl-artifacts/{configs,outputs}
# Clone axolotl repository
CLONE_DIR=${PATH_STORAGE}/axolotl
if [ ! -d "$CLONE_DIR" ]; then
    git clone --single-branch https://github.com/axolotl-ai-cloud/axolotl.git $CLONE_DIR
fi

# Install causal_conv1d and axolotl in PyTorch environment
export PATH="/home/ubuntu/miniconda3/envs/pytorch/bin:/home/ubuntu/miniconda3/bin:/home/ubuntu/miniconda3/condabin:/home/ubuntu/.local/bin:/usr/lib/cuda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin"
export LD_LIBRARY_PATH="/usr/lib/cuda/lib64"
export CUDA_HOME="/usr/lib/nvidia-cuda-toolkit"
/home/ubuntu/miniconda3/bin/conda run -n pytorch pip install causal_conv1d
/home/ubuntu/miniconda3/bin/conda run -n pytorch pip install --no-cache -e $CLONE_DIR[deepspeed,flash-attn,optimizers]

# Configure git credential helper
git config --global credential.helper store

# Install and configure tmux
sudo apt-get install -y tmux
echo '# Run tmux only in interactive shells
if [[ $- == *i* ]] && [[ -z "$TMUX" ]]; then
  tmux attach-session -t ssh_tmux || tmux new-session -s ssh_tmux
fi' >> ~/.bashrc

# Create huggingface cache directory and set environment variables
mkdir -p ${PATH_STORAGE}/.cache/huggingface
echo "export HF_HOME=\"${PATH_STORAGE}/.cache/huggingface\"" >> ~/.bashrc
echo 'export HF_HUB_ENABLE_HF_TRANSFER="1"' >> ~/.bashrc
echo 'export PATH="/home/ubuntu/miniconda3/envs/pytorch/bin:/home/ubuntu/miniconda3/bin:/home/ubuntu/miniconda3/condabin:/home/ubuntu/.local/bin:/usr/lib/cuda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin"' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH="/usr/lib/cuda/lib64"' >> ~/.bashrc
echo 'export CUDA_HOME="/usr/lib/nvidia-cuda-toolkit"' >> ~/.bashrc

# default .profile adds ~/.local/bin which breaks pip/python
sed -i '/if \[ -d "\$HOME\/\.local\/bin" \] ; then/,/fi/s/^/#/' ~/.profile
