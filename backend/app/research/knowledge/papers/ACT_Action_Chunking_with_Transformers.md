# ACT: Action Chunking with Transformers for Imitation Learning

## Abstract

We propose ACT (Action Chunking Transformer), a novel imitation learning architecture for robot manipulation. ACT uses a conditional VAE with a transformer encoder-decoder to predict action chunks. Our method achieves state-of-the-art performance on SO101 robot tasks with only 50 demonstrations.

## Introduction

Imitation learning has become a key approach for robot manipulation. However, behavior cloning suffers from distribution shift. In this work, we introduce action chunking to reduce the effective horizon and improve policy robustness.

## Method

We propose ACT, a transformer-based policy that predicts chunks of actions. The architecture consists of a CVAE encoder for style inference and a transformer decoder for action generation. We design the policy to output 10-step action chunks, which reduces compounding errors.

## Experiment

We evaluate ACT on SO101 robot with LeRobot framework. The dataset contains 50 episodes of manipulation tasks. Results show ACT outperforms baseline BC by 30% success rate. We also test on Isaac Sim environment for sim-to-real transfer.

## Conclusion

We demonstrate that action chunking with transformers significantly improves imitation learning. Our method can be applied to VLA models for better generalization. Future work includes integrating with diffusion policy.
