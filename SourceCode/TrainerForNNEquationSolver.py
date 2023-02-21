import torch
from .NeuralNetworkFunction import NeuralNetworkFunction
from .EquationClass import AbstractEquation
import numpy as np
import random


class TrainerForNNEquationSolver:
    def __init__(
            self,
            main_eq: AbstractEquation,
            n_epochs: int = 20
    ):
        self.set_seed(77)
        self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        self.main_eq = main_eq
        self.batch_size = 1
        self.norm = lambda x: torch.pow(x, 2)
        self.nn_models = self.get_nn_models()
        # self.nn_model.to(self.device)
        self.num_epochs = n_epochs
        lr = 1e-1
        # self.optimizer = torch.optim.Adam(
        #     self.nn_model.parameters(), lr=lr , betas=(0.99, 0.9999)
        # )
        model_parameters = []
        for nn_model in self.nn_models:
            model_parameters += list(nn_model.parameters())
        self.optimizer = torch.optim.LBFGS(params = model_parameters, lr=lr, max_iter=20)
        self.scheduler = torch.optim.lr_scheduler.StepLR(
            self.optimizer, step_size=10, gamma=1
        )

    def get_nn_models(self):
        n_inputs = 1
        n_hidden_neurons = 50
        n_layers = 2
        n = self.main_eq.count_equations()
        return [NeuralNetworkFunction(n_inputs, n_hidden_neurons, n_layers) for _ in range(n)]

    @staticmethod
    def set_seed(seed: int = 77) -> None:
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
        torch.cuda.manual_seed(seed)
        torch.backends.cudnn.deterministic = True

    def fit(self, verbose: bool = False) -> (torch.Tensor, torch.Tensor, torch.nn):
        mse_loss_train = torch.zeros(self.num_epochs)
        mse_loss_valid = torch.zeros(self.num_epochs)
        for epoch in range(self.num_epochs):
            if verbose:
                print("Epoch {}/{}:".format(epoch, self.num_epochs - 1), flush=True)
            # Each epoch has a training and validation phase
            for phase in ["train", "valid"]:
                if phase == "train":
                    self.nn_models = [nn_model.train() for nn_model in self.nn_models]  # Set model to training mode
                else:
                    self.nn_models = [nn_model.eval() for nn_model in self.nn_models]  # Set model to evaluate mode
                epoch_loss = self.get_loss(phase)
                if phase == "train":
                    self.scheduler.step()
                    mse_loss_train[epoch] = epoch_loss
                else:
                    mse_loss_valid[epoch] = epoch_loss
                if verbose:
                    print("{} Loss: {:.4f}".format(phase, epoch_loss), flush=True)
        return mse_loss_train, mse_loss_valid, self.nn_models

    def get_loss(self, phase: str) -> float:
        def closure():
            self.optimizer.zero_grad()
            total_loss, max_residual_norm = self.main_eq.get_residuals_norm(self.nn_models, phase)
            if phase == "train":
                total_loss.backward()
            return max_residual_norm.item()

        self.optimizer.step(closure=closure)
        epoch_loss = closure()
        return epoch_loss
