# -*- coding: utf-8 -*-
"""
Automatically generated by Colab.

Cardiac MRI still image deep learning

Preprocessing
"""

# Cardiac images tracings deep learning analysis and annotation
# Vivek Pujara 8/22/24

# Prelim logic and notes
"""
preprocessing pipeline
traced images > masks > contours > polygons > fill
validate polygon fill

import libraries
random seed (for reproducibility if needed)
device agnostic
preprocessing (traced images > binary masks)
data (train and test)
dataloader (train and test)
model
    CNN (feature extraction and classification) (U-Net) (ResNet)
    softmax (end of classifer block for probability distribution) (via loss)
    forward method
instantiate
    model
    loss function (criterion) (CrossEntropyLoss()) or BCE loss
    optimizer (Adam)
training function (train)
validation function (test)
train model (loop) (80/20, train/test)
    optim zero grad
    forward
    loss
    backward
    optim step
test model (loop)
"""

"""
import torch
import torch.nn as nn
import torch.optim as optim
import torchvision
from torchvision import transforms
from torch.utils.data import DataLoader
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import random
from tqdm.auto import tqdm
import os
import cv2
from PIL import Image
from torchvision.datasets import ImageFolder

torch.manual_seed(42)

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

data_train = ImageFolder(root="data/train", transform=tranforms.ToTensor())
data_test = ImageFolder(root="data/test", transform=tranforms.ToTensor())

dataloader_train = DataLoader(data_train, batch_size=32, shuffle=True)
dataloader_test = DataLoader(data_test, batch_size=32, shuffle=True)
"""

# -----------------------------------------------------------------

# Cardiac MRI still images tracings deep learning analysis and annotation in Google Colab

# Preprocessing (traced jpg images > filled binary masks)
import os
import cv2
import numpy as np

traced_images_folder = '/content/Traced'

mask_output_folder = '/content/mask_output_folder'

# Create the output folder if it doesn't exist
os.makedirs(mask_output_folder, exist_ok=True)

# Adjusted color thresholds for the masks
COLOR_THRESHOLDS = {
    'right_ventricle': ([0, 100, 100], [10, 255, 255]),  # Example HSV range for red
    'left_ventricle': ([40, 50, 50], [80, 255, 255]),    # Example HSV range for green
    'whole_heart': ([90, 50, 50], [130, 255, 255])       # Adjusted HSV range for blue
}

# Function to generate and fill a binary mask for a given color
def generate_filled_mask(image, lower, upper):
    # Convert to NumPy arrays with appropriate dtype
    lower = np.array(lower, dtype="uint8")
    upper = np.array(upper, dtype="uint8")

    # Convert the BGR image to HSV
    hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # Create the mask based on the HSV range
    mask = cv2.inRange(hsv_image, lower, upper)

    # Fill any holes or gaps within the mask
    # Find contours in the mask
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Fill the contours
    cv2.drawContours(mask, contours, -1, (255), thickness=cv2.FILLED)

    return mask

# Process each traced image in the folder
for traced_image_file in os.listdir(traced_images_folder):
    if traced_image_file.endswith('.jpg'):
        # Path to the current traced image
        traced_image_path = os.path.join(traced_images_folder, traced_image_file)

        # Load the traced image
        image = cv2.imread(traced_image_path)

        # Iterate over the defined structures to generate, fill, and save masks
        for structure, (lower, upper) in COLOR_THRESHOLDS.items():
            # Generate the filled mask
            mask = generate_filled_mask(image, lower, upper)

            # Define the path to save the mask, naming it based on the original file and structure
            mask_filename = f'{os.path.splitext(traced_image_file)[0]}_{structure}_mask.png'
            mask_path = os.path.join(mask_output_folder, mask_filename)

            # Save the mask image
            cv2.imwrite(mask_path, mask)

print(f"Filled masks have been successfully saved to {mask_output_folder}")

"""Dataset and dataloader"""

import os
import torch
import numpy as np
import cv2
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms

class CardiacMRIDataset(Dataset):
    def __init__(self, image_folder, mask_folder, image_size=(256, 256)):
        self.image_folder = image_folder
        self.mask_folder = mask_folder
        self.image_size = image_size
        self.image_filenames = [f for f in os.listdir(image_folder) if f.endswith('.jpg')]
        self.mask_filenames = [f for f in os.listdir(mask_folder) if f.endswith('.png')]
        self.image_filenames.sort()
        self.mask_filenames.sort()
        self.transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Resize(self.image_size)
        ])

    def __len__(self):
        return len(self.image_filenames)

    def __getitem__(self, idx):
        image_path = os.path.join(self.image_folder, self.image_filenames[idx])
        mask_path = os.path.join(self.mask_folder, self.image_filenames[idx].replace('.jpg', '_left_ventricle_mask.png'))

        image = cv2.imread(image_path)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)  # Convert to RGB
        image = self.transform(image)

        mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
        mask = cv2.resize(mask, self.image_size, interpolation=cv2.INTER_NEAREST)
        mask = torch.tensor(mask, dtype=torch.long)

        # Create a one-hot encoded mask
        one_hot_mask = torch.zeros(3, *self.image_size)
        for i, color in enumerate([1, 2, 3]):  # Adjust based on the color mapping
            one_hot_mask[i] = (mask == color).float()

        return image, one_hot_mask

# Initialize the dataset and dataloader
image_folder = '/content/Untraced'
mask_folder = '/content/mask_output_folder'
dataset = CardiacMRIDataset(image_folder, mask_folder)
dataloader = DataLoader(dataset, batch_size=2, shuffle=True)

"""U-Net model definition"""

import torch
import torch.nn as nn
import torchvision.models as models
import torch.nn.functional as F

