# Diffusion Policy: Visuomotor Policy Learning via Action Diffusion

## Abstract

We propose Diffusion Policy, a novel visuomotor policy learning framework for robot manipulation. Diffusion Policy formulates robot control as a denoising diffusion process over action sequences. Our method achieves state-of-the-art performance on Franka Panda robot tasks with 200 demonstrations.

## Introduction

Visuomotor policy learning has become a key approach for robot manipulation. However, deterministic policies struggle with multimodal action distributions. In this work, we introduce diffusion models to capture multimodality and improve policy expressiveness.

## Method

We propose Diffusion Policy, a diffusion-based policy that generates action sequences via iterative denoising. The architecture consists of a U-Net noise prediction network and a DDPM sampler. We design the policy to output 16-step action sequences, which enables multimodal action modeling.

## Experiment

We evaluate Diffusion Policy on Franka Panda robot with Robomimic framework. The dataset contains 200 episodes of manipulation tasks. Results show Diffusion Policy outperforms baseline LSTM-BC by 45% success rate. We also test on Robosuite environment for sim-to-real transfer.

## Conclusion

We demonstrate that diffusion models significantly improve visuomotor policy learning. Our method can be applied to VLA models for better multimodal action modeling. Future work includes integrating with ACT action chunking.
