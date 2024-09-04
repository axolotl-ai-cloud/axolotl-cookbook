#!/bin/bash

NUM_NODES=8
JOB_ID=axolotl-lambda
# You may need to change the MAIN_NODE to the resolved ip address
MAIN_NODE=ml-64-node-001:29500
YAML_CFG=/home/ubuntu/ml-1cc/axolotl-cookbook/lambda/configs/fsdp-405b.yaml
export NODE_IDX=$((10#$(hostname | grep -oE '[0-9]+$') - 1))

/home/ubuntu/miniconda3/envs/pytorch/bin/torchrun --nnodes=$NUM_NODES --nproc-per-node=8 --node-rank=0 --rdzv-backend=c10d --rdzv-id=$JOB_ID --rdzv-endpoint=$MAIN_NODE -m axolotl.cli.train $YAML_CFG