class UNet(nn.Module):
    def __init__(self, in_channels=3, out_channels=3):
        super(UNet, self).__init__()
        self.encoder = nn.Sequential(
            nn.Conv2d(in_channels, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv2d(64, 64, kernel_size=3, padding=1),
            nn.ReLU()
        )
        self.middle = nn.Sequential(
            nn.MaxPool2d(2),
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv2d(128, 128, kernel_size=3, padding=1),
            nn.ReLU()
        )
        self.decoder = nn.Sequential(
            nn.Conv2d(128, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv2d(64, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv2d(64, out_channels, kernel_size=1)
        )
        self.pool = nn.MaxPool2d(2)
        self.upconv = nn.ConvTranspose2d(128, 64, kernel_size=2, stride=2)

    def forward(self, x):
        enc1 = self.encoder(x)            # Encoder path
        enc2 = self.middle(self.pool(enc1))  # Middle path
        dec1 = self.upconv(enc2)             # Upsample

        # Ensure the size of enc1 matches dec1 before concatenation
        if dec1.size()[2:] != enc1.size()[2:]:
            dec1 = F.interpolate(dec1, size=enc1.size()[2:], mode='bilinear', align_corners=False)

        dec1 = torch.cat([dec1, enc1], dim=1)  # Concatenate encoder output with decoder output
        out = self.decoder(dec1)               # Decoder path
        return out

model = UNet()

"""Model training"""

# Potential overfitting. Fine-tuning, with hyperparameter optimization (updated code in section below).
"""
import torch.optim as optim
import torch.nn.functional as F

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = UNet().to(device)
optimizer = optim.Adam(model.parameters(), lr=1e-4)
criterion = nn.BCEWithLogitsLoss()

def train_epoch(dataloader, model, optimizer, criterion, device):
    model.train()
    running_loss = 0.0
    for images, masks in dataloader:
        images = images.to(device)
        masks = masks.to(device)

        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, masks)
        loss.backward()
        optimizer.step()

        running_loss += loss.item() * images.size(0)

    epoch_loss = running_loss / len(dataloader.dataset)
    return epoch_loss

num_epochs = 4
for epoch in range(num_epochs):
    epoch_loss = train_epoch(dataloader, model, optimizer, criterion, device)
    print(f"Epoch {epoch+1}/{num_epochs}, Loss: {epoch_loss:.4f}")
"""

# Updated training loop with weighted CrossEntropyLoss (for class imbalance) and lower learning rate
# Can test and update batch_size and num_epochs
import torch.optim as optim
import torch.nn as nn

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = UNet().to(device)

# Define class weights for balancing
class_weights = torch.tensor([1.0, 1.0, 1.0], dtype=torch.float32).to(device)  # Adjust based on class distribution
criterion = nn.CrossEntropyLoss(weight=class_weights)
optimizer = optim.Adam(model.parameters(), lr=1e-5)  # Reduced learning rate

def train_epoch(dataloader, model, optimizer, criterion, device):
    model.train()
    running_loss = 0.0
    for images, masks in dataloader:
        images = images.to(device)
        masks = masks.to(device)

        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, torch.argmax(masks, dim=1))
        loss.backward()
        optimizer.step()

        running_loss += loss.item() * images.size(0)

    epoch_loss = running_loss / len(dataloader.dataset)
    return epoch_loss

num_epochs = 4
for epoch in range(num_epochs):
    epoch_loss = train_epoch(dataloader, model, optimizer, criterion, device)
    print(f"Epoch {epoch+1}/{num_epochs}, Loss: {epoch_loss:.4f}")

"""Post-processing visualization and colored mask overlays (optional) (beta)

import matplotlib.pyplot as plt
from google.colab.patches import cv2_imshow  # For displaying images in Google Colab

def apply_color_mask(image, mask, color):
    color_mask = np.zeros_like(image)
    color_mask[mask == 1] = color
    return cv2.addWeighted(image, 1.0, color_mask, 0.5, 0)

def generate_colored_overlays(image_folder, mask_folder, model, device):
    model.eval()
    os.makedirs('/content/overlay_output', exist_ok=True)  # Ensure the output directory exists

    for filename in os.listdir(image_folder):
        if filename.endswith('.jpg'):
            image_path = os.path.join(image_folder, filename)
            image = cv2.imread(image_path)
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            image_tensor = transforms.ToTensor()(image_rgb).unsqueeze(0).to(device)

            with torch.no_grad():
                output = model(image_tensor)
                output = output.squeeze().cpu().numpy()

                # Convert output to mask
                pred_mask = np.argmax(output, axis=0)

                # Apply color masks
                overlay = np.zeros_like(image_rgb)
                overlay = apply_color_mask(overlay, pred_mask == 0, [255, 0, 0])  # Red for right_ventricle
                overlay = apply_color_mask(overlay, pred_mask == 1, [0, 255, 0])  # Green for left_ventricle
                overlay = apply_color_mask(overlay, pred_mask == 2, [0, 0, 255])  # Blue for whole_heart

                # Save the overlay
                output_path = os.path.join('/content/overlay_output', filename)
                cv2.imwrite(output_path, overlay)

                # Display the original image, prediction mask, and overlay
                plt.figure(figsize=(15, 5))

                plt.subplot(1, 3, 1)
                plt.title('Original Image')
                plt.imshow(image_rgb)
                plt.axis('off')

                plt.subplot(1, 3, 2)
                plt.title('Predicted Mask')
                plt.imshow(pred_mask, cmap='gray')
                plt.axis('off')

                plt.subplot(1, 3, 3)
                plt.title('Overlay')
                plt.imshow(overlay)
                plt.axis('off')

                plt.show()

# Run the visualization
generate_colored_overlays(image_folder, '/content/overlay_output', model, device)
"""

!nvidia-smi

