# Talk like a Pirate

Built on a synthetic dataset from Gemini Flash 1.5, we samplee 10,000 rows from ultrachat-200k to respond like a pirate.

Dataset: [winglian/pirate-ultrachat-10k](https://huggingface.co/datasets/winglian/pirate-ultrachat-10k)
WandB: https://wandb.ai/axolotl-ai/pirate-ultrachat-llama31
Model (LoRA adapter) [winglian/llama-3.1-8b-talk-like-a-pirate][https://huggingface.co/winglian/llama-3.1-8b-talk-like-a-pirate]

### Hardware

With a single L40S GPU (48GB), this model will train in approximately 6 hours. See [config](https://wandb.ai/axolotl-ai/pirate-ultrachat-llama31/runs/ux2ukksw/files/tmp/axolotl_config_tc5xe_jx.yml).

For Multi-GPU, there is additional memory overhead needed to use DDP, thus we need to employ DeepSpeed ZeRO-2 in order to 
finetune the model with OOM-ing.
