#!/bin/bash

# Check if the argument is provided
if [ -z "$1" ] || [ -z "$2" ]; then
  echo "Usage: $0 <path_storage> <main_node>"
  exit 1
fi

PATH_STORAGE=$1
MAIN_NODE=$2

NUM_NODES=8
JOB_ID=axolotl-lambda
# You may need to change the MAIN_NODE to the resolved ip address
MAIN_NODE=${MAIN_NODE}:29500
YAML_CFG=${PATH_STORAGE}/axolotl-cookbook/lambda/configs/llama-3_1-405b-fft.yaml
export NODE_IDX=$((10#$(hostname | grep -oE '[0-9]+$') - 1))

/home/ubuntu/miniconda3/envs/pytorch/bin/torchrun --nnodes=$NUM_NODES --nproc-per-node=8 --node-rank=0 --rdzv-backend=c10d --rdzv-id=$JOB_ID --rdzv-endpoint=$MAIN_NODE -m axolotl.cli.train $YAML_CFG
