♻️ Smart Waste AI Classification

AI-Powered Waste Sorting Assistant — Upload a photo, AI identifies the waste type and guides proper disposal.

Features
Real-time image classification (Glass, Metal, Paper, Plastic)
Confidence scores for all categories
Recycling guidelines and bin recommendations
Mobile-friendly interface
Models

Choose from 4 trained models, each traded off differently between speed and accuracy:

CNN — custom-built baseline
MobileNetV2 — lightweight, phone-friendly
ResNet50 — most accurate single model (~97% test accuracy)
Feature Fusion (ResNet50+CLIP) — dual-branch model combining ResNet50 with CLIP features
Input: 224x224 RGB images
Output: 4-class softmax probabilities (Glass, Metal, Paper, Plastic)
Deployment

Deployed on Streamlit Community Cloud
