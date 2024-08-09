"""
Training file for the models we implemented 
"""

from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.utils
from torch.utils.data import DataLoader
from einops import rearrange
import wandb
from tqdm import tqdm

from model import BigramLanguageModel, MiniGPT
from dataset import TinyStoriesDataset
from config import BigramConfig, MiniGPTConfig


MODEL = "minigpt"  # bigram or minigpt

if MODEL == "bigram":
    config = BigramConfig
    model = BigramLanguageModel(config)
elif MODEL == "minigpt":
    config = MiniGPTConfig
    model = MiniGPT(config)
else:
    raise ValueError("Invalid model name")


# Initialize wandb if you want to use it
if config.to_log:
    wandb.init(project="dl2_proj3")


def count_parameters(model):
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


train_dataset = TinyStoriesDataset(
    config.path_to_data,
    mode="train",
    context_length=config.context_length,
)
eval_dataset = TinyStoriesDataset(
    config.path_to_data, mode="test", context_length=config.context_length
)

train_dataloader = DataLoader(
    train_dataset, batch_size=config.batch_size, pin_memory=True
)
eval_dataloader = DataLoader(
    eval_dataset, batch_size=config.batch_size, pin_memory=True
)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print("number of trainable parameters: %.2fM" % (count_parameters(model) / 1e6,))


if not Path.exists(config.save_path):
    Path.mkdir(MiniGPTConfig.save_path, parents=True, exist_ok=True)


### ==================== START OF YOUR CODE ==================== ###
"""
You are required to implement the training loop for the model.

Please keep the following in mind:
- You will need to define an appropriate loss function for the model.
- You will need to define an optimizer for the model.
- You are required to log the loss (either on wandb or any other logger you prefer) every `config.log_interval` iterations.
- It is recommended that you save the model weights every `config.save_iterations` iterations you can also just save the model with the best training loss.

Please check the config file to see the different configurations you can set for the model.
NOTE : 
The MiniGPT config has params that you do not need to use, these were added to scale the model but are 
not a required part of the assignment. 
Feel free to experiment with the parameters and I would be happy to talk to you about them if interested :)
"""

#========Set Loss Function and Optimizer========#
criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.001, weight_decay = 1e-4)
#===============================================#

#========Set Save Path========#
best_model_params_path = "./models/" + MODEL + "/best_model_params.pt"
torch.save(model.state_dict(), best_model_params_path)
#=============================#

#========Bookkeeping========#
best_train_loss = 1000.0
iteration = 0
num_epochs = 1
#===========================#

#========Training Loop========#
for epoch_idx in tqdm(range(num_epochs)):
    for inputs, targets in train_dataloader:
        if iteration==5000: #hard code to stop at 5000 iterations
          break
        model.train()
        optimizer.zero_grad()
        inputs = inputs.to(device)
        targets = targets.to(device)
        logits = model(inputs)
        logits = logits.transpose(1,2)
        loss = criterion(logits, targets)
        loss.backward()
        optimizer.step()
        iteration += 1

        if loss.item() < best_train_loss: #save model with best training loss
            best_train_loss = loss.item()
            torch.save(model.state_dict(), best_model_params_path)

        if iteration%config.log_interval == 0: #record the loss in wandb and validate
            wandb.log({"Training loss": loss.item()})
            model.eval()
            with torch.no_grad():
                total_loss = 0.0
                num_batches = 20
                for i in range(num_batches): #validate on 20 batches from the eval dataset
                    batch = next(iter(eval_dataloader))
                    inputs, targets = batch
                    inputs = inputs.to(device)
                    targets = targets.to(device)
                    logits = model(inputs)
                    logits = logits.transpose(1,2)
                    loss = criterion(logits, targets)
                    total_loss += loss.item()
                val_loss = total_loss/num_batches
                wandb.log({"Validation loss": val_loss})

    print(f'Epoch [{epoch_idx+1}/{num_epochs}], Loss: {loss.item():.4f}')
wandb.finish()
#=============================#
